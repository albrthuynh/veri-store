"""
test_server.py -- Integration tests for the FastAPI server endpoints.

Uses FastAPI's TestClient (wraps httpx) to exercise the HTTP layer without
starting a real process.

Covers:
    - PUT /fragments/{block_id}/{index}: happy path, duplicate, invalid fpcc
    - GET /fragments/{block_id}/{index}: happy path, 404
    - DELETE /fragments/{block_id}/{index}: happy path, 404
    - GET /health: returns 200 with correct server_id
    - Auth: unauthenticated requests return 401
"""

import pytest
import base64
import json
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from pathlib import Path

from src.network.server import create_app
from src.erasure.encoder import encode
from src.verification.cross_checksum import FingerprintedCrossChecksum

_TOKEN = "test-token"


@pytest.fixture
def client():
    """Provide a TestClient backed by a fresh server with temp storage."""
    test_root = Path("data/test_runs") / str(uuid.uuid4())
    test_root.mkdir(parents=True, exist_ok=False)

    app = create_app(server_id=1, data_dir=str(test_root), token=_TOKEN)
    client = TestClient(app, headers={"Authorization": f"Bearer {_TOKEN}"})

    try:
        yield client
    finally:
        shutil.rmtree(test_root, ignore_errors=True)


@pytest.fixture
def limited_client():
    """Provide a TestClient with a small rate limit for limiter tests."""
    test_root = Path("data/test_runs") / str(uuid.uuid4())
    test_root.mkdir(parents=True, exist_ok=False)

    app = create_app(
        server_id=1,
        data_dir=str(test_root),
        token=_TOKEN,
        rate_limit_max_requests=2,
        rate_limit_window_seconds=60.0,
    )
    client = TestClient(app, headers={"Authorization": f"Bearer {_TOKEN}"})

    try:
        yield client
    finally:
        shutil.rmtree(test_root, ignore_errors=True)


@pytest.fixture
def valid_store_body():
    """A minimal valid StoreFragmentRequest payload dict."""
    frags = encode(b"server test", n=5, m=3, block_id="block1")
    fpcc = FingerprintedCrossChecksum.generate(frags)
    return {
        "fragment_data": base64.b64encode(frags[0].data).decode(),
        "total_n": 5,
        "threshold_m": 3,
        "original_length": len(b"server test"),
        "fpcc_json": fpcc.to_json(),
    }

def test_create_app_without_token_raises():
    """Creating the app with an empty API token should raise an error."""
    with pytest.raises(ValueError, match="API token must be provided for authentication"):
        create_app(server_id=1, data_dir="/tmp", token="")

class TestPutFragment:
    """Tests for PUT /fragments/{block_id}/{index}."""

    def test_put_valid_fragment_returns_200(self, client, valid_store_body):
        """A valid PUT returns 200 with verification_status=valid."""
        resp = client.put("/fragments/block1/0", json=valid_store_body)
        assert resp.status_code == 200
        assert resp.json()["verification_status"] == "valid"

    def test_put_invalid_fpcc_returns_422(self, client, valid_store_body):
        """A PUT with tampered fragment bytes returns 422."""
        tampered = {**valid_store_body, "fragment_data": base64.b64encode(b"garbage").decode()}
        resp = client.put("/fragments/block1/0", json=tampered)
        assert resp.status_code == 422

    def test_put_missing_fragment_data_returns_422(self, client, valid_store_body):
        """A PUT missing fragment_data is rejected by request validation."""
        invalid_body = dict(valid_store_body)
        invalid_body.pop("fragment_data")

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_extra_field_returns_422(self, client, valid_store_body):
        """A PUT with unexpected fields is rejected when extra='forbid'."""
        invalid_body = {**valid_store_body, "unexpected_field": "should not be allowed"}

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_threshold_greater_than_total_returns_422(self, client, valid_store_body):
        """A PUT with threshold_m > total_n is rejected by model validation."""
        invalid_body = {**valid_store_body, "total_n": 3, "threshold_m": 4}

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_empty_fragment_data_returns_422(self, client, valid_store_body):
        """A PUT with empty fragment_data is rejected by model validation."""
        invalid_body = {**valid_store_body, "fragment_data": ""}

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_whitespace_fpcc_json_returns_422(self, client, valid_store_body):
        """A PUT with blank fpcc_json is rejected after whitespace stripping."""
        invalid_body = {**valid_store_body, "fpcc_json": "   "}

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_invalid_base64_returns_422(self, client, valid_store_body):
        """A PUT with malformed base64 is rejected by request validation."""
        invalid_body = {**valid_store_body, "fragment_data": "not-valid-base64!!!"}

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_empty_decoded_fragment_returns_422(self, client, valid_store_body):
        """A PUT whose fragment_data decodes to zero bytes is rejected."""
        invalid_body = {**valid_store_body, "fragment_data": base64.b64encode(b"").decode()}

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_invalid_fpcc_json_shape_returns_422(self, client, valid_store_body):
        """A PUT with malformed fpcc_json is rejected by request validation."""
        invalid_body = {
            **valid_store_body,
            "fpcc_json": json.dumps({"hashes": [], "r": 5}),
        }

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_invalid_fpcc_json_syntax_returns_422(self, client, valid_store_body):
        """A PUT with non-JSON fpcc_json is rejected by request validation."""
        invalid_body = {**valid_store_body, "fpcc_json": "{not valid json}"}

        resp = client.put("/fragments/block1/0", json=invalid_body)

        assert resp.status_code == 422

    def test_put_idempotent_returns_200(self, client, valid_store_body):
        """Re-sending the identical fragment returns 200 (idempotent)."""
        client.put("/fragments/block1/0", json=valid_store_body)
        resp = client.put("/fragments/block1/0", json=valid_store_body)
        assert resp.status_code == 200

    def test_put_duplicate_different_data_returns_409(self, client, valid_store_body):
        """Re-sending a different fragment for the same (block_id, index) returns 409."""
        client.put("/fragments/block1/0", json=valid_store_body)
        different = {**valid_store_body, "original_length": valid_store_body["original_length"] + 1}
        resp = client.put("/fragments/block1/0", json=different)
        assert resp.status_code == 409

    def test_put_unauthenticated_returns_401(self, client, valid_store_body):
        """A PUT without a valid token returns 401."""
        resp = client.put(
            "/fragments/block1/0",
            json=valid_store_body,
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401


class TestGetFragment:
    """Tests for GET /fragments/{block_id}/{index}."""

    def test_get_stored_fragment_returns_200(self, client, valid_store_body):
        """GET after PUT returns the stored fragment data."""
        client.put("/fragments/block1/0", json=valid_store_body)
        resp = client.get("/fragments/block1/0")
        assert resp.status_code == 200
        assert resp.json()["index"] == 0
        assert resp.json()["block_id"] == "block1"

    def test_get_missing_fragment_returns_404(self, client):
        """GET for an unknown fragment returns 404."""
        resp = client.get("/fragments/missing_block/0")
        assert resp.status_code == 404

    def test_get_unauthenticated_returns_401(self, client):
        """A GET without a valid token returns 401."""
        resp = client.get("/fragments/block1/0", headers={"Authorization": "Bearer wrong-token"})
        assert resp.status_code == 401


class TestDeleteFragment:
    """Tests for DELETE /fragments/{block_id}/{index}."""

    def test_delete_stored_fragment_returns_200(self, client, valid_store_body):
        """DELETE after PUT returns 200; subsequent GET returns 404."""
        client.put("/fragments/block1/0", json=valid_store_body)
        resp = client.delete("/fragments/block1/0")
        assert resp.status_code == 200
        assert client.get("/fragments/block1/0").status_code == 404

    def test_delete_missing_returns_404(self, client):
        """DELETE for an unknown fragment returns 404."""
        resp = client.delete("/fragments/no_block/0")
        assert resp.status_code == 404

    def test_delete_unauthenticated_returns_401(self, client):
        """A DELETE without a valid token returns 401."""
        resp = client.delete("/fragments/block1/0", headers={"Authorization": "Bearer wrong-token"})
        assert resp.status_code == 401


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        """GET /health returns 200 with server_id=1."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["server_id"] == 1
        assert resp.json()["status"] == "ok"

    def test_health_unauthenticated_returns_200(self, client):
        """GET /health is publicly accessible without a token."""
        resp = client.get("/health", headers={"Authorization": ""})
        assert resp.status_code == 200


class TestRateLimiting:
    """Tests for per-client request rate limiting."""

    def test_put_rate_limit_exceeded_returns_429(self, limited_client, valid_store_body):
        """The third request within the active window is rejected with 429."""
        resp1 = limited_client.put("/fragments/block1/0", json=valid_store_body)
        resp2 = limited_client.put("/fragments/block1/0", json=valid_store_body)
        resp3 = limited_client.put("/fragments/block1/0", json=valid_store_body)

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp3.status_code == 429

    def test_rate_limited_response_includes_retry_after_header(
        self, limited_client, valid_store_body
    ):
        """A rate-limited response should include Retry-After."""
        limited_client.put("/fragments/block1/0", json=valid_store_body)
        limited_client.put("/fragments/block1/0", json=valid_store_body)
        resp = limited_client.put("/fragments/block1/0", json=valid_store_body)

        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_health_is_not_rate_limited(self, limited_client):
        """Health checks remain available even after the client exceeds the limit."""
        resp1 = limited_client.get("/health")
        resp2 = limited_client.get("/health")
        resp3 = limited_client.get("/health")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp3.status_code == 200


class TestConcurrentAccess:
    def test_concurrent_puts_to_same_fragment_are_idempotent(self, client, valid_store_body):
        path = "/fragments/concurrent_block/0"
        workers = 10

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = []
            for _ in range(workers):
                futures.append(pool.submit(client.put, path, json=valid_store_body))
            responses = []
            for future in as_completed(futures):
                responses.append(future.result())

        assert len(responses) == workers
        for resp in responses:
            assert resp.status_code == 200
        assert client.get(path).status_code == 200

    def test_concurrent_gets_from_same_fragment_return_consistent_data(
        self, client, valid_store_body
    ):
        path = "/fragments/concurrent_block/0"
        put_resp = client.put(path, json=valid_store_body)
        assert put_resp.status_code == 200

        workers = 10
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = []
            for _ in range(workers):
                futures.append(pool.submit(client.get, path))
            responses = []
            for future in as_completed(futures):
                responses.append(future.result())

        assert len(responses) == workers
        payloads: list[str] = []
        for resp in responses:
            assert resp.status_code == 200
            payloads.append(resp.json()["fragment_data"])
        for payload in payloads:
            assert payload == payloads[0]


class TestSecurityHeaders:
    """Tests for security-related response headers."""

    def _assert_security_headers(self, response) -> None:
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Cache-Control"] == "no-store"
        assert response.headers["Pragma"] == "no-cache"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert (
            response.headers["Content-Security-Policy"]
            == "default-src 'none'; frame-ancestors 'none'"
        )

    def test_success_response_includes_security_headers(self, client, valid_store_body):
        """A successful fragment PUT includes the configured security headers."""
        resp = client.put("/fragments/block1/0", json=valid_store_body)

        assert resp.status_code == 200
        self._assert_security_headers(resp)

    def test_health_response_includes_security_headers(self, client):
        """The public health endpoint also includes security headers."""
        resp = client.get("/health")

        assert resp.status_code == 200
        self._assert_security_headers(resp)

    def test_error_response_includes_security_headers(self, client):
        """Security headers are present on error responses as well."""
        resp = client.get("/fragments/missing_block/0")

        assert resp.status_code == 404
        self._assert_security_headers(resp)
