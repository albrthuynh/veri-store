"""
test_verifier.py -- Unit tests for the Verifier (server-side fragment check).

Covers:
    - CONSISTENT result for a valid fragment at an index in [0, m)
    - CONSISTENT result for a valid fragment at an index in [m, n) (hash-only check)
    - HASH_MISMATCH when fragment bytes are altered
    - FP_MISMATCH when fingerprint data is tampered for indices < m
    - INDEX_ERROR when fragment_index is out of range
    - batch_check() returns one report per input, in input order
    - Byzantine fault detection: substitution, bit flips, fragment swaps,
      truncation, extension, parity-index swaps
    - r is recomputed from hashes, not trusted from fpcc.r
    - Detection probability: empirically verify that all byte-level corruptions
      are caught (SHA-256 collision probability is negligible in practice)
    - False positive rate is empirically zero for valid fragments
"""

import pytest

from src.erasure.encoder import encode
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.verifier import Verifier, VerificationResult


@pytest.fixture
def encoded_block():
    """Return (fragments, fpcc) for a canonical 5-fragment block."""
    frags = encode(b"verifier test data block", n=5, m=3)
    fpcc = FingerprintedCrossChecksum.generate(frags)
    return frags, fpcc


# ---------------------------------------------------------------------------
# Consistent (valid) fragment checks
# ---------------------------------------------------------------------------


class TestVerifierConsistent:
    """Tests for the CONSISTENT outcome."""

    def test_valid_fragment_index_0_to_m(self, encoded_block):
        """A fingerprinted fragment (index < m) passes both hash and fp checks."""
        frags, fpcc = encoded_block

        report = Verifier.check(0, frags[0].data, fpcc)

        assert report.result == VerificationResult.CONSISTENT
        assert report.hash_matched is True
        assert report.fp_checked is True
        assert report.fp_matched is True

    def test_valid_fragment_index_m_to_n(self, encoded_block):
        """A parity fragment (m <= index < n) passes the hash-only check."""
        frags, fpcc = encoded_block

        report = Verifier.check(3, frags[3].data, fpcc)

        assert report.result == VerificationResult.CONSISTENT
        assert report.hash_matched is True
        assert report.fp_checked is False
        assert report.fp_matched is None

    def test_all_fragments_consistent(self, encoded_block):
        """Every fragment in an unmodified block passes verification."""
        frags, fpcc = encoded_block

        for frag in frags:
            report = Verifier.check(frag.index, frag.data, fpcc)
            assert report.result == VerificationResult.CONSISTENT

    def test_consistent_detail_message_is_human_readable(self, encoded_block):
        """A successful report includes a readable explanation."""
        frags, fpcc = encoded_block

        report = Verifier.check(0, frags[0].data, fpcc)

        assert "consistent with the fpcc" in report.detail.lower()


# ---------------------------------------------------------------------------
# Corruption detection
# ---------------------------------------------------------------------------


class TestVerifierDetectsCorruption:
    """Tests for corruption detection."""

    def test_hash_mismatch_for_altered_fragment(self, encoded_block):
        """Flipping a byte triggers HASH_MISMATCH."""
        frags, fpcc = encoded_block
        corrupted = bytes([frags[4].data[0] ^ 0xFF]) + frags[4].data[1:]

        report = Verifier.check(4, corrupted, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH
        assert report.hash_matched is False
        assert report.fp_checked is False
        assert report.fp_matched is None
        assert "hash mismatch" in report.detail.lower()

    def test_fp_mismatch_when_hash_collides(self, encoded_block):
        """If a corrupt fragment passes the hash check, fp catches it.

        Constructed deterministically: keep the real fragment data so its hash
        still matches the fpcc hashes, but inject a wrong fingerprint value for
        fragment 0. The hash check passes and the fingerprint check fails.
        """
        frags, fpcc = encoded_block

        GF256 = type(fpcc.fingerprints[0])
        wrong_fp = GF256(fpcc.fingerprints[0].value ^ 0xFF)
        tampered_fpcc = FingerprintedCrossChecksum(
            hashes=fpcc.hashes,
            fingerprints=[wrong_fp] + fpcc.fingerprints[1:],
            r=fpcc.r,
            n=fpcc.n,
            m=fpcc.m,
        )

        report = Verifier.check(0, frags[0].data, tampered_fpcc)

        assert report.result == VerificationResult.FP_MISMATCH
        assert report.hash_matched is True
        assert report.fp_checked is True
        assert report.fp_matched is False
        assert "fingerprint mismatch" in report.detail.lower()

    def test_index_out_of_range(self, encoded_block):
        """An out-of-range index returns INDEX_ERROR."""
        _, fpcc = encoded_block

        report = Verifier.check(99, b"data", fpcc)

        assert report.result == VerificationResult.INDEX_ERROR
        assert report.hash_matched is None
        assert report.fp_checked is False
        assert report.fp_matched is None
        assert "out of range" in report.detail.lower()

    def test_negative_index_is_index_error(self, encoded_block):
        """A negative fragment index returns INDEX_ERROR, not a crash."""
        _, fpcc = encoded_block

        report = Verifier.check(-1, b"data", fpcc)

        assert report.result == VerificationResult.INDEX_ERROR
        assert report.hash_matched is None
        assert report.fp_checked is False
        assert report.fp_matched is None

    def test_tampered_stored_r_does_not_change_verification(self, encoded_block):
        """Verifier recomputes r from hashes instead of trusting fpcc.r."""
        frags, fpcc = encoded_block

        GF256 = type(fpcc.r)
        wrong_r = GF256(fpcc.r.value ^ 0xFF)
        tampered_fpcc = FingerprintedCrossChecksum(
            hashes=fpcc.hashes,
            fingerprints=fpcc.fingerprints,
            r=wrong_r,
            n=fpcc.n,
            m=fpcc.m,
        )

        report = Verifier.check(0, frags[0].data, tampered_fpcc)

        assert report.result == VerificationResult.CONSISTENT
        assert report.hash_matched is True
        assert report.fp_checked is True
        assert report.fp_matched is True

    def test_tampered_parity_fingerprint_is_ignored_for_parity_index(self, encoded_block):
        """Parity fragments do not consult fpcc.fingerprints during verification."""
        frags, fpcc = encoded_block

        GF256 = type(fpcc.fingerprints[0])
        tampered_fingerprints = [GF256(fp.value ^ 0xFF) for fp in fpcc.fingerprints]
        tampered_fpcc = FingerprintedCrossChecksum(
            hashes=fpcc.hashes,
            fingerprints=tampered_fingerprints,
            r=fpcc.r,
            n=fpcc.n,
            m=fpcc.m,
        )

        report = Verifier.check(4, frags[4].data, tampered_fpcc)

        assert report.result == VerificationResult.CONSISTENT
        assert report.hash_matched is True
        assert report.fp_checked is False
        assert report.fp_matched is None


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------


class TestBatchCheck:
    """Tests for Verifier.batch_check()."""

    def test_batch_length_matches_input(self, encoded_block):
        """batch_check() returns one report per (index, data) pair."""
        frags, fpcc = encoded_block
        pairs = [(f.index, f.data) for f in frags]

        reports = Verifier.batch_check(pairs, fpcc)

        assert len(reports) == len(pairs)

    def test_batch_all_consistent_for_valid_block(self, encoded_block):
        """All reports are CONSISTENT for an unmodified block."""
        frags, fpcc = encoded_block
        pairs = [(f.index, f.data) for f in frags]

        reports = Verifier.batch_check(pairs, fpcc)

        assert all(r.result == VerificationResult.CONSISTENT for r in reports)

    def test_batch_detects_single_corrupted_fragment(self, encoded_block):
        """batch_check identifies the one bad fragment among valid ones."""
        frags, fpcc = encoded_block
        corrupted_data = bytes([frags[2].data[0] ^ 0x01]) + frags[2].data[1:]
        pairs = [
            (frags[0].index, frags[0].data),
            (frags[1].index, frags[1].data),
            (frags[2].index, corrupted_data),
            (frags[3].index, frags[3].data),
            (frags[4].index, frags[4].data),
        ]

        reports = Verifier.batch_check(pairs, fpcc)

        assert reports[2].result == VerificationResult.HASH_MISMATCH
        assert all(reports[i].result == VerificationResult.CONSISTENT for i in [0, 1, 3, 4])

    def test_batch_preserves_input_order(self, encoded_block):
        """Reports are returned in the same order as the input pairs."""
        frags, fpcc = encoded_block
        pairs = [
            (frags[3].index, frags[3].data),
            (frags[1].index, frags[1].data),
            (99, b"bad-index"),
            (frags[0].index, frags[0].data),
        ]

        reports = Verifier.batch_check(pairs, fpcc)

        assert [r.fragment_index for r in reports] == [3, 1, 99, 0]
        assert reports[2].result == VerificationResult.INDEX_ERROR


# ---------------------------------------------------------------------------
# Byzantine fault detection
# ---------------------------------------------------------------------------


class TestByzantineDetection:
    """Tests for Byzantine fault detection scenarios.

    A Byzantine server actively returns incorrect data rather than failing
    silently. These tests verify that Verifier.check() catches each known
    attack variant. The verification pipeline uses two checks in series:

        1. Hash check (all indices):    SHA-256(d_i) == fpcc.hashes[i]
        2. Fp check   (indices < m):    fp(r, d_i)   == fpcc.fingerprints[i]

    Because SHA-256 is collision-resistant, the hash check alone catches
    virtually all practical corruptions. The fingerprint check provides a
    second layer for the m most critical fragments, guarding against the
    1/256 theoretical probability of an adversary finding a hash collision.
    """

    def test_complete_data_substitution(self, encoded_block):
        """Replacing a fragment with entirely different data is detected."""
        frags, fpcc = encoded_block
        forged = b"FORGED_DATA_INJECTED_BY_BYZANTINE_SERVER" * 2

        report = Verifier.check(0, forged, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH

    def test_all_zeros_substitution(self, encoded_block):
        """A Byzantine server returning all-zero bytes is detected."""
        frags, fpcc = encoded_block
        zeros = bytes(len(frags[1].data))

        report = Verifier.check(1, zeros, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH

    def test_fragment_swap_across_indices(self, encoded_block):
        """A server returning fragment[2]'s data at index 0 is detected."""
        frags, fpcc = encoded_block

        report = Verifier.check(0, frags[2].data, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH

    def test_parity_fragment_swap_detected(self, encoded_block):
        """Swapping parity fragments across indices is detected."""
        frags, fpcc = encoded_block

        report = Verifier.check(3, frags[4].data, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH

    def test_single_bit_flip_detected(self, encoded_block):
        """Flipping one bit of one byte is detected."""
        frags, fpcc = encoded_block
        data = frags[0].data
        corrupted = bytes([data[0] ^ 0x01]) + data[1:]

        report = Verifier.check(0, corrupted, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH

    def test_truncated_fragment_detected(self, encoded_block):
        """A fragment shorter than expected is detected."""
        frags, fpcc = encoded_block
        truncated = frags[0].data[:-1]

        report = Verifier.check(0, truncated, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH

    def test_extended_fragment_detected(self, encoded_block):
        """A fragment with extra bytes appended is detected."""
        frags, fpcc = encoded_block
        extended = frags[0].data + b"\x00"

        report = Verifier.check(0, extended, fpcc)

        assert report.result == VerificationResult.HASH_MISMATCH

    def test_fp_check_skipped_for_parity_indices(self, encoded_block):
        """Parity fragments undergo hash check only, never fingerprint check."""
        frags, fpcc = encoded_block

        for frag in frags:
            if frag.index >= fpcc.m:
                report = Verifier.check(frag.index, frag.data, fpcc)
                assert report.fp_checked is False
                assert report.fp_matched is None

    def test_report_fragment_index_matches_input(self, encoded_block):
        """The report's fragment_index field reflects the input index."""
        frags, fpcc = encoded_block

        for frag in frags:
            report = Verifier.check(frag.index, frag.data, fpcc)
            assert report.fragment_index == frag.index

    def test_detection_rate_across_random_corruptions(self, encoded_block):
        """Empirically verify 100% detection for representative byte flips."""
        frags, fpcc = encoded_block
        data = frags[0].data
        flip_masks = (0x01, 0x80, 0xFF)

        trials = 0
        detected = 0
        for byte_pos in range(len(data)):
            for mask in flip_masks:
                corrupted = bytearray(data)
                corrupted[byte_pos] ^= mask
                report = Verifier.check(0, bytes(corrupted), fpcc)
                if report.result != VerificationResult.CONSISTENT:
                    detected += 1
                trials += 1

        assert detected == trials, (
            f"Expected all {trials} corruptions to be detected, "
            f"but only {detected} were caught."
        )


# ---------------------------------------------------------------------------
# False positive rate
# ---------------------------------------------------------------------------


class TestFalsePositiveRate:
    """Measures the false positive rate of Verifier.check()."""

    _CONFIGS = [(5, 3), (7, 4), (10, 6)]
    _PAYLOADS = [
        b"tiny",
        b"A" * 64,
        b"\x00" * 128,
        b"\xff" * 128,
        bytes(range(256)),
        b"mixed: " + bytes(range(128)) * 3,
    ]

    def test_valid_fragments_never_rejected_across_configs(self):
        """All valid fragments across representative configurations pass."""
        false_positives = 0
        total = 0

        for n, m in self._CONFIGS:
            for i, payload in enumerate(self._PAYLOADS):
                data = f"fp-test-{n}-{m}-{i}:".encode() + payload
                fragments = encode(data, n=n, m=m)
                fpcc = FingerprintedCrossChecksum.generate(fragments)

                for frag in fragments:
                    report = Verifier.check(frag.index, frag.data, fpcc)
                    if report.result != VerificationResult.CONSISTENT:
                        false_positives += 1
                    total += 1

        assert false_positives == 0, (
            f"False positive rate: {false_positives}/{total} valid fragments "
            f"incorrectly rejected (expected 0/{total})."
        )

    def test_repeated_verification_is_deterministic(self):
        """Re-verifying the same valid fragment always gives the same result."""
        frags = encode(b"determinism test -- repeated verification", n=5, m=3)
        fpcc = FingerprintedCrossChecksum.generate(frags)

        repetitions = 50
        for frag in frags:
            for attempt in range(repetitions):
                report = Verifier.check(frag.index, frag.data, fpcc)
                assert report.result == VerificationResult.CONSISTENT, (
                    f"Fragment {frag.index} failed on attempt {attempt + 1}/{repetitions}: "
                    f"{report.result.value} - {report.detail}"
                )

    def test_false_positive_rate_empirically_zero(self):
        """Measure the empirical false positive rate over 500 fragment checks."""
        false_positives = 0
        total = 0

        for i in range(100):
            data = f"empirical-fp-rate-block-{i:04d}:".encode() + b"X" * 64
            fragments = encode(data, n=5, m=3)
            fpcc = FingerprintedCrossChecksum.generate(fragments)

            for frag in fragments:
                report = Verifier.check(frag.index, frag.data, fpcc)
                if report.result != VerificationResult.CONSISTENT:
                    false_positives += 1
                total += 1

        rate = false_positives / total
        assert false_positives == 0, (
            f"Empirical false positive rate: {false_positives}/{total} = {rate:.4%}. "
            f"Expected: 0/{total} = 0.0000%.\n"
            f"A non-zero rate indicates a bug in the verification pipeline - "
            f"Verifier.check() is rejecting fragments it should accept."
        )