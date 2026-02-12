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
import httpx
from dataclasses import dataclass


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
        # TODO: return f"http://{self.host}:{self.port}"
        ...


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
        # TODO: Validate len(servers) >= m.
        # TODO: Store attributes.
        ...

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
        # TODO: 1. Call erasure.encode(data, n=len(servers), m=self.m).
        # TODO: 2. Call FingerprintedCrossChecksum.generate(fragments).
        # TODO: 3. For each fragment, POST to the corresponding server (parallel).
        # TODO: 4. Count successes; raise DispersalError if < m succeed.
        # TODO: 5. Return block_id.
        ...

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
        # TODO: 1. Request fragment from each server (parallel, best-effort).
        # TODO: 2. Collect the first m successful responses.
        # TODO: 3. Deserialize fpcc from the first response.
        # TODO: 4. Re-verify each retrieved fragment with Verifier.check().
        # TODO: 5. If any fragment fails verification, discard and try next server.
        # TODO: 6. Call erasure.decode(verified_fragments).
        # TODO: 7. Return reconstructed data.
        ...

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
        # TODO: return f"{server.base_url}/fragments/{block_id}/{index}"
        ...


class DispersalError(RuntimeError):
    """Raised when fewer than m servers acknowledged a PUT."""


class RetrievalError(RuntimeError):
    """Raised when the client cannot assemble m verified fragments for a GET."""
