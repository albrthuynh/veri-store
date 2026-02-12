"""
test_fingerprint.py -- Unit tests for the homomorphic fingerprint function.

Key property to verify (Theorem 2.3):
    fp(r, alpha*d1 XOR beta*d2) == alpha*fp(r,d1) XOR beta*fp(r,d2)

Also tests:
    - Fingerprint of empty data
    - Fingerprint is deterministic (same input -> same output)
    - random_point() returns values in [0, 255]
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
        # TODO: r = GF256(5) ; data = b"deterministic"
        #       assert fingerprint(r, data) == fingerprint(r, data)
        ...

    def test_empty_data(self):
        """Fingerprint of empty bytes is the zero element."""
        # TODO: assert fingerprint(GF256(7), b"") == GF256(0)
        ...

    def test_single_byte(self):
        """Fingerprint of a single byte d is fp(r, d) = d (degree-0 polynomial)."""
        # TODO: assert fingerprint(GF256(3), bytes([42])) == GF256(42)
        ...

    def test_homomorphic_property_additive(self):
        """fp(r, d1 XOR d2) == fp(r, d1) XOR fp(r, d2)."""
        # TODO: Choose r, d1, d2 of equal length.
        #       d_combined = bytes(a ^ b for a, b in zip(d1, d2))
        #       assert fingerprint(r, d_combined) == fingerprint(r, d1) + fingerprint(r, d2)
        ...

    def test_homomorphic_property_scalar(self):
        """fp(r, alpha * d) == alpha * fp(r, d) (scalar multiplication over GF(2^8))."""
        # TODO: This requires defining scalar multiplication on byte strings.
        #       Multiply each byte of d by alpha in GF(2^8), then fingerprint.
        ...

    def test_verify_homomorphic_property_returns_true(self):
        """verify_homomorphic_property() returns True for arbitrary valid inputs."""
        # TODO: r = GF256(13) ; d1 = b"\\x01\\x02\\x03" ; d2 = b"\\x04\\x05\\x06"
        #       assert verify_homomorphic_property(r, d1, d2, (GF256(1), GF256(1)))
        ...


class TestRandomPoint:
    """Tests for the random_point() oracle function."""

    def test_returns_gf256_element(self):
        """random_point() returns a GF256 value in [0, 255]."""
        # TODO: r = random_point(b"seed") ; assert 0 <= int(r) <= 255
        ...

    def test_deterministic_for_same_seed(self):
        """Same seed always produces the same point."""
        # TODO: assert random_point(b"seed") == random_point(b"seed")
        ...

    def test_different_seeds_likely_different_points(self):
        """Different seeds should (with high probability) give different points."""
        # TODO: Collect 10 distinct seeds and check that not all give the same r.
        #       (This is a probabilistic check; failure rate is negligible.)
        ...
