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
import base64
import logging
import os
from pathlib import Path as _Path
from fastapi import FastAPI, HTTPException, Path

from .protocol import (
    StoreFragmentRequest,
    StoreFragmentResponse,
    GetFragmentResponse,
    DeleteFragmentResponse,
    HealthResponse,
)
from ..storage.store import (
    FragmentStore, 
    FragmentNotFoundError,
)
from ..storage.fragment import (
    FragmentRecord, 
    VerificationStatus,
)
from ..storage.metadata import ObjectMetadata
from ..verification.cross_checksum import FingerprintedCrossChecksum
from ..verification.verifier import (
    Verifier, 
    VerificationResult,
)

# Module-level logger.  Each log message embeds server_id in the format
# string so log lines from multiple server processes can be distinguished
# when output is aggregated (e.g. in a shared log file or log collector).
_log = logging.getLogger(__name__)


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
    app = FastAPI(title=f"veri-store server {server_id}")
    store = FragmentStore(f"{data_dir}/server_{server_id}")

    # In-memory fpcc_json cache keyed by (block_id, index).
    # Populated unconditionally on PUT (including INVALID fragments) so that
    # a subsequent GET can return the fpcc alongside the fragment bytes.
    # This bridges a data-model gap: FragmentRecord currently stores only
    # fpcc_digest, not the full JSON.  Once FragmentRecord.to_dict() and
    # from_dict() are implemented to persist fpcc_json on disk, this cache
    # can be removed and get_fragment() can source fpcc_json from the record.

    # TODO: Remove once FragmentRecord stores fpcc_json and the store is fully implemented.
    fpcc_cache: dict[tuple[str, int], str] = {}

    # ------------------------------------------------------------------
    # Route handlers
    # Each is a thin closure that delegates to the standalone helpers below,
    # binding the per-instance store, server_id, and fpcc_cache.
    # ------------------------------------------------------------------

    @app.put("/fragments/{block_id}/{index}")
    def _put(
        body: StoreFragmentRequest,
        block_id: str = Path(min_length=1, description="Block identifier"),
        index: int = Path(ge=0, description="Fragment index (0-based)"),
    ) -> StoreFragmentResponse:
        # Cache fpcc_json before calling put_fragment.  Even if verification
        # fails and put_fragment raises HTTP 422, the fragment is still stored
        # (design intent), so the cache entry must exist for GET to work.

        # TODO: Remove once FragmentRecord stores fpcc_json and the store is fully implemented.
        fpcc_cache[(block_id, index)] = body.fpcc_json
        return put_fragment(block_id, index, body, store, server_id)

    @app.get("/fragments/{block_id}/{index}")
    def _get(
        block_id: str = Path(min_length=1, description="Block identifier"),
        index: int = Path(ge=0, description="Fragment index (0-based)"),
    ) -> GetFragmentResponse:
        response = get_fragment(block_id, index, store)
        # Inject the fpcc_json that was stashed at PUT time.
        # model_copy() (Pydantic v2) returns a new model with only the named
        # field overridden, leaving all other fields unchanged.

        # TODO: Update once FragmentRecord stores fpcc_json and the store is fully implemented.
        return response.model_copy(update={"fpcc_json": fpcc_cache.get((block_id, index), "")})

    @app.delete("/fragments/{block_id}/{index}")
    def _delete(
        block_id: str = Path(min_length=1, description="Block identifier"),
        index: int = Path(ge=0, description="Fragment index (0-based)"),
    ) -> DeleteFragmentResponse:
        # Evict the cached fpcc_json when a fragment is deleted so the cache
        # does not grow without bound during long-running server sessions.
    
        # TODO: Remove once FragmentRecord stores fpcc_json and the store is fully implemented.
        fpcc_cache.pop((block_id, index), None)
        return delete_fragment(block_id, index, store)

    @app.get("/health")
    def _health() -> HealthResponse:
        return get_health(store, server_id)

    return app


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
    # 1. Reject duplicates before doing any I/O.
    #    The store is a write-once model: re-sending the same fragment is an
    #    error rather than an idempotent update.
    if store.has(block_id, index):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Fragment ({block_id}, {index}) already exists "
                f"on server {server_id}."
            ),
        )

    # 2. Decode the fragment bytes from the base64 wire encoding.
    #    All binary data is transmitted as base64 strings because JSON cannot
    #    natively represent arbitrary byte sequences.
    try:
        fragment_bytes = base64.b64decode(body.fragment_data)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid base64 in fragment_data: {exc}",
        )

    # 3. Deserialize the fpcc from its JSON representation.
    #    The fpcc was generated by the client at dispersal time and carries
    #    SHA-256 hashes for all n fragments and GF(256) fingerprints for the
    #    first m fragments, enabling server-side consistency verification.
    try:
        fpcc = FingerprintedCrossChecksum.from_json(body.fpcc_json)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid fpcc_json: {exc}",
        )

    # 4. Run the server-side consistency check (Definition 3.3 of the paper).
    #    Verifier.check() may perform up to two sub-checks:
    #      - Hash check  (all indices): SHA-256(d_i) == fpcc.hashes[i]
    #      - Fingerprint check (i < m): fp(r, d_i) == fpcc.fingerprints[i]
    #    The returned VerificationReport captures which checks ran and why
    #    any failure occurred.
    report = Verifier.check(index, fragment_bytes, fpcc)

    # 5. Map the VerificationResult to a VerificationStatus for persistent
    #    storage, and emit a structured WARNING for any non-CONSISTENT result.
    #
    #    All failure variants (HASH_MISMATCH, FP_MISMATCH, INDEX_ERROR) map
    #    to INVALID.  Only CONSISTENT maps to VALID.
    if report.result == VerificationResult.CONSISTENT:
        status = VerificationStatus.VALID
    else:
        # Log with enough context to identify the offending server, block,
        # and fragment when inspecting aggregated output across all servers.
        # The report.result value names the specific check that failed, and
        # report.detail provides a human-readable explanation.
        _log.warning(
            "[server %d] Verification FAILED for fragment (%s, %d): "
            "result=%s  detail=%s",
            server_id,
            block_id,
            index,
            report.result.value,
            report.detail,
        )
        status = VerificationStatus.INVALID

    # 6. Persist the fragment regardless of verification outcome.
    #    Storing INVALID fragments lets operators retrieve them for
    #    post-incident forensics without re-running the client dispersal.
    #    fpcc_digest is a SHA-256 of the canonical fpcc JSON, providing a
    #    stable reference for re-verification on demand (e.g. during audits).
    record = FragmentRecord(
        index=index,
        data=fragment_bytes,
        block_id=block_id,
        total_n=body.total_n,
        threshold_m=body.threshold_m,
        original_length=body.original_length,
        verification_status=status,
        fpcc_digest=fpcc.digest(),
    )
    store.put(record)

    # 7. Reject INVALID fragments with HTTP 422 *after* persisting them.
    #    The 422 signals to the client that this fragment must not be used
    #    for reconstruction; the fragment remains on disk for debugging.
    if status == VerificationStatus.INVALID:
        raise HTTPException(status_code=422, detail=report.detail)

    return StoreFragmentResponse(
        block_id=block_id,
        index=index,
        verification_status=status.value,
        message=report.detail,
    )

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
    # Fetch the record; surface a 404 if this fragment was never stored.
    try:
        record = store.get(block_id, index)
    except FragmentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Fragment ({block_id}, {index}) not found.",
        )

    # Base64-encode the raw bytes for JSON transport (matching the PUT format).
    fragment_data_b64 = base64.b64encode(record.data).decode()

    # fpcc_json is left empty here; the route handler in create_app._get
    # injects the cached value via model_copy() before sending the response.
    # This separation keeps get_fragment() testable in isolation without a
    # live fpcc_cache.
    return GetFragmentResponse(
        block_id=record.block_id,
        index=record.index,
        fragment_data=fragment_data_b64,
        total_n=record.total_n,
        threshold_m=record.threshold_m,
        original_length=record.original_length,
        fpcc_json="",
        verification_status=record.verification_status.value,
    )


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
    try:
        store.delete(block_id, index) # At this time (3/15), store.delete() is not implemented.
    except FragmentNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Fragment ({block_id}, {index}) not found.",
        )

    return DeleteFragmentResponse(
        block_id=block_id,
        index=index,
        message=f"Fragment ({block_id}, {index}) deleted.",
    )


def get_health(store: FragmentStore, server_id: int) -> HealthResponse:
    """Handle GET /health.

    Args:
        store:     The server's fragment store (used to count stored fragments).
        server_id: This server's ID.

    Returns:
        HealthResponse with status and fragment count.
    """
    # Count all fragment JSON files stored under the server's data directory.
    # This relies on FragmentStore.__init__ having set store.base_dir.
    # getattr with a None default handles the case where store.base_dir is not
    # yet set (its __init__ is still a TODO stub), keeping the health endpoint
    # operational while the rest of the store implementation is in progress.
    base_dir = getattr(store, "base_dir", None)
    try:
        count = sum(1 for _ in _Path(base_dir).rglob("fragment_*.json")) if base_dir else 0
    except OSError:
        count = 0

    return HealthResponse(server_id=server_id, status="ok", fragment_count=count)


# ---------------------------------------------------------------------------
# Module-level default app (for `uvicorn src.network.server:app`)
# ---------------------------------------------------------------------------

# Read server identity from environment variables so uvicorn can import this
# module directly without a CLI wrapper:
#
#   export SERVER_ID=1
#   export DATA_DIR=./data          # optional; defaults to ./data
#   uvicorn src.network.server:app --port 5001

# Where (or when) are these environment variables set?
app = create_app(
    server_id=int(os.environ.get("SERVER_ID", "1")),
    data_dir=os.environ.get("DATA_DIR", "./data"),
)
