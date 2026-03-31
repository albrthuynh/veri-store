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
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path as _Path

from fastapi import FastAPI, HTTPException, Path, Request

from ..storage.fragment import FragmentRecord, VerificationStatus
from ..storage.metadata import ObjectMetadata
from ..storage.store import FragmentNotFoundError, FragmentStore
from ..verification.cross_checksum import FingerprintedCrossChecksum
from ..verification.verifier import VerificationResult, Verifier
from .protocol import (
    DeleteFragmentResponse,
    GetFragmentResponse,
    HealthResponse,
    StoreFragmentRequest,
    StoreFragmentResponse,
)
from ..verification.oracle import RandomOracle

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

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP Requests, with their codes and timing"""

        start_time = time.time()
        response = await call_next(request)
        end_time = time.time()

        time_elapsed_ms = (end_time - start_time) * 1000

        _log.info(
            "[server %d] %s %s → %d (%.0fms)",
            server_id,
            request.method,
            request.url.path,
            response.status_code,
            time_elapsed_ms,
        )

        return response

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

        fragment_size = len(body.fragment_data)
        _log.info(
            "[server %d] Storing fragment: block_id=%s, index=%d, size=%d bytes",
            server_id,
            block_id,
            index,
            fragment_size,
        )

        fpcc_cache[(block_id, index)] = body.fpcc_json
        response = put_fragment(block_id, index, body, store, server_id, fpcc_cache)

        _log.info(
            "[server %d] Stored fragment: block_id=%s, index=%d, status=%s",
            server_id,
            block_id,
            index,
            response.verification_status,
        )

        return response

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
        return response.model_copy(
            update={"fpcc_json": fpcc_cache.get((block_id, index), "")}
        )

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
        response = get_health(store, server_id)
        _log.debug(
            "[server %d] Health check: status=%s, fragments=%d",
            server_id,
            response.status,
            response.fragment_count,
        )
        return response

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
    fpcc_cache: dict[tuple[str, int], str],
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
        fpcc_cache: In-memory cache mapping (block_id, index) to fpcc_json strings, used for idempotency checks when fragments already exist.

    Returns:
        StoreFragmentResponse with the verification result.

    Raises:
        HTTPException(422): If fpcc verification fails.
        HTTPException(409): If a fragment for this (block_id, index) has different content.
    """
    # 1. Reject duplicates before doing any I/O.
    # The store is a write-once model: re-sending the same fragment is an error rather than an idempotent update.
    # For idempotency, if a fragment has the same content -> 200 OK, if not -> 409 Conflict
    if store.has(block_id, index):
        stored = store.get(block_id, index)
        cache_stored_fpcc = fpcc_cache.get((block_id, index))

        # Check if all the data is the same
        # Because if someone sends the same fragment data but with different erasure coding parameters, it's a completely different logical fragment
        metadata_matches = (
            stored.total_n == body.total_n
            and stored.threshold_m == body.threshold_m
            and stored.original_length == body.original_length
        )
        fpcc_matches = cache_stored_fpcc == body.fpcc_json

        try:
            incoming_bytes = base64.b64decode(body.fragment_data)
        except ValueError:
            raise HTTPException(
                status_code=409,
                detail=f"Fragment ({block_id}, {index}) exists with different data",
            )

        incoming_hash = RandomOracle.hash_fragment(incoming_bytes)
        stored_hash = RandomOracle.hash_fragment(stored.data)
        data_matches = incoming_hash == stored_hash

        if metadata_matches and fpcc_matches and data_matches:
            _log.info(
                "[server %d] Idempotent PUT detected: block_id=%s, index=%d, returning existing fragment",
                server_id,
                block_id,
                index,
            )
            return StoreFragmentResponse(
                block_id=block_id,
                index=index,
                verification_status=stored.verification_status.value,
                message=f"Fragment ({block_id}, {index}) already stored (idempotent).",
            )
        else:
            _log.warning(
                "[server %d] Fragment mismatch for PUT: block_id=%s, index=%d, "
                "metadata_match=%s, fpcc_match=%s, data_match=%s",
                server_id,
                block_id,
                index,
                metadata_matches,
                fpcc_matches,
                data_matches,
            )
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Fragment ({block_id}, {index}) already exists with different data"
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
        store.delete(
            block_id, index
        )  # At this time (3/15), store.delete() is not implemented.
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
    """Handle GET /health. Confirms the server is running and attempts a lightweight
    check of the fragment store. Not a comprehensive health check, but sufficient
    for Kubernetes liveness/readiness probes.

    Args:
        store:     The server's fragment store (used to count stored fragments).
        server_id: This server's ID.

    Returns:
        HealthResponse with status and fragment count.
    """
    status = "ok"

    try:
        count = int(store.fragment_count())
    except Exception:
        count = 0
        status = "failed"

    return HealthResponse(server_id=server_id, status=status, fragment_count=count)


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
