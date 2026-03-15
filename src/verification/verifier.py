"""
verifier.py -- Server-side fragment consistency verification.

A server receiving fragment d_i and an fpcc verifies consistency as follows
(Definition 3.3):

    1. Recompute h_i' = SHA-256(d_i).
    2. Check h_i' == fpcc.hashes[i].  (Hash check)
    3. If i < m, recompute r' = Oracle(fpcc.hashes), then:
       Check fp(r', d_i) == fpcc.fingerprints[i].  (Fingerprint check)

If both checks pass, the fragment is *consistent* with the fpcc.  A failed
check means the fragment is corrupt or Byzantine-modified.

Theorem 3.4 guarantees that any *inconsistent* fragment will be detected except
with probability at most 1/q = 1/256 (for a single check).
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .cross_checksum import FingerprintedCrossChecksum
from .oracle import RandomOracle
from ..fingerprint.fingerprint import fingerprint


class VerificationResult(Enum):
    """Outcome of a fragment verification check.

    CONSISTENT    -- All applicable checks passed.
    HASH_MISMATCH -- The fragment's hash does not match the fpcc entry.
    FP_MISMATCH   -- The fingerprint check failed (for indices < m).
    INDEX_ERROR   -- The fragment index is out of range for the fpcc.
    """
    CONSISTENT = "consistent"
    HASH_MISMATCH = "hash_mismatch"
    FP_MISMATCH = "fp_mismatch"
    INDEX_ERROR = "index_error"


@dataclass
class VerificationReport:
    """Detailed report returned by Verifier.check().

    Attributes:
        result (VerificationResult): The overall outcome.
        fragment_index (int):        The index of the checked fragment.
        hash_matched (bool | None):  True if the hash check passed, None if not run.
        fp_checked (bool):           True if a fingerprint check was also performed.
        fp_matched (bool | None):    True if the fp check passed, None if not run.
        detail (str):                Human-readable explanation.
    """
    result: VerificationResult
    fragment_index: int
    hash_matched: bool | None
    fp_checked: bool
    fp_matched: bool | None
    detail: str


class Verifier:
    """Checks a single fragment for consistency against an fpcc.

    This is the primary server-side integrity primitive.  A server calls
    Verifier.check() when it receives a new fragment and periodically to
    audit stored fragments.
    """

    @staticmethod
    def check(
        fragment_index: int,
        fragment_data: bytes,
        fpcc: FingerprintedCrossChecksum,
    ) -> VerificationReport:
        """Verify that a fragment is consistent with the given fpcc.

        Args:
            fragment_index: The index i of the fragment being checked (0-based).
            fragment_data:  The raw bytes of fragment d_i.
            fpcc:           The fingerprinted cross-checksum for the block.

        Returns:
            A VerificationReport summarising the outcome.
        """
        # Is the index out of bounds?
        if not (0 <= fragment_index < fpcc.n):
            return VerificationReport(
                result=VerificationResult.INDEX_ERROR,
                fragment_index=fragment_index,
                hash_matched=None,
                fp_checked=False,
                fp_matched=None,
                detail=f"Fragment index {fragment_index} is out of range for fpcc with n={fpcc.n}."
            )

        # Does the fragment hash match the fpcc entry?
        h_i_prime = RandomOracle.hash_fragment(fragment_data)
        if h_i_prime != fpcc.hashes[fragment_index]:
            return VerificationReport(
                result=VerificationResult.HASH_MISMATCH,
                fragment_index=fragment_index,
                hash_matched=False,
                fp_checked=False,
                fp_matched=None,
                detail=f"Hash mismatch for fragment index {fragment_index}."
            )

        # For indices < m, do the fingerprints match?
        if (fragment_index < fpcc.m):
            r_prime = RandomOracle.derive(fpcc.hashes)
            fp_prime = fingerprint(r_prime, fragment_data)

            if fp_prime != fpcc.fingerprints[fragment_index]:
                return VerificationReport(
                    result=VerificationResult.FP_MISMATCH,
                    fragment_index=fragment_index,
                    hash_matched=True,
                    fp_checked=True,
                    fp_matched=False,
                    detail=f"Fingerprint mismatch for fragment index {fragment_index}."
                )

        # If we reach here, all checks passed.
        return VerificationReport(
            result=VerificationResult.CONSISTENT,
            fragment_index=fragment_index,
            hash_matched=True,
            fp_checked=(fragment_index < fpcc.m),
            fp_matched=True if fragment_index < fpcc.m else None,
            detail=f"Fragment index {fragment_index} is consistent with the fpcc."
        )

    @staticmethod
    def batch_check(
        fragments: list[tuple[int, bytes]],
        fpcc: FingerprintedCrossChecksum,
    ) -> list[VerificationReport]:
        """Verify multiple fragments against the same fpcc.

        Useful for auditing all fragments stored on a single server.

        Args:
            fragments: List of (index, data) pairs.
            fpcc:      The fingerprinted cross-checksum for the block.

        Returns:
            A list of VerificationReport objects, one per input fragment,
            in the same order as the input list.
        """
        return [Verifier.check(index, data, fpcc) for index, data in fragments]