"""
server.py -- FastAPI application for a single veri-store storage server.

Each server process is started with a unique server_id (1–n) and a port number.
It owns a FragmentStore rooted at ./data/server_{id}/ and handles:

    PUT  /fragments/{block_id}/{index}  -- receive and store a fragment
    GET  /fragments/{block_id}/{index}  -- return a stored fragment
    DELETE /fragments/{block_id}/{index} -- remove a stored fragment
    GET  /health                         -- liveness / readiness probe

On receipt of a PUT, the server immediately verifies the fragment against the
supplied fpcc.  If verification fails, the server still stores the fragment
(so the client can request it for debugging) but marks it INVALID and returns
HTTP 422.

Run a single server:
    uvicorn src.network.server:app --port 5001
    # or with the CLI wrapper:
    python -m veri-store.server --id 1 --port 5001
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException, Path
from .protocol import (
    StoreFragmentRequest,
    StoreFragmentResponse,
    GetFragmentResponse,
    DeleteFragmentResponse,
    HealthResponse,
)
from ..storage.store import FragmentStore, FragmentNotFoundError
from ..storage.fragment import FragmentRecord, VerificationStatus
from ..storage.metadata import ObjectMetadata
from ..verification.cross_checksum import FingerprintedCrossChecksum
from ..verification.verifier import Verifier, VerificationResult

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(server_id: int, data_dir: str = "./data") -> FastAPI:
    """Create and configure the FastAPI application for one server instance.

    Args:
        server_id: This server's unique integer ID (1-based).
        data_dir:  Root directory for fragment storage.

    Returns:
        A configured FastAPI application instance.
    """
    # TODO: Instantiate FastAPI(title=f"veri-store server {server_id}").
    # TODO: Create FragmentStore(f"{data_dir}/server_{server_id}").
    # TODO: Register all route handlers below.
    # TODO: Return the app instance.
    ...


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def put_fragment(
    block_id: str,
    index: int,
    body: StoreFragmentRequest,
    store: FragmentStore,
    server_id: int,
) -> StoreFragmentResponse:
    """Handle PUT /fragments/{block_id}/{index}.

    Decodes the fragment, verifies it against the fpcc, persists it, and
    returns the verification outcome.

    Args:
        block_id: Data block identifier (from URL path).
        index:    Fragment index (from URL path).
        body:     Validated request body.
        store:    The server's fragment store.
        server_id: This server's ID (for logging).

    Returns:
        StoreFragmentResponse with the verification result.

    Raises:
        HTTPException(422): If fpcc verification fails.
        HTTPException(409): If a fragment for this (block_id, index) already exists.
    """
    # TODO: 1. Decode base64 fragment_data from body.
    # TODO: 2. Deserialize fpcc from body.fpcc_json.
    # TODO: 3. Run Verifier.check(index, fragment_bytes, fpcc).
    # TODO: 4. Map VerificationResult to VerificationStatus.
    # TODO: 5. Construct and persist FragmentRecord.
    # TODO: 6. Return StoreFragmentResponse.
    ...


def get_fragment(
    block_id: str,
    index: int,
    store: FragmentStore,
) -> GetFragmentResponse:
    """Handle GET /fragments/{block_id}/{index}.

    Args:
        block_id: Data block identifier.
        index:    Fragment index.
        store:    The server's fragment store.

    Returns:
        GetFragmentResponse with the fragment data and metadata.

    Raises:
        HTTPException(404): If the fragment is not found.
    """
    # TODO: 1. Call store.get(block_id, index); catch FragmentNotFoundError -> 404.
    # TODO: 2. Base64-encode record.data.
    # TODO: 3. Return GetFragmentResponse.
    ...


def delete_fragment(
    block_id: str,
    index: int,
    store: FragmentStore,
) -> DeleteFragmentResponse:
    """Handle DELETE /fragments/{block_id}/{index}.

    Args:
        block_id: Data block identifier.
        index:    Fragment index.
        store:    The server's fragment store.

    Returns:
        DeleteFragmentResponse confirming deletion.

    Raises:
        HTTPException(404): If the fragment is not found.
    """
    # TODO: 1. Call store.delete(block_id, index); catch FragmentNotFoundError -> 404.
    # TODO: 2. Return DeleteFragmentResponse.
    ...


def get_health(store: FragmentStore, server_id: int) -> HealthResponse:
    """Handle GET /health.

    Args:
        store:     The server's fragment store (used to count stored fragments).
        server_id: This server's ID.

    Returns:
        HealthResponse with status and fragment count.
    """
    # TODO: Count total stored fragments across all blocks.
    # TODO: Return HealthResponse(server_id, "ok", count).
    ...


# ---------------------------------------------------------------------------
# Module-level default app (for `uvicorn src.network.server:app`)
# ---------------------------------------------------------------------------

# TODO: Expose a default `app` instance using environment variables
#       SERVER_ID and DATA_DIR so uvicorn can import it directly.
# app = create_app(server_id=int(os.environ.get("SERVER_ID", "1")))
