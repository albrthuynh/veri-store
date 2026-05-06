import hashlib

import pytest

from src.verification.oracle import RandomOracle
from src.fingerprint.field import GF256


class TestRandomOracleDerive:
    """Tests for RandomOracle.derive()."""

    def test_deterministic(self):
        """Same fragment hashes always produce the same r."""
        hashes = [b"\x00" * 32, b"\xff" * 32, b"\xab" * 32]

        r1 = RandomOracle.derive(hashes)
        r2 = RandomOracle.derive(hashes)

        assert r1 == r2  # should be the same for the same input

    def test_returns_gf256(self):
        """derive() returns a GF256 element."""
        hashes = [b"\x00" * 32]

        r = RandomOracle.derive(hashes)

        assert isinstance(r, GF256)

    def test_never_returns_zero(self):
        """derive() retries until it finds a nonzero GF256 element."""
        hashes = [b"\x01" * 32, b"\x02" * 32]

        r = RandomOracle.derive(hashes)

        assert r.value != 0

    def test_empty_hashes_raises(self):
        """derive() raises ValueError for an empty list."""
        with pytest.raises(ValueError, match="fragment_hashes cannot be empty"):
            RandomOracle.derive([])

    def test_different_hashes_likely_different_r(self):
        """
        Different hash vectors should (usually) produce different r values.

        Under the random oracle model, derive maps inputs approximately uniformly to non-zero GF(2^8) elements.
        Two distinct inputs could collide with probability 1/255.
        """
        r1 = RandomOracle.derive([b"\x00" * 32])
        r2 = RandomOracle.derive([b"\xff" * 32])

        assert r1 != r2  # Not guaranteed, but very likely different

    def test_hash_order_matters(self):
        """Changing the order of hashes should change the derived point."""
        r1 = RandomOracle.derive([b"\x11" * 32, b"\x22" * 32])
        r2 = RandomOracle.derive([b"\x22" * 32, b"\x11" * 32])

        assert r1 != r2  # Order should matter

    def test_matches_first_nonzero_candidate_from_sha256_counter_loop(self):
        """derive() returns the first nonzero first-byte candidate from the loop."""
        hashes = [b"\x00" * 32, b"\x20" * 32, b"\x30" * 32]
        concatenated = b"".join(hashes)

        counter = 0
        while True:
            digest = hashlib.sha256(concatenated + counter.to_bytes(4, "big")).digest()
            candidate = GF256(digest[0])
            if candidate.value != 0:
                expected = candidate
                break
            counter = counter + 1

        assert RandomOracle.derive(hashes) == expected


class TestHashFragment:
    """Tests for RandomOracle.hash_fragment()."""

    def test_returns_32_bytes(self):
        """hash_fragment() returns a 32-byte digest."""
        digest = RandomOracle.hash_fragment(b"data")

        assert isinstance(digest, bytes)
        assert len(digest) == 32

    def test_deterministic(self):
        """Same data produces the same hash."""
        assert RandomOracle.hash_fragment(b"same") == RandomOracle.hash_fragment(
            b"same"
        )

    def test_different_data_different_hash(self):
        """Different data should produce different hashes."""
        assert RandomOracle.hash_fragment(b"a") != RandomOracle.hash_fragment(b"b")

    def test_matches_hashlib_sha256(self):
        """hash_fragment() is exactly SHA-256 over the fragment bytes."""
        data = b"veri-store oracle test payload"
        expected = hashlib.sha256(data).digest()

        assert RandomOracle.hash_fragment(data) == expected

