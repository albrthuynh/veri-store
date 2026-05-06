from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .cross_checksum import FingerprintedCrossChecksum
from .oracle import RandomOracle
from ..fingerprint.fingerprint import fingerprint


class VerificationResult(Enum):
    CONSISTENT = "consistent"
    HASH_MISMATCH = "hash_mismatch"
    FP_MISMATCH = "fp_mismatch"
    INDEX_ERROR = "index_error"


@dataclass
class VerificationReport:
    result: VerificationResult
    fragment_index: int
    hash_matched: bool | None
    fp_checked: bool
    fp_matched: bool | None
    detail: str


class Verifier:
    @staticmethod
    def check(
        fragment_index: int,
        fragment_data: bytes,
        fpcc: FingerprintedCrossChecksum,
    ) -> VerificationReport:
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
        return [Verifier.check(index, data, fpcc) for index, data in fragments]
