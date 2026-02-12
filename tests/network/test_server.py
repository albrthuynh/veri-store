"""
test_server.py -- Integration tests for the FastAPI server endpoints.

Uses FastAPI's TestClient (wraps httpx) to exercise the HTTP layer without
starting a real process.

Covers:
    - PUT /fragments/{block_id}/{index}: happy path, duplicate, invalid fpcc
    - GET /fragments/{block_id}/{index}: happy path, 404
    - DELETE /fragments/{block_id}/{index}: happy path, 404
    - GET /health: returns 200 with correct server_id
"""

import pytest
import base64
from fastapi.testclient import TestClient
from pathlib import Path

# TODO: Import create_app once server.py is implemented.
# from src.network.server import create_app


@pytest.fixture
def client(tmp_path: Path):
    """Provide a TestClient backed by a fresh server with temp storage."""
    # TODO: app = create_app(server_id=1, data_dir=str(tmp_path))
    #       return TestClient(app)
    ...


@pytest.fixture
def valid_store_body():
    """A minimal valid StoreFragmentRequest payload dict."""
    # TODO: frags = encode(b"server test", n=5, m=3)
    #       fpcc = FingerprintedCrossChecksum.generate(frags)
    #       return {
    #           "fragment_data": base64.b64encode(frags[0].data).decode(),
    #           "total_n": 5,
    #           "threshold_m": 3,
    #           "original_length": len(b"server test"),
    #           "fpcc_json": fpcc.to_json(),
    #       }
    ...


class TestPutFragment:
    """Tests for PUT /fragments/{block_id}/{index}."""

    def test_put_valid_fragment_returns_200(self, client, valid_store_body):
        """A valid PUT returns 200 with verification_status=consistent."""
        # TODO: resp = client.put("/fragments/block1/0", json=valid_store_body)
        #       assert resp.status_code == 200
        #       assert resp.json()["verification_status"] == "consistent"
        ...

    def test_put_invalid_fpcc_returns_422(self, client):
        """A PUT with a tampered fragment returns 422."""
        # TODO: tampered_body = {... , "fragment_data": base64.b64encode(b"garbage").decode() ...}
        #       resp = client.put("/fragments/block1/0", json=tampered_body)
        #       assert resp.status_code == 422
        ...


class TestGetFragment:
    """Tests for GET /fragments/{block_id}/{index}."""

    def test_get_stored_fragment_returns_200(self, client, valid_store_body):
        """GET after PUT returns the stored fragment data."""
        # TODO: client.put("/fragments/block1/0", json=valid_store_body)
        #       resp = client.get("/fragments/block1/0")
        #       assert resp.status_code == 200
        #       assert resp.json()["index"] == 0
        ...

    def test_get_missing_fragment_returns_404(self, client):
        """GET for an unknown fragment returns 404."""
        # TODO: resp = client.get("/fragments/missing_block/0")
        #       assert resp.status_code == 404
        ...


class TestDeleteFragment:
    """Tests for DELETE /fragments/{block_id}/{index}."""

    def test_delete_stored_fragment_returns_200(self, client, valid_store_body):
        """DELETE after PUT returns 200; subsequent GET returns 404."""
        # TODO: client.put("/fragments/block1/0", json=valid_store_body)
        #       resp = client.delete("/fragments/block1/0")
        #       assert resp.status_code == 200
        #       assert client.get("/fragments/block1/0").status_code == 404
        ...

    def test_delete_missing_returns_404(self, client):
        """DELETE for an unknown fragment returns 404."""
        # TODO: resp = client.delete("/fragments/no_block/0")
        #       assert resp.status_code == 404
        ...


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        """GET /health returns 200 with server_id=1."""
        # TODO: resp = client.get("/health")
        #       assert resp.status_code == 200
        #       assert resp.json()["server_id"] == 1
        #       assert resp.json()["status"] == "ok"
        ...
