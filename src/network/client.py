"""
client.py -- HTTP client implementing the veri-store dispersal and retrieval protocols.

The client is the entry point for application code (and the CLI).  It:

    Dispersal  (PUT):
        1. Erasure-encode the data into n fragments.
        2. Generate the fingerprinted cross-checksum (fpcc).
        3. Send each fragment to its designated server in parallel.
        4. Confirm that at least m servers accepted without error.

    Retrieval  (GET):
        1. Request fragment i from server i for all i in [0, n).
        2. Collect the first m successful responses.
        3. Verify each returned fragment against the fpcc.
        4. Decode the m fragments to recover the original data.

    Deletion   (DELETE):
        1. Send DELETE /fragments/{block_id}/{i} to all n servers.

The client does *not* trust servers; it re-verifies every retrieved fragment
before passing data to the caller.
"""

from __future__ import annotations

import base64
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from src.erasure.decoder import decode
from src.erasure.encoder import Fragment, encode
from src.network.protocol import GetFragmentResponse, StoreFragmentRequest
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.verifier import VerificationResult, Verifier

_log = logging.getLogger(__name__)

# These can be added to VeriStoreClient.__init__ if desired, but will hardcode for now.
_MAX_ATTEMPTS = 3  # Max attempts allowed for transient HTTP failures
_BACKOFF = 0.5  # Backoff time in seconds between retries

@dataclass
class ServerAddress:
    """Address of a single veri-store server.

    Attributes:
        server_id (int): Server index (1-based, matches fragment index).
        host (str):      Hostname or IP address.
        port (int):      TCP port.
    """

    server_id: int
    host: str = "localhost"
    port: int = 5001

    @property
    def base_url(self) -> str:
        """Construct the base URL for this server."""
        return f"http://{self.host}:{self.port}"


class VeriStoreClient:
    """High-level client for the veri-store dispersal/retrieval protocol.

    Attributes:
        servers (list[ServerAddress]): Addresses of all n storage servers.
        m (int): Reconstruction threshold (minimum fragments needed).
        timeout (float): HTTP request timeout in seconds.
    """

    def __init__(
        self,
        servers: list[ServerAddress],
        m: int = 3,
        timeout: float = 5.0,
    ) -> None:
        """Initialise the client.

        Args:
            servers: List of server addresses (length == n).
            m:       Reconstruction threshold (default 3).
            timeout: Per-request HTTP timeout in seconds (default 5.0).
        """
        if m <= 0:
            raise ValueError("m must be >= 1")
        if len(servers) < m:
            raise ValueError("len(servers) must be >= m")
        if timeout <= 0:
            raise ValueError("timeout must be > 0")

        self.servers = servers
        self.m = m
        self.timeout = timeout

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        json: dict | None = None,
    ) -> httpx.Response | None:
        """Helper method to send an HTTP request with retry logic for transient failures."""
        delay = _BACKOFF

        for attempt in range(_MAX_ATTEMPTS):
            try:
                with httpx.Client(timeout=self.timeout) as http:
                    response = http.request(method, url, json=json)
                
                if response.status_code < 500:
                    return response
            except httpx.RequestError:
                pass

            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(delay)
                delay = delay + _BACKOFF
        
        return None

    def put(self, block_id: str, data: bytes) -> str:
        """Encode data and disperse fragments to all servers.

        Args:
            block_id: User-supplied key for this object.  Must be unique.
            data:     Raw bytes to store.

        Returns:
            The block_id confirming successful dispersal.

        Raises:
            DispersalError: If fewer than m servers accepted the fragment.
        """
        fragments = encode(data, n=len(self.servers), m=self.m, block_id=block_id)
        fpcc = FingerprintedCrossChecksum.generate(fragments)
        fpcc_json = fpcc.to_json()

        def _put_one(server: ServerAddress, fragment: Fragment) -> bool:
            request_body = StoreFragmentRequest(
                fragment_data=base64.b64encode(fragment.data).decode(),
                total_n=fragment.total_n,
                threshold_m=fragment.threshold_m,
                original_length=fragment.original_length,
                fpcc_json=fpcc_json,
            )
            # try:
            #     with httpx.Client(timeout=self.timeout) as http:
            #         response = http.put(
            #             self._server_url(server, fragment.block_id, fragment.index),
            #             json=request_body.model_dump(),
            #         )
            #         return response.status_code == 200
            # except httpx.RequestError:
            #     return False
            response = self._request_with_retry(
                "PUT",
                self._server_url(server, fragment.block_id, fragment.index),
                json=request_body.model_dump(),
            )

            if response is None: # All retries failed
                return False
            return response.status_code == 200

        successes = 0
        with ThreadPoolExecutor(max_workers=len(self.servers)) as pool:
            futures = [
                pool.submit(_put_one, server, fragment)
                for server, fragment in zip(self.servers, fragments)
            ]
            for future in as_completed(futures):
                if future.result():
                    successes += 1

        if successes < self.m:
            raise DispersalError(
                f"Dispersal failed: only {successes}/{len(self.servers)} servers accepted fragments."
            )

        return fragments[0].block_id

    def get(self, block_id: str) -> bytes:
        """Retrieve and reconstruct the original data for a block.

        Args:
            block_id: The key supplied at PUT time.

        Returns:
            The original data bytes.

        Raises:
            RetrievalError: If fewer than m fragments can be retrieved or
                            verified.
        """

        def _get_one(server: ServerAddress, index: int) -> GetFragmentResponse | None:
            # try:
            #     with httpx.Client(timeout=self.timeout) as http:
            #         response = http.get(self._server_url(server, block_id, index))
            #     if response.status_code != 200:
            #         return None
            #     return GetFragmentResponse.model_validate(response.json())
            # except (httpx.RequestError, ValidationError, ValueError):
            #     return None
            
            response = self._request_with_retry(
                "GET",
                self._server_url(server, block_id, index),
            )

            if response is None or response.status_code != 200: # All retries failed or non-200 response
                return None
            
            try:
                return GetFragmentResponse.model_validate(response.json())
            except (ValidationError, ValueError):
                return None

        successful_responses: list[GetFragmentResponse] = []
        with ThreadPoolExecutor(max_workers=len(self.servers)) as pool:
            futures = [
                pool.submit(_get_one, server, index)
                for index, server in enumerate(self.servers)
            ]
            for future in as_completed(futures):
                response_model = future.result()
                if response_model is not None:
                    successful_responses.append(response_model)

        if not successful_responses:
            raise RetrievalError("Retrieval failed: no servers returned a fragment.")

        base_fpcc_json = successful_responses[0].fpcc_json

        try:
            fpcc = FingerprintedCrossChecksum.from_json(base_fpcc_json)
        except Exception as exc:  # pragma: no cover - defensive parse guard
            raise RetrievalError(
                f"Retrieval failed: invalid fpcc from server response ({exc})."
            ) from exc

        verified_fragments: list[Fragment] = []
        for response_model in successful_responses:
            if response_model.fpcc_json != base_fpcc_json:
                _log.warning(
                    "FPCC mismatch in server response for block_id %s, index %d; fragment untrusted, skipping.",
                    block_id,
                    response_model.index,
                )
                continue

            try:
                fragment_bytes = base64.b64decode(response_model.fragment_data)
            except Exception:
                _log.warning(
                    "Malformed fragment data in server response for block_id %s, index %d.",
                    block_id,
                    response_model.index,
                )
                continue
            report = Verifier.check(response_model.index, fragment_bytes, fpcc)
            if report.result != VerificationResult.CONSISTENT:
                _log.warning(
                    "Verification FAILED for fragment (%s, %d): "
                    "result=%s  detail=%s",
                    block_id,
                    response_model.index,
                    report.result.value,
                    report.detail,
                )
                continue

            verified_fragments.append(
                Fragment(
                    index=response_model.index,
                    data=fragment_bytes,
                    block_id=response_model.block_id,
                    total_n=response_model.total_n,
                    threshold_m=response_model.threshold_m,
                    original_length=response_model.original_length,
                )
            )
            if len(verified_fragments) >= self.m:
                break

        if len(verified_fragments) < self.m:
            raise RetrievalError(
                f"Retrieval failed: only {len(verified_fragments)} verified fragments available; need {self.m}."
            )

        try:
            return decode(verified_fragments)
        except Exception as exc:
            raise RetrievalError(f"Retrieval failed during decode: {exc}") from exc

    def delete(self, block_id: str) -> None:
        """Request deletion of a stored block from all servers.

        Sends DELETE requests to all servers; ignores 404 responses (fragment
        may have already been deleted or never reached a server).

        Args:
            block_id: The key of the block to delete.
        """
        def _delete_one(server: ServerAddress, index: int) -> None:
            # try:
            #     with httpx.Client(timeout=self.timeout) as http:
            #         response = http.delete(self._server_url(server, block_id, index))
            #     if response.status_code in (200, 404):
            #         return
            #     _log.warning(
            #         "DELETE unexpected status from server %s (%s): %s",
            #         server.server_id,
            #         self._server_url(server, block_id, index),
            #         response.status_code,
            #     )
            # except httpx.RequestError as exc:
            #     _log.warning(
            #         "DELETE request error for server %s (%s): %s",
            #         server.server_id,
            #         self._server_url(server, block_id, index),
            #         exc,
            #     )
            response = self._request_with_retry(
                "DELETE",
                self._server_url(server, block_id, index)
            )

            if response is None:
                _log.warning(
                    "Delete request failed after retries for server %s (%s).",
                    server.server_id,
                    self._server_url(server, block_id, index),
                )
                return

            if response.status_code in (200, 404):
                return
            
            _log.warning(
                "Delete unexpected status from server %s (%s): %s",
                server.server_id,
                self._server_url(server, block_id, index),
                response.status_code,
            )

        with ThreadPoolExecutor(max_workers=len(self.servers)) as pool:
            futures = [
                pool.submit(_delete_one, server, index)
                for index, server in enumerate(self.servers)
            ]
            for future in as_completed(futures):
                future.result()

    def health_check(self) -> dict[int, bool]:
        """Ping all servers and return their availability.

        Returns:
            A dict mapping server_id -> True (healthy) / False (unreachable).
        """
        def _health_one(server: ServerAddress) -> tuple[int, bool]:
            # try:
            #     with httpx.Client(timeout=self.timeout) as http:
            #         response = http.get(f"{server.base_url}/health")
            #     return server.server_id, response.status_code == 200
            # except httpx.RequestError:
            #     return server.server_id, False
            response = self._request_with_retry(
                "GET",
                f"{server.base_url}/health",
            )
            if response is None:
                return server.server_id, False
            
            return server.server_id, response.status_code == 200

        results: dict[int, bool] = {}
        with ThreadPoolExecutor(max_workers=len(self.servers)) as pool:
            futures = [pool.submit(_health_one, server) for server in self.servers]
            for future in as_completed(futures):
                server_id, healthy = future.result()
                results[server_id] = healthy
        return results

    def _server_url(self, server: ServerAddress, block_id: str, index: int) -> str:
        """Build the fragment endpoint URL for a given server.

        Args:
            server:   The target server.
            block_id: Data block identifier.
            index:    Fragment index.

        Returns:
            Full URL string, e.g. "http://localhost:5001/fragments/abc123/0".
        """
        return f"{server.base_url}/fragments/{block_id}/{index}"


class DispersalError(RuntimeError):
    """Raised when fewer than m servers acknowledged a PUT."""


class RetrievalError(RuntimeError):
    """Raised when the client cannot assemble m verified fragments for a GET."""
