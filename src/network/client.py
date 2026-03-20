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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from src.erasure.decoder import decode
from src.erasure.encoder import Fragment, encode
from src.network.protocol import GetFragmentResponse, StoreFragmentRequest
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.verifier import VerificationResult, Verifier


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
            try:
                with httpx.Client(timeout=self.timeout) as http:
                    response = http.put(
                        self._server_url(server, fragment.block_id, fragment.index),
                        json=request_body.model_dump(),
                    )
                    return response.status_code == 200
            except httpx.RequestError:
                return False

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
            try:
                with httpx.Client(timeout=self.timeout) as http:
                    response = http.get(self._server_url(server, block_id, index))
                if response.status_code != 200:
                    return None
                return GetFragmentResponse.model_validate(response.json())
            except (httpx.RequestError, ValidationError, ValueError):
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
                continue
            try:
                fragment_bytes = base64.b64decode(response_model.fragment_data)
            except Exception:
                continue
            report = Verifier.check(response_model.index, fragment_bytes, fpcc)
            if report.result != VerificationResult.CONSISTENT:
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
        # TODO: Send DELETE /fragments/{block_id}/{i} to each server.
        # TODO: Log any unexpected errors but do not raise.
        ...

    def health_check(self) -> dict[int, bool]:
        """Ping all servers and return their availability.

        Returns:
            A dict mapping server_id -> True (healthy) / False (unreachable).
        """
        # TODO: GET /health from each server; catch httpx.RequestError.

        ...

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
