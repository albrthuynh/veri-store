"""
test_client.py -- Unit tests for VeriStoreClient.

Uses unittest.mock to intercept httpx calls without real network I/O.

Covers:
    - put() disperses to all n servers and returns block_id
    - put() raises DispersalError when fewer than m servers respond
    - get() collects m fragments, verifies them, and decodes correctly
    - get() raises RetrievalError when fewer than m verified fragments available
    - get() re-verifies fragments and rejects corrupt server responses
    - delete() sends DELETE to all servers (ignores 404)
    - health_check() returns True for responding servers, False for unreachable
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.erasure.encoder import encode
from src.network.client import (
    DispersalError,
    RetrievalError,
    ServerAddress,
    VeriStoreClient,
)
from src.network.protocol import GetFragmentResponse, HealthResponse, StoreFragmentResponse
from src.verification.cross_checksum import FingerprintedCrossChecksum

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_BLOCK_ID = "test-block-byzantine"
_DATA = b"The quick brown fox jumps over the lazy dog -- long enough for RS coding."
_N = 5
_M = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_response(status_code: int, body: dict) -> MagicMock:
    """Minimal mock of an httpx.Response."""
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    return r


def _get_body(fragment, fpcc_json: str, *, corrupt: bool = False) -> dict:
    """
    Build a GetFragmentResponse JSON body for a fragment.

    If corrupt=True, every byte is XOR-ed with 0xFF — the same transformation
    used by the server's Byzantine fault injection mode.  This guarantees a
    SHA-256 hash mismatch that Verifier.check() will catch.
    """
    data = fragment.data
    if corrupt:
        data = bytes(b ^ 0xFF for b in data)
    return GetFragmentResponse(
        block_id=fragment.block_id,
        index=fragment.index,
        fragment_data=base64.b64encode(data).decode(),
        total_n=fragment.total_n,
        threshold_m=fragment.threshold_m,
        original_length=fragment.original_length,
        fpcc_json=fpcc_json,
        verification_status="valid",
    ).model_dump()


def _put_body(block_id: str, index: int) -> dict:
    return StoreFragmentResponse(
        block_id=block_id,
        index=index,
        verification_status="valid",
        message="ok",
    ).model_dump()


def _health_body(server_id: int) -> dict:
    return HealthResponse(server_id=server_id, status="ok", fragment_count=0).model_dump()


def _fragment_url(port: int, block_id: str, index: int) -> str:
    return f"http://localhost:{port}/fragments/{block_id}/{index}"


def _mock_http(url_map: dict[str, MagicMock]) -> MagicMock:
    """
    Return a mock that plays the role of both the httpx.Client instance
    returned by `httpx.Client(timeout=...)` and the `http` variable bound
    inside `with httpx.Client(...) as http:`.

    url_map maps a URL string to the mock httpx.Response to return.
    Any URL not in the map raises httpx.RequestError (network unreachable).
    """
    mock = MagicMock()

    def _request(method, url, **kwargs):
        resp = url_map.get(url)
        if resp is None:
            raise httpx.RequestError(f"No mock configured for {method} {url}")
        return resp

    mock.request.side_effect = _request
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def encoded():
    """
    Real erasure-coded fragments and fpcc computed once for the whole module.

    Keeping this module-scoped avoids re-running the Reed-Solomon encoder for
    every test while still providing authentic cryptographic material that
    Verifier.check() can validate.
    """
    fragments = encode(_DATA, n=_N, m=_M, block_id=_BLOCK_ID)
    fpcc = FingerprintedCrossChecksum.generate(fragments)
    fpcc_json = fpcc.to_json()
    return fragments, fpcc_json


@pytest.fixture
def servers() -> list[ServerAddress]:
    return [ServerAddress(server_id=i + 1, port=5000 + i + 1) for i in range(_N)]


@pytest.fixture
def client(servers) -> VeriStoreClient:
    return VeriStoreClient(servers=servers, m=_M)


# ---------------------------------------------------------------------------
# TestClientPut
# ---------------------------------------------------------------------------


class TestClientPut:
    """Tests for VeriStoreClient.put()."""

    def test_put_calls_all_servers(self, client, servers):
        """put() sends exactly one PUT request to each of the n servers."""
        url_map = {
            _fragment_url(servers[i].port, _BLOCK_ID, i): _http_response(200, _put_body(_BLOCK_ID, i))
            for i in range(_N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            client.put(_BLOCK_ID, _DATA)

        put_calls = [c for c in mock_http.request.call_args_list if c.args[0] == "PUT"]
        assert len(put_calls) == _N

    def test_put_returns_block_id(self, client, servers):
        """put() returns the block_id string on success."""
        url_map = {
            _fragment_url(servers[i].port, _BLOCK_ID, i): _http_response(200, _put_body(_BLOCK_ID, i))
            for i in range(_N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            result = client.put(_BLOCK_ID, _DATA)

        assert result == _BLOCK_ID

    def test_put_raises_dispersal_error_when_too_few_succeed(self, client, servers):
        """put() raises DispersalError if fewer than m=3 servers accept (HTTP 200)."""
        # Servers 2-4 return 422 (verification failure).  _request_with_retry
        # returns a 422 response immediately (< 500, no retry), but _put_one
        # treats anything other than 200 as a failure — only 2 successes total.
        url_map = {
            _fragment_url(servers[0].port, _BLOCK_ID, 0): _http_response(200, _put_body(_BLOCK_ID, 0)),
            _fragment_url(servers[1].port, _BLOCK_ID, 1): _http_response(200, _put_body(_BLOCK_ID, 1)),
            _fragment_url(servers[2].port, _BLOCK_ID, 2): _http_response(422, {"detail": "verification failed"}),
            _fragment_url(servers[3].port, _BLOCK_ID, 3): _http_response(422, {"detail": "verification failed"}),
            _fragment_url(servers[4].port, _BLOCK_ID, 4): _http_response(422, {"detail": "verification failed"}),
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            with pytest.raises(DispersalError):
                client.put(_BLOCK_ID, _DATA)


# ---------------------------------------------------------------------------
# TestClientGet
# ---------------------------------------------------------------------------


class TestClientGet:
    """Tests for VeriStoreClient.get()."""

    def test_get_returns_original_data(self, client, servers, encoded):
        """get() decodes and returns the original data when all servers are honest."""
        fragments, fpcc_json = encoded
        url_map = {
            _fragment_url(servers[i].port, _BLOCK_ID, i): _http_response(
                200, _get_body(fragments[i], fpcc_json)
            )
            for i in range(_N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            result = client.get(_BLOCK_ID)

        assert result == _DATA

    def test_get_rejects_corrupt_fragment(self, client, servers, encoded):
        """
        get() skips fragments that fail Verifier.check() and still reconstructs
        the original data from the remaining honest fragments.

        Servers 0 and 1 act as Byzantine faults: they return the fragment data
        XOR-ed with 0xFF, which guarantees a SHA-256 hash mismatch.  Servers
        2, 3, and 4 are honest.  With m=3 honest fragments available, the
        client must succeed and return the original data.
        """
        fragments, fpcc_json = encoded
        url_map = {
            # Byzantine servers — corrupt data, valid fpcc_json
            _fragment_url(servers[0].port, _BLOCK_ID, 0): _http_response(
                200, _get_body(fragments[0], fpcc_json, corrupt=True)
            ),
            _fragment_url(servers[1].port, _BLOCK_ID, 1): _http_response(
                200, _get_body(fragments[1], fpcc_json, corrupt=True)
            ),
            # Honest servers
            _fragment_url(servers[2].port, _BLOCK_ID, 2): _http_response(
                200, _get_body(fragments[2], fpcc_json)
            ),
            _fragment_url(servers[3].port, _BLOCK_ID, 3): _http_response(
                200, _get_body(fragments[3], fpcc_json)
            ),
            _fragment_url(servers[4].port, _BLOCK_ID, 4): _http_response(
                200, _get_body(fragments[4], fpcc_json)
            ),
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            result = client.get(_BLOCK_ID)

        assert result == _DATA

    def test_get_raises_retrieval_error_when_not_enough_valid(self, client, servers, encoded):
        """
        get() raises RetrievalError when all servers return Byzantine fragments
        and the client cannot assemble m=3 verified fragments.
        """
        fragments, fpcc_json = encoded
        url_map = {
            _fragment_url(servers[i].port, _BLOCK_ID, i): _http_response(
                200, _get_body(fragments[i], fpcc_json, corrupt=True)
            )
            for i in range(_N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            with pytest.raises(RetrievalError):
                client.get(_BLOCK_ID)


# ---------------------------------------------------------------------------
# TestClientEdgeCases
# ---------------------------------------------------------------------------


class TestClientEdgeCases:
    """Edge-case coverage for payload handling."""

    def test_put_empty_data_raises_value_error(self, client):
        """Empty payloads are rejected by the encoder (non-empty fragments required)."""
        with pytest.raises(ValueError):
            client.put("empty-block", b"")

    def test_put_get_binary_data_round_trip(self, client, servers):
        """Binary payloads (including all byte values) round-trip correctly."""
        binary_data = bytes(range(256)) * 32  # 8KB binary payload
        block_id = "binary-block"
        fragments = encode(binary_data, n=_N, m=_M, block_id=block_id)
        fpcc_json = FingerprintedCrossChecksum.generate(fragments).to_json()

        url_map: dict[str, MagicMock] = {}
        for i in range(_N):
            url = _fragment_url(servers[i].port, block_id, i)
            body = _get_body(fragments[i], fpcc_json)
            url_map[url] = _http_response(200, body)
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            result = client.get(block_id)

        assert result == binary_data


# ---------------------------------------------------------------------------
# TestClientDelete
# ---------------------------------------------------------------------------


class TestClientDelete:
    """Tests for VeriStoreClient.delete()."""

    def test_delete_sends_to_all_servers(self, client, servers):
        """delete() sends a DELETE request to each of the n servers."""
        url_map = {
            _fragment_url(servers[i].port, _BLOCK_ID, i): _http_response(
                200, {"block_id": _BLOCK_ID, "index": i, "message": "deleted"}
            )
            for i in range(_N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            client.delete(_BLOCK_ID)

        delete_calls = [c for c in mock_http.request.call_args_list if c.args[0] == "DELETE"]
        assert len(delete_calls) == _N

    def test_delete_ignores_404(self, client, servers):
        """delete() does not raise when a server returns 404 (fragment already gone)."""
        url_map = {
            _fragment_url(servers[i].port, _BLOCK_ID, i): _http_response(404, {"detail": "not found"})
            for i in range(_N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            client.delete(_BLOCK_ID)  # must not raise


# ---------------------------------------------------------------------------
# TestClientHealthCheck
# ---------------------------------------------------------------------------


class TestClientHealthCheck:
    """Tests for VeriStoreClient.health_check()."""

    def test_all_healthy(self, client, servers):
        """health_check() returns True for all servers that respond with 200."""
        url_map = {
            f"http://localhost:{servers[i].port}/health": _http_response(
                200, _health_body(servers[i].server_id)
            )
            for i in range(_N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            result = client.health_check()

        assert len(result) == _N
        assert all(result.values())

    def test_some_unreachable(self, client, servers):
        """
        health_check() returns False for servers that are unreachable.

        Servers 0 and 1 raise httpx.RequestError on every attempt (simulating
        a crashed or network-partitioned node).  time.sleep is patched to keep
        the test fast despite _request_with_retry's backoff logic.
        """
        # Servers 2-4 are healthy; 0 and 1 are absent from the url_map so
        # _mock_http raises RequestError for them.
        url_map = {
            f"http://localhost:{servers[i].port}/health": _http_response(
                200, _health_body(servers[i].server_id)
            )
            for i in range(2, _N)
        }
        mock_http = _mock_http(url_map)
        with patch("src.network.client.httpx.Client", return_value=mock_http):
            with patch("src.network.client.time.sleep"):  # skip retry backoff
                result = client.health_check()

        healthy = [sid for sid, ok in result.items() if ok]
        unreachable = [sid for sid, ok in result.items() if not ok]
        assert len(healthy) == 3
        assert len(unreachable) == 2
