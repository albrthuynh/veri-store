"""
oracle.py -- Random oracle for deriving the fingerprint evaluation point r.

The evaluation point r must be chosen *after* all fragment hashes are fixed,
so that a Byzantine server cannot pre-compute a forgery.  We model this as a
random oracle:

    r = Oracle(h_0 || h_1 || ... || h_{n-1})

In practice, Oracle is implemented as the first byte of SHA-256 applied to the
concatenated fragment hashes.  This gives r in GF(2^8) = {0, ..., 255}.

The collision probability for any single verification check is at most 1/q
where q = 256 = |GF(2^8)|.  See Theorem 3.4 in the paper.
"""

from __future__ import annotations
from ..fingerprint.field import GF256


class RandomOracle:
    """Deterministic random oracle mapping fragment-hash vectors to GF(2^8).

    The oracle is pure (no state): the same inputs always produce the same r.
    """

    @staticmethod
    def derive(fragment_hashes: list[bytes]) -> GF256:
        """Derive the evaluation point r from a list of fragment hash digests.

        Args:
            fragment_hashes: Ordered list of raw hash digests (bytes), one per
                             fragment (index 0 to n-1).  Each should be a
                             fixed-length digest (e.g. 32 bytes for SHA-256).

        Returns:
            A GF256 element to use as the fingerprint evaluation point.

        Raises:
            ValueError: If fragment_hashes is empty.
        """
        # TODO: 1. Concatenate all fragment hash bytes in order.
        # TODO: 2. Compute SHA-256 of the concatenation.
        # TODO: 3. Return GF256(digest[0]).
        ...

    @staticmethod
    def hash_fragment(fragment_data: bytes) -> bytes:
        """Compute the SHA-256 hash of a fragment's data bytes.

        Args:
            fragment_data: The raw bytes of a single fragment.

        Returns:
            A 32-byte SHA-256 digest.
        """
        # TODO: return hashlib.sha256(fragment_data).digest()
        ...
