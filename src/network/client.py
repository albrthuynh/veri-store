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
import asyncio
import base64
import logging
import httpx
from dataclasses import dataclass

from ..erasure.decoder import decode
from ..erasure.encoder import Fragment, encode
from ..verification.cross_checksum import FingerprintedCrossChecksum
from ..verification.verifier import VerificationResult, Verifier


_log = logging.getLogger(__name__)


@dataclass
class ServerAddress:
    """Address of a single veri-store server.

    Attributes:
        server_id (int): Server index (1-based, matches fragment index).
        host (str):      Hostname or IP address.
        port (int):      TCP port.
    """
    server_id: int
    port: int
    host: str = "localhost"

    def __post_init__(self) -> None:
        """Validate the server address fields."""
        errors = []

        if not isinstance(self.server_id, int) or self.server_id < 1:
            errors.append(
                f"Invalid server_id: {self.server_id}. Must be an integer >= 1."
            )

        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            errors.append(
                f"Invalid port number: {self.port}. Must be an integer between 1 and 65535."
            )

        if errors:
            raise ValueError("\n".join(errors))

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
        """Validate and initialise the client.

        Args:
            servers: List of server addresses (length == n).
            m:       Reconstruction threshold (default 3).
            timeout: Per-request HTTP timeout in seconds (default 5.0).
        """
        errors = []
        if (servers is None) or (not isinstance(servers, list)) or (len(servers) <= 0):
            errors.append("servers must be a non-empty list of ServerAddress objects.")
        elif not all(isinstance(s, ServerAddress) for s in servers):
            errors.append("All items in servers must be instances of ServerAddress.")

        if not isinstance(m, int) or m <= 0:
            errors.append("m must be a positive integer.")

        if isinstance(servers, list) and isinstance(m, int) and len(servers) < m:
            errors.append(f"Number of servers (n={len(servers)}) must be >= m ({m}).")

        if not isinstance(timeout, (int, float)) or timeout <= 0:
            errors.append("Timeout must be a positive number.")

        if errors:
            raise ValueError("\n".join(errors))

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

        async def post_fragment(
            client: httpx.AsyncClient,
            server: ServerAddress,
            fragment,
        ) -> bool:
            try:
                response = await client.put(
                    self._server_url(server, block_id, fragment.index),
                    json={
                        "fragment_data": base64.b64encode(fragment.data).decode("ascii"),
                        "total_n": fragment.total_n,
                        "threshold_m": fragment.threshold_m,
                        "original_length": fragment.original_length,
                        "fpcc_json": fpcc_json,
                    },
                )
                return response.is_success
            except httpx.RequestError:
                return False

        async def disperse() -> int:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                results = await asyncio.gather(
                    *(
                        post_fragment(client, server, fragment)
                        for server, fragment in zip(self.servers, fragments)
                    )
                )
            return sum(results)

        success_count = asyncio.run(disperse())
        if success_count < self.m:
            raise DispersalError(
                f"Dispersal failed: only {success_count}/{len(self.servers)} servers accepted fragments; need at least {self.m}."
            )
        return block_id

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
        async def get_fragment(
            client: httpx.AsyncClient,
            server: ServerAddress,
            index: int,
        ) -> dict | None:
            try:
                response = await client.get(
                    self._server_url(server, block_id, index)
                )
                if not response.is_success:
                    return None
                return response.json()
            except (httpx.RequestError, ValueError):
                return None
            
        async def retrieve_fragments() -> list[dict]:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                responses = await asyncio.gather(
                    *(
                        get_fragment(client, server, index)
                        for index, server in enumerate(self.servers)
                    )
                )
            return [response for response in responses if response is not None]
        
        fragment_responses = asyncio.run(retrieve_fragments())

        if len(fragment_responses) < self.m:
            raise RetrievalError(
                f"Retrieval failed: only {len(fragment_responses)}/{len(self.servers)} servers responded with fragments; need at least {self.m}."
            )
        
        fpcc = None
        for response in fragment_responses:
            try:
                fpcc = FingerprintedCrossChecksum.from_json(response["fpcc_json"])
                break
            except (KeyError, ValueError, TypeError):
                continue
        
        if fpcc is None:
            raise RetrievalError(
                "Retrieval failed: no valid fpcc found in server responses; cannot verify fragments."
            )

        # Build the list of verified fragments until either every fragment is tested or we have m verified fragments.
        verified_fragments = []

        for response in fragment_responses:
            try:
                fragment_data = base64.b64decode(response["fragment_data"])
                index = response["index"]
            except (KeyError, ValueError, TypeError):
                continue

            # Verify the fragment against the fpcc.
            verification_report = Verifier.check(index, fragment_data, fpcc)

            if verification_report.result == VerificationResult.CONSISTENT:
                fragment = Fragment(
                    index=response["index"],
                    data=fragment_data,
                    block_id=block_id,
                    total_n=fpcc.n,
                    threshold_m=fpcc.m,
                    original_length=response["original_length"],
                )
                verified_fragments.append(fragment)


            if len(verified_fragments) >= self.m:
                break

        if len(verified_fragments) < self.m:
            raise RetrievalError(
                f"Retrieval failed: only {len(verified_fragments)}/{len(fragment_responses)} fragments verified as consistent; need at least {self.m}."
            )

        return decode(verified_fragments)


    def delete(self, block_id: str) -> None:
        """Request deletion of a stored block from all servers.

        Sends DELETE requests to all servers; ignores 404 responses (fragment
        may have already been deleted or never reached a server).

        Args:
            block_id: The key of the block to delete.
        """
        async def delete_fragment(
            client: httpx.AsyncClient,
            server: ServerAddress,
            index: int,
        ) -> None:
            try:
                response = await client.delete(self._server_url(server, block_id, index))

                # A missing fragment is expected here: it may never have been stored
                # or may already have been removed by an earlier delete.
                if response.status_code == 404:
                    return

                # Log non-404 failures for visibility, but keep delete best-effort
                # so one bad server does not fail the whole client call.
                if not response.is_success:
                    _log.warning(
                        "DELETE failed for block %s fragment %d on server %d: HTTP %d",
                        block_id,
                        index,
                        server.server_id,
                        response.status_code,
                    )
            except httpx.RequestError as exc:
                # Network issues are unexpected, but deletion remains best-effort.
                _log.warning(
                    "DELETE request error for block %s fragment %d on server %d: %s",
                    block_id,
                    index,
                    server.server_id,
                    exc,
                )

        async def delete_all_fragments() -> None:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await asyncio.gather(
                    *(
                        delete_fragment(client, server, index)
                        for index, server in enumerate(self.servers)
                    )
                )

        asyncio.run(delete_all_fragments())

    def health_check(self) -> dict[int, bool]:
        """Ping all servers and return their availability.

        Returns:
            A dict mapping server_id -> True (healthy) / False (unreachable).
        """
        async def check_server(
            client: httpx.AsyncClient,
            server: ServerAddress,
        ) -> tuple[int, bool]:
            try:
                # Probe this server's health endpoint directly; a healthy server
                # should respond with HTTP 200 and a JSON body containing status="ok".
                response = await client.get(f"{server.base_url}/health")
                if not response.is_success:
                    return server.server_id, False

                # Treat any non-"ok" status as unhealthy even if the endpoint responds.
                payload = response.json()
                return server.server_id, payload.get("status") == "ok"
            except (httpx.RequestError, ValueError):
                # Network failures and malformed responses both count as unhealthy.
                return server.server_id, False

        async def check_all_servers() -> dict[int, bool]:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check every server concurrently so one slow server does not
                # delay the rest of the availability results.
                results = await asyncio.gather(
                    *(check_server(client, server) for server in self.servers)
                )
            # Convert the list of (server_id, healthy) pairs into the API's
            # expected return shape.
            return dict(results)

        return asyncio.run(check_all_servers())

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
