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
from fastapi.testclient import TestClient
from pathlib import Path

from src.network.server import create_app
from src.erasure.encoder import encode
from src.verification.cross_checksum import FingerprintedCrossChecksum

_TOKEN = "test-token"


@pytest.fixture
def client(tmp_path: Path):
    """Provide a TestClient backed by a fresh server with temp storage."""
    app = create_app(server_id=1, data_dir=str(tmp_path), token=_TOKEN)
    return TestClient(app, headers={"Authorization": f"Bearer {_TOKEN}"})


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
