"""
test_fingerprint.py -- Unit tests for the homomorphic fingerprint function.

Key property to verify (Theorem 2.3):
    fp(r, alpha*d1 XOR beta*d2) == alpha*fp(r,d1) XOR beta*fp(r,d2)

Also tests:
    - Fingerprint of empty data
    - Fingerprint is deterministic (same input -> same output)
    - random_point() returns values in [1, 255] (never zero)
    - random_point() is deterministic for a given seed
    - verify_homomorphic_property() helper returns True for valid data
"""

import pytest
from src.fingerprint.field import GF256
from src.fingerprint.fingerprint import fingerprint, random_point, verify_homomorphic_property


class TestFingerprint:
    """Tests for the fp(r, data) function."""

    def test_deterministic(self):
        """Same r and data always produce the same fingerprint."""
        r = GF256(5)
        data = b"deterministic"
        assert fingerprint(r, data) == fingerprint(r, data)

    def test_empty_data(self):
        """Fingerprint of empty bytes is the zero element."""
        assert fingerprint(GF256(7), b"") == GF256(0)

    def test_single_byte(self):
        """Fingerprint of a single byte d is fp(r, d) = d (degree-0 polynomial)."""
        # A one-byte block is a constant polynomial; evaluation point doesn't matter.
        assert fingerprint(GF256(3), bytes([42])) == GF256(42)
        assert fingerprint(GF256(255), bytes([42])) == GF256(42)

    def test_two_byte_manual(self):
        """Manually verify a two-byte block: fp(r, [c0, c1]) = c0 + c1*r."""
        r = GF256(3)
        c0, c1 = GF256(5), GF256(7)
        expected = c0 + c1 * r
        assert fingerprint(r, bytes([c0.value, c1.value])) == expected

    def test_homomorphic_property_additive(self):
        """fp(r, d1 XOR d2) == fp(r, d1) XOR fp(r, d2)."""
        r = GF256(17)
        d1 = b"\x01\x02\x03\x04"
        d2 = b"\x10\x20\x30\x40"
        d_combined = bytes(a ^ b for a, b in zip(d1, d2))
        assert fingerprint(r, d_combined) == fingerprint(r, d1) + fingerprint(r, d2)

    def test_homomorphic_property_scalar(self):
        """fp(r, alpha * d) == alpha * fp(r, d)."""
        r = GF256(7)
        alpha = GF256(13)
        d = b"\x05\x0A\x0F\x14"
        scaled = bytes((alpha * GF256(b)).value for b in d)
        assert fingerprint(r, scaled) == alpha * fingerprint(r, d)

    def test_homomorphic_property_general(self):
        """fp(r, a*d1 + b*d2) == a*fp(r,d1) + b*fp(r,d2) for arbitrary a, b."""
        r = GF256(42)
        d1 = b"\x01\x02\x03"
        d2 = b"\x04\x05\x06"
        assert verify_homomorphic_property(r, d1, d2, (GF256(3), GF256(5)))
        assert verify_homomorphic_property(r, d1, d2, (GF256(255), GF256(128)))
        assert verify_homomorphic_property(r, d1, d2, (GF256(1), GF256(1)))

    def test_verify_homomorphic_property_returns_true(self):
        """verify_homomorphic_property() returns True for arbitrary valid inputs."""
        r = GF256(13)
        d1 = b"\x01\x02\x03"
        d2 = b"\x04\x05\x06"
        assert verify_homomorphic_property(r, d1, d2, (GF256(1), GF256(1)))

    def test_verify_homomorphic_property_raises_on_length_mismatch(self):
        """verify_homomorphic_property() raises ValueError when data lengths differ."""
        with pytest.raises(ValueError):
            verify_homomorphic_property(GF256(1), b"\x01\x02", b"\x01", (GF256(1), GF256(1)))

    def test_different_points_give_different_fingerprints(self):
        """Different evaluation points generally produce different fingerprints."""
        data = b"hello world"
        results = {fingerprint(GF256(r), data) for r in range(1, 20)}
        # With a non-trivial polynomial, at most deg(p) evaluation points can collide.
        assert len(results) > 1

    def test_zero_scalar_gives_zero_fingerprint(self):
        """Scaling data by GF256(0) yields zero fingerprint."""
        r = GF256(7)
        d = b"\x01\x02\x03"
        scaled = bytes((GF256(0) * GF256(b)).value for b in d)
        assert fingerprint(r, scaled) == GF256(0)

    def test_evaluation_point_zero_returns_constant_term(self):
        """fp(0, data) returns only the constant term (first byte)."""
        data = b"\x42\x01\x02\x03"
        assert fingerprint(GF256(0), data) == GF256(0x42)

    def test_verify_homomorphic_zero_coefficients(self):
        """verify_homomorphic_property with a=0, b=0 gives zero on both sides."""
        r = GF256(7)
        d1 = b"\x01\x02\x03"
        d2 = b"\x04\x05\x06"
        assert verify_homomorphic_property(r, d1, d2, (GF256(0), GF256(0)))


class TestRandomPoint:
    """Tests for the random_point() oracle function."""

    def test_returns_gf256_element(self):
        """random_point() returns a GF256 value in [0, 255]."""
        r = random_point(b"seed")
        assert 0 <= int(r) <= 255

    def test_never_returns_zero(self):
        """random_point() never returns GF256(0)."""
        for i in range(20):
            r = random_point(i.to_bytes(4, "big"))
            assert r.value != 0

    def test_deterministic_for_same_seed(self):
        """Same seed always produces the same point."""
        assert random_point(b"seed") == random_point(b"seed")
        assert random_point(b"abc123") == random_point(b"abc123")

    def test_different_seeds_likely_different_points(self):
        """Different seeds should (with high probability) give different points."""
        results = {random_point(str(i).encode()).value for i in range(10)}
        assert len(results) > 1

    def test_empty_seed(self):
        """random_point() handles an empty seed without error."""
        r = random_point(b"")
        assert isinstance(r, GF256)
        assert r.value != 0

    def test_large_seed(self):
        """random_point() handles a large seed without error."""
        r = random_point(b"x" * 10_000)
        assert isinstance(r, GF256)
        assert r.value != 0
