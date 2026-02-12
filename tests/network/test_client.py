"""
test_client.py -- Unit tests for VeriStoreClient.

Uses httpx's MockTransport to avoid real network calls.

Covers:
    - put() disperses to all n servers and returns block_id
    - put() raises DispersalError when fewer than m servers respond
    - get() collects m fragments, verifies them, and decodes correctly
    - get() raises RetrievalError when fewer than m verified fragments available
    - get() re-verifies fragments and rejects corrupt server responses
    - delete() sends DELETE to all servers (ignores 404)
    - health_check() returns True for responding servers, False for unreachable
"""

import pytest
from unittest.mock import MagicMock, patch
from src.network.client import VeriStoreClient, ServerAddress, DispersalError, RetrievalError


@pytest.fixture
def servers() -> list[ServerAddress]:
    """Five local server addresses for testing."""
    return [ServerAddress(server_id=i + 1, port=5000 + i + 1) for i in range(5)]


@pytest.fixture
def client(servers) -> VeriStoreClient:
    """A VeriStoreClient with mock servers."""
    return VeriStoreClient(servers=servers, m=3)


class TestClientPut:
    """Tests for VeriStoreClient.put()."""

    def test_put_calls_all_servers(self, client):
        """put() sends a request to each of the n servers."""
        # TODO: Patch httpx.Client.put to record calls.
        #       client.put("key1", b"data")
        #       assert number of PUT calls == 5
        ...

    def test_put_returns_block_id(self, client):
        """put() returns the block_id string."""
        # TODO: Mock all servers to return 200.
        #       result = client.put("mykey", b"some data")
        #       assert isinstance(result, str)
        ...

    def test_put_raises_dispersal_error_when_too_few_succeed(self, client):
        """put() raises DispersalError if < m servers accept."""
        # TODO: Mock only 2 servers to succeed (< m=3).
        #       with pytest.raises(DispersalError): client.put("key", b"data")
        ...


class TestClientGet:
    """Tests for VeriStoreClient.get()."""

    def test_get_returns_original_data(self, client):
        """get() decodes and returns the original data bytes."""
        # TODO: Mock servers to return valid fragments (pre-encoded).
        #       assert client.get("key1") == original_data
        ...

    def test_get_rejects_corrupt_fragment(self, client):
        """get() skips fragments that fail verification."""
        # TODO: Mock 2 servers to return corrupt data, 3 to return valid data.
        #       result = client.get("key1")
        #       assert result == original_data  # still succeeds with valid fragments
        ...

    def test_get_raises_retrieval_error_when_not_enough_valid(self, client):
        """get() raises RetrievalError if fewer than m fragments verify."""
        # TODO: Mock all servers to return corrupt data.
        #       with pytest.raises(RetrievalError): client.get("key1")
        ...


class TestClientHealthCheck:
    """Tests for VeriStoreClient.health_check()."""

    def test_all_healthy(self, client):
        """health_check() returns True for all reachable servers."""
        # TODO: Mock all /health endpoints to return 200.
        #       result = client.health_check()
        #       assert all(result.values())
        ...

    def test_some_unreachable(self, client):
        """health_check() returns False for unreachable servers."""
        # TODO: Mock 2 servers to raise a connection error.
        #       result = client.health_check()
        #       assert sum(result.values()) == 3  # 3 healthy, 2 down
        ...
