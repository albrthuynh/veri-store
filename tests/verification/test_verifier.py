"""
test_verifier.py -- Unit tests for the Verifier (server-side fragment check).

Covers:
    - CONSISTENT result for a valid fragment at an index in [0, m)
    - CONSISTENT result for a valid fragment at an index in [m, n)  (hash-only check)
    - HASH_MISMATCH when fragment bytes are altered
    - FP_MISMATCH when fragment bytes produce a wrong fingerprint (corrupt < m)
    - INDEX_ERROR when fragment_index is out of range
    - batch_check() returns one report per input
    - Detection probability: empirically verify that most corruptions are caught
"""

import pytest
from src.erasure.encoder import encode
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.verifier import Verifier, VerificationResult


@pytest.fixture
def encoded_block():
    """Return (fragments, fpcc) for a canonical 5-fragment block."""
    # TODO: frags = encode(b"verifier test data block", n=5, m=3)
    #       fpcc = FingerprintedCrossChecksum.generate(frags)
    #       return frags, fpcc
    ...


class TestVerifierConsistent:
    """Tests for the CONSISTENT outcome."""

    def test_valid_fragment_index_0_to_m(self, encoded_block):
        """A fingerprinted fragment (index < m) passes both hash and fp checks."""
        # TODO: frags, fpcc = encoded_block
        #       report = Verifier.check(0, frags[0].data, fpcc)
        #       assert report.result == VerificationResult.CONSISTENT
        #       assert report.fp_checked is True
        ...

    def test_valid_fragment_index_m_to_n(self, encoded_block):
        """A parity fragment (m <= index < n) passes the hash-only check."""
        # TODO: frags, fpcc = encoded_block
        #       report = Verifier.check(3, frags[3].data, fpcc)
        #       assert report.result == VerificationResult.CONSISTENT
        #       assert report.fp_checked is False
        ...


class TestVerifierDetectsCorruption:
    """Tests for corruption detection."""

    def test_hash_mismatch_for_altered_fragment(self, encoded_block):
        """Flipping a byte triggers HASH_MISMATCH."""
        # TODO: frags, fpcc = encoded_block
        #       corrupted = bytes([frags[4].data[0] ^ 0xFF]) + frags[4].data[1:]
        #       report = Verifier.check(4, corrupted, fpcc)
        #       assert report.result == VerificationResult.HASH_MISMATCH
        ...

    def test_fp_mismatch_when_hash_collides(self, encoded_block):
        """If a corrupt fragment passes the hash check (collision), fp catches it.

        This is hard to trigger deterministically, but we can stub the scenario
        by constructing a doctored fpcc with a matching hash but wrong fingerprint.
        """
        # TODO: Construct a synthetic fpcc where hashes[0] matches the corrupt
        #       fragment but fingerprints[0] does not.
        #       Verify FP_MISMATCH is returned.
        ...

    def test_index_out_of_range(self, encoded_block):
        """An out-of-range index returns INDEX_ERROR."""
        # TODO: _, fpcc = encoded_block
        #       report = Verifier.check(99, b"data", fpcc)
        #       assert report.result == VerificationResult.INDEX_ERROR
        ...


class TestBatchCheck:
    """Tests for Verifier.batch_check()."""

    def test_batch_length_matches_input(self, encoded_block):
        """batch_check() returns one report per (index, data) pair."""
        # TODO: frags, fpcc = encoded_block
        #       pairs = [(f.index, f.data) for f in frags]
        #       reports = Verifier.batch_check(pairs, fpcc)
        #       assert len(reports) == 5
        ...

    def test_batch_all_consistent_for_valid_block(self, encoded_block):
        """All reports are CONSISTENT for an unmodified block."""
        # TODO: frags, fpcc = encoded_block
        #       pairs = [(f.index, f.data) for f in frags]
        #       reports = Verifier.batch_check(pairs, fpcc)
        #       assert all(r.result == VerificationResult.CONSISTENT for r in reports)
        ...
