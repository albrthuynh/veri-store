import hashlib

import pytest

from src.erasure.encoder import encode
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.oracle import RandomOracle
from src.fingerprint.fingerprint import fingerprint


@pytest.fixture
def fragments():
    """Canonical 5-of-3 encoded fragment set used across fpcc tests."""
    return encode(b"cross checksum test block", n=5, m=3, block_id="fpcc-test-block")


class TestFPCCGenerate:
    """Tests for FingerprintedCrossChecksum.generate()."""

    def test_correct_number_of_hashes_and_fingerprints(self, fragments):
        """fpcc has n hashes and m fingerprints."""
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        assert len(fpcc.hashes) == 5
        assert len(fpcc.fingerprints) == 3
        assert fpcc.n == 5
        assert fpcc.m == 3

    def test_hashes_match_sha256(self, fragments):
        """Each fpcc hash equals SHA-256 of the corresponding fragment."""
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        for i, frag in enumerate(fragments):
            expected = hashlib.sha256(frag.data).digest()
            assert fpcc.hashes[i] == expected

    def test_fingerprints_match_fp_function(self, fragments):
        """Each stored fingerprint equals fp(r, d_j) for j < m."""
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        for j in range(fpcc.m):
            expected = fingerprint(fpcc.r, fragments[j].data)
            assert fpcc.fingerprints[j] == expected

    def test_r_matches_oracle(self, fragments):
        """The stored r equals RandomOracle.derive(hashes)."""
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        expected_r = RandomOracle.derive(fpcc.hashes)

        assert fpcc.r == expected_r

    def test_generate_rejects_empty_fragment_list(self):
        """generate() raises ValueError for an empty fragment list."""
        with pytest.raises(ValueError, match="fragments cannot be empty"):
            FingerprintedCrossChecksum.generate([])

    def test_generate_rejects_out_of_order_fragments(self, fragments):
        """generate() raises ValueError if fragments are not in index order."""
        out_of_order = fragments.copy()
        out_of_order[0], out_of_order[1] = out_of_order[1], out_of_order[0]

        with pytest.raises(
            ValueError, match="fragments must be in index order with no gaps"
        ):
            FingerprintedCrossChecksum.generate(out_of_order)


class TestFPCCSerialization:
    """Tests for to_json() / from_json() round-trip."""

    def test_json_round_trip(self, fragments):
        """from_json(to_json(fpcc)) == fpcc (structural equality)."""
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        restored = FingerprintedCrossChecksum.from_json(fpcc.to_json())

        assert restored == fpcc

    def test_json_round_trip_preserves_field_values(self, fragments):
        """Serialized fpcc preserves hashes, fingerprints, r, n, and m exactly."""
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        restored = FingerprintedCrossChecksum.from_json(fpcc.to_json())

        assert restored.hashes == fpcc.hashes
        assert restored.fingerprints == fpcc.fingerprints
        assert restored.r == fpcc.r
        assert restored.n == fpcc.n
        assert restored.m == fpcc.m

    def test_digest_is_stable(self, fragments):
        """digest() returns the same hex string for the same fpcc."""
        fpcc = FingerprintedCrossChecksum.generate(fragments)

        assert fpcc.digest() == fpcc.digest()

    def test_digest_changes_when_fpcc_changes(self, fragments):
        """Different fpcc values should produce different digests."""
        fpcc1 = FingerprintedCrossChecksum.generate(fragments)

        modified_fragments = encode(
            b"cross checksum test block modified",
            n=5,
            m=3,
            block_id="fpcc-test-block-2",
        )
        fpcc2 = FingerprintedCrossChecksum.generate(modified_fragments)

        assert fpcc1.digest() != fpcc2.digest()

