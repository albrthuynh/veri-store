"""
test_polynomial.py -- Unit tests for Polynomial over GF(2^8).

Covers:
    - from_bytes / to_bytes round-trip
    - evaluate() with Horner's method (spot-checks against hand calculation)
    - Polynomial addition and subtraction (coefficient-wise XOR)
    - Polynomial multiplication (schoolbook)
    - divide_by_linear(): verify quotient * (x - root) + remainder == original
    - degree property
"""

from src.fingerprint.field import GF256
from src.fingerprint.polynomial import Polynomial


class TestPolynomialConstruction:
    """Tests for Polynomial construction and conversion."""

    def test_from_bytes_to_bytes_round_trip(self):
        """from_bytes then to_bytes recovers the original byte string."""
        data = b"Hello, GF!"
        assert Polynomial.from_bytes(data).to_bytes() == data

    def test_degree_of_constant_polynomial(self):
        """A single non-zero coefficient has degree 0."""
        assert Polynomial([GF256(5)]).degree == 0

    def test_degree_of_zero_polynomial(self):
        """The zero polynomial has degree -1."""
        assert Polynomial([GF256(0)]).degree == -1

    def test_trailing_zero_coefficients_stripped(self):
        """Leading zero coefficients do not affect degree."""
        p = Polynomial([GF256(1), GF256(0), GF256(0)])
        assert p.degree == 0
        assert p.coeffs == [GF256(1)]


class TestPolynomialEvaluation:
    """Tests for Polynomial.evaluate()."""

    def test_constant_polynomial(self):
        """p(x) = c evaluates to c for any x."""
        p = Polynomial([GF256(7)])
        assert p.evaluate(GF256(3)) == GF256(7)

    def test_linear_polynomial(self):
        """p(x) = a + b*x evaluates correctly at a specific point."""
        p = Polynomial([GF256(2), GF256(3)])  # 2 + 3x
        r = GF256(4)
        expected = GF256(2) + GF256(3) * r
        assert p.evaluate(r) == expected

    def test_evaluation_at_zero(self):
        """p(0) equals the constant term."""
        p = Polynomial.from_bytes(b"\xAB\x00\xCD")
        assert p.evaluate(GF256(0)) == GF256(0xAB)


class TestPolynomialArithmetic:
    """Tests for polynomial addition and subtraction."""

    def test_add_zero_polynomial(self):
        """p + 0 == p."""
        p = Polynomial.from_bytes(b"test data")
        zero = Polynomial([GF256(0)])
        assert p + zero == p
        assert p - zero == p

    def test_add_self_is_zero(self):
        """p + p == 0 in characteristic 2."""
        p = Polynomial.from_bytes(b"\x12\x34")
        result = p + p
        assert result == Polynomial([GF256(0)])
        assert result.degree == -1

    def test_addition_commutativity(self):
        """p1 + p2 == p2 + p1."""
        p1 = Polynomial.from_bytes(b"\x01\x02\x03")
        p2 = Polynomial.from_bytes(b"\x10\x20")
        assert p1 + p2 == p2 + p1
        assert p1 - p2 == p2 - p1


class TestPolynomialDivision:
    """Tests for divide_by_linear()."""

    def test_quotient_times_factor_plus_remainder_equals_original(self):
        """p == quotient * (x - root) + remainder."""
        p = Polynomial.from_bytes(b"some bytes")
        root = GF256(7)
        quotient, remainder = p.divide_by_linear(root)
        factor = Polynomial([root, GF256(1)])
        reconstructed = quotient * factor + Polynomial([remainder])
        assert reconstructed == p

    def test_root_gives_zero_remainder(self):
        """If root is actually a root of p, remainder is 0."""
        root = GF256(9)
        factor_a = Polynomial([GF256(5), GF256(1)])  # x - 5
        factor_root = Polynomial([root, GF256(1)])   # x - root
        p = factor_a * factor_root

        _, remainder = p.divide_by_linear(root)
        assert remainder == GF256(0)
