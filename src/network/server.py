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

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse

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
from .rate_limit import SlidingWindowRateLimiter

# Module-level logger.  Each log message embeds server_id in the format
# string so log lines from multiple server processes can be distinguished
# when output is aggregated (e.g. in a shared log file or log collector).
_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(
    server_id: int,
    data_dir: str = "./data",
    byzantine_indices: frozenset[int] = frozenset(),
    token: str = "",
    rate_limit_max_requests: int = 60,
    rate_limit_window_seconds: float = 60.0,
) -> FastAPI:
    """Create and configure the FastAPI application for one server instance.

    Args:
        server_id:         This server's unique integer ID (1-based).
        data_dir:          Root directory for fragment storage.
        byzantine_indices: Fragment indices for which this server will return
                           deliberately corrupted data on GET, simulating a
                           Byzantine-faulty server.  All other behaviour
                           (PUT, DELETE, health) is unaffected.  Defaults to
                           the empty set (honest server).
        token:             API token for authentication with clients.
        rate_limit_max_requests: Maximum number of allowed requests per client within the rate limit window.
        rate_limit_window_seconds: Length of the rate limit window in seconds.

    Returns:
        A configured FastAPI application instance.
    """
    if not token:
        raise ValueError("API token must be provided for authentication")

    app = FastAPI(title=f"veri-store server {server_id}")
    store = FragmentStore(f"{data_dir}/server_{server_id}")
    
    rate_limiter = SlidingWindowRateLimiter(
        max_requests=rate_limit_max_requests,
        window_seconds=rate_limit_window_seconds
    )

    _api_token = token
    _bearer = HTTPBearer()

    def verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> None:
        if credentials.credentials != _api_token:
            raise HTTPException(
                status_code=401, 
                detail="Invalid or missing token"
            )

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
    
    def get_client_key(request: Request) -> str:
        auth_header = request.headers.get("Authorization", "").strip()

        if auth_header.startswith("Bearer "):
            token_value = auth_header.removeprefix("Bearer ").strip()

            if token_value:
                return f"token:{token_value}"
            
        client_host = request.client.host if request.client is not None else "unknown"
        return f"ip:{client_host}"
    
    @app.middleware("http")
    async def enforce_rate_limit(request: Request, call_next):
        # Keep /health exempt so liveness/readiness probes can't be throttled.
        if request.url.path == "/health":
            return await call_next(request)
        
        client_key = get_client_key(request)
        decision = rate_limiter.check(client_key)

        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry later."},
                headers={
                    "Retry-After": str(decision.retry_after_seconds or 1),
                    "X-RateLimit-Limit": str(rate_limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        
        response = await call_next(request)

        # These headers are optional but useful to clients.
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        if decision.retry_after_seconds is not None:
            response.headers["Retry-After"] = str(decision.retry_after_seconds)
        
        return response

    # ------------------------------------------------------------------
    # Route handlers
    # Each is a thin closure that delegates to the standalone helpers below,
    # binding the per-instance store and server_id.
    # ------------------------------------------------------------------

    @app.put("/fragments/{block_id}/{index}")
    def _put(
        body: StoreFragmentRequest,
        block_id: str = Path(min_length=1, description="Block identifier"),
        index: int = Path(ge=0, description="Fragment index (0-based)"),
        _: None = Depends(verify_token),
    ) -> StoreFragmentResponse:

        fragment_size = len(body.fragment_data)
        _log.info(
            "[server %d] Storing fragment: block_id=%s, index=%d, size=%d bytes",
            server_id,
            block_id,
            index,
            fragment_size,
        )

        response = put_fragment(block_id, index, body, store, server_id)

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
        _: None = Depends(verify_token),
    ) -> GetFragmentResponse:
        response = get_fragment(block_id, index, store)

        # Byzantine fault injection: if this index is in byzantine_indices,
        # corrupt the fragment bytes before returning them.  Every byte is
        # XOR-ed with 0xFF, guaranteeing a SHA-256 hash mismatch that the
        # client's Verifier.check() call will catch and reject.
        if index in byzantine_indices:
            original_bytes = base64.b64decode(response.fragment_data)
            corrupted_bytes = bytes(b ^ 0xFF for b in original_bytes)
            _log.warning(
                "[server %d] BYZANTINE fault injected for fragment (%s, %d): "
                "returning %d corrupted bytes",
                server_id,
                block_id,
                index,
                len(corrupted_bytes),
            )
            response = response.model_copy(
                update={"fragment_data": base64.b64encode(corrupted_bytes).decode()}
            )

        return response

    @app.delete("/fragments/{block_id}/{index}")
    def _delete(
        block_id: str = Path(min_length=1, description="Block identifier"),
        index: int = Path(ge=0, description="Fragment index (0-based)"),
        _: None = Depends(verify_token),
    ) -> DeleteFragmentResponse:

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
    """
    # 1. Reject duplicates before doing any I/O.
    # The store is a write-once model: re-sending the same fragment is an error rather than an idempotent update.
    # For idempotency, if a fragment has the same content -> 200 OK, if not -> 409 Conflict
    if store.has(block_id, index):
        stored = store.get(block_id, index)

        # Check if all the data is the same
        # Because if someone sends the same fragment data but with different
        # erasure coding parameters, it's a completely different logical fragment
        metadata_matches = (
            stored.total_n == body.total_n
            and stored.threshold_m == body.threshold_m
            and stored.original_length == body.original_length
        )
        fpcc_matches = stored.fpcc_json == body.fpcc_json

        # StoreFragmentRequest.validate_payload_structure() validates base64 encoding.
        incoming_bytes = base64.b64decode(body.fragment_data)

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
    # StoreFragmentRequest.validate_payload_structure() validates the base64 encoding.
    fragment_bytes = base64.b64decode(body.fragment_data)

    # 3. Deserialize the fpcc from its JSON representation.
    #    The fpcc was generated by the client at dispersal time and carries
    #    SHA-256 hashes for all n fragments and GF(256) fingerprints for the
    #    first m fragments, enabling server-side consistency verification.
    # StoreFragmentRequest.validate_payload_structure() validates the shape
    # of the fpcc_json.
    fpcc = FingerprintedCrossChecksum.from_json(body.fpcc_json)

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
        fpcc_json=body.fpcc_json,
    )
    store.put(record)

    # 7. Reject INVALID fragments with HTTP 422 *after* persisting them.
    #    The 422 signals to the client that this fragment must not be used
    #    for reconstruction; the fragment remains on disk for debugging.
    if status == VerificationStatus.INVALID:
        raise HTTPException(
            status_code=422, 
            detail=report.detail
        )

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

    return GetFragmentResponse(
        block_id=record.block_id,
        index=record.index,
        fragment_data=fragment_data_b64,
        total_n=record.total_n,
        threshold_m=record.threshold_m,
        original_length=record.original_length,
        fpcc_json=record.fpcc_json or "",  # Should always be present, but default to empty string if not.
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
# BYZANTINE_INDICES: comma-separated fragment indices this server should
# corrupt on GET, e.g. "0,2".  Empty string (the default) means honest.
_byzantine_env = os.environ.get("BYZANTINE_INDICES", "")
_byzantine_indices: frozenset[int] = (
    frozenset(int(i) for i in _byzantine_env.split(",") if i.strip())
    if _byzantine_env.strip()
    else frozenset()
)

def _create_default_fastapi_app() -> FastAPI:
    """Create the default FastAPI app using environment variables for configuration."""
    token = os.environ.get("VERI_STORE_TOKEN", "")
    if not token:
        raise ValueError("API token must be provided for authentication")
    
    return create_app(
        server_id=int(os.environ.get("SERVER_ID", "1")),
        data_dir=os.environ.get("DATA_DIR", "./data"),
        byzantine_indices=_byzantine_indices,
        token=token,
    )

class LazyServerApp:
    """ASGI application that lazily initializes the FastAPI app on first request."""
    def __init__(self) -> None:
        self._fastapi_app: FastAPI | None = None
    
    def _get_app(self) -> FastAPI:
        if self._fastapi_app is None:
            self._fastapi_app = _create_default_fastapi_app()
        return self._fastapi_app
    
    async def __call__(self, scope, receive, send) -> None:
        fastapi_app = self._get_app()
        await fastapi_app(scope, receive, send)

app = LazyServerApp()
