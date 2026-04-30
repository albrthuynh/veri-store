"""
test_security.py -- End-to-end security integration tests.

These tests wire a real VeriStoreClient to five in-process FastAPI server apps.
They exercise the full dispersal/retrieval path across the HTTP layer while
keeping everything local and deterministic.

Covers:
    - honest 5-server round-trip succeeds
    - retrieval succeeds with up to f=2 Byzantine servers corrupting GET responses
    - retrieval fails closed when 3 servers are Byzantine
    - wrong client token causes dispersal to fail
    - delete removes data from the whole cluster
    - health_check reports unreachable servers correctly
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from src.network.client import DispersalError, RetrievalError, ServerAddress, VeriStoreClient
from src.network.server import create_app

_TOKEN = "integration-token"
_N = 5
_M = 3


class _LocalHttpxClient:
    """Route client HTTP calls into in-process FastAPI TestClients by port."""

    def __init__(self, clients_by_port: dict[int, TestClient]) -> None:
        self._clients_by_port = clients_by_port

    def request(self, method: str, url: str, **kwargs):
        parsed = urlparse(url)
        port = parsed.port
        if port is None or port not in self._clients_by_port:
            raise httpx.RequestError(f"No local test server configured for {url}")

        local_client = self._clients_by_port[port]
        return local_client.request(
            method,
            parsed.path,
            json=kwargs.get("json"),
            headers=kwargs.get("headers"),
        )

    def __enter__(self) -> _LocalHttpxClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.fixture
def servers() -> list[ServerAddress]:
    return [ServerAddress(server_id=i + 1, port=5001 + i) for i in range(_N)]


@pytest.fixture
def cluster_factory():
    """Create an in-process 5-server cluster with optional Byzantine/unreachable nodes."""

    created_clients: list[TestClient] = []
    created_roots: list[Path] = []

    def _make_cluster(
        *,
        byzantine_server_ids: set[int] | None = None,
        unavailable_server_ids: set[int] | None = None,
    ) -> tuple[dict[int, TestClient], Path]:
        byzantine_server_ids = byzantine_server_ids or set()
        unavailable_server_ids = unavailable_server_ids or set()

        root = Path("data/test_runs") / str(uuid.uuid4())
        root.mkdir(parents=True, exist_ok=False)
        created_roots.append(root)

        clients_by_port: dict[int, TestClient] = {}
        for server_id in range(1, _N + 1):
            if server_id in unavailable_server_ids:
                continue

            byzantine_indices = frozenset({server_id - 1}) if server_id in byzantine_server_ids else frozenset()
            app = create_app(
                server_id=server_id,
                data_dir=str(root),
                byzantine_indices=byzantine_indices,
                token=_TOKEN,
            )
            test_client = TestClient(app)
            created_clients.append(test_client)
            clients_by_port[5000 + server_id] = test_client

        return clients_by_port, root

    try:
        yield _make_cluster
    finally:
        for client in created_clients:
            client.close()
        for root in created_roots:
            shutil.rmtree(root, ignore_errors=True)


def _make_veristore_client(servers: list[ServerAddress], *, token: str = _TOKEN) -> VeriStoreClient:
    return VeriStoreClient(servers=servers, m=_M, token=token)


class TestSecurityIntegration:
    """End-to-end security integration tests."""

    def test_honest_cluster_round_trip(self, cluster_factory, servers):
        """A normal PUT -> GET round-trip succeeds across all five servers."""
        clients_by_port, _ = cluster_factory()
        client = _make_veristore_client(servers)
        data = b"integration round-trip payload"
        block_id = "security-roundtrip"

        with patch("src.network.client.httpx.Client", return_value=_LocalHttpxClient(clients_by_port)):
            stored_block_id = client.put(block_id, data)
            recovered = client.get(block_id)

        assert stored_block_id == block_id
        assert recovered == data

    def test_retrieval_succeeds_with_two_byzantine_servers(self, cluster_factory, servers):
        """The client still reconstructs the original block with f=2 Byzantine servers."""
        clients_by_port, _ = cluster_factory(byzantine_server_ids={1, 2})
        client = _make_veristore_client(servers)
        data = b"byzantine tolerance integration payload"
        block_id = "security-byzantine-2"

        with patch("src.network.client.httpx.Client", return_value=_LocalHttpxClient(clients_by_port)):
            client.put(block_id, data)
            recovered = client.get(block_id)

        assert recovered == data

    def test_retrieval_fails_with_three_byzantine_servers(self, cluster_factory, servers):
        """Retrieval fails closed when more than f=2 servers are Byzantine."""
        clients_by_port, _ = cluster_factory(byzantine_server_ids={1, 2, 3})
        client = _make_veristore_client(servers)
        data = b"too many byzantine servers"
        block_id = "security-byzantine-3"

        with patch("src.network.client.httpx.Client", return_value=_LocalHttpxClient(clients_by_port)):
            client.put(block_id, data)
            with pytest.raises(RetrievalError, match="only .* verified fragments available"):
                client.get(block_id)

    def test_wrong_client_token_causes_dispersal_failure(self, cluster_factory, servers):
        """A client with the wrong bearer token cannot successfully disperse data."""
        clients_by_port, _ = cluster_factory()
        client = _make_veristore_client(servers, token="wrong-token")

        with patch("src.network.client.httpx.Client", return_value=_LocalHttpxClient(clients_by_port)):
            with pytest.raises(DispersalError):
                client.put("wrong-token-block", b"should not be accepted")

    def test_delete_removes_data_from_cluster(self, cluster_factory, servers):
        """After DELETE, GET fails because no servers still have the fragments."""
        clients_by_port, _ = cluster_factory()
        client = _make_veristore_client(servers)
        data = b"delete me securely"
        block_id = "security-delete"

        with patch("src.network.client.httpx.Client", return_value=_LocalHttpxClient(clients_by_port)):
            client.put(block_id, data)
            client.delete(block_id)
            with pytest.raises(RetrievalError, match="no servers returned a fragment"):
                client.get(block_id)

    def test_health_check_reports_unreachable_servers(self, cluster_factory, servers):
        """health_check() marks missing servers as unhealthy."""
        clients_by_port, _ = cluster_factory(unavailable_server_ids={4, 5})
        client = _make_veristore_client(servers)

        with patch("src.network.client.httpx.Client", return_value=_LocalHttpxClient(clients_by_port)):
            with patch("src.network.client.time.sleep"):
                status = client.health_check()

        assert status[1] is True
        assert status[2] is True
        assert status[3] is True
        assert status[4] is False
        assert status[5] is False
