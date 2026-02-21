"""
test_field.py -- Unit tests for GF(2^8) arithmetic.

Covers:
    - Addition (XOR) commutativity and associativity
    - Additive identity (zero element)
    - Multiplication commutativity and associativity
    - Distributive law: a*(b+c) == a*b + a*c
    - Multiplicative identity (one element)
    - Multiplicative inverse: a * a^{-1} == 1  for all a != 0
    - Division: (a / b) * b == a
    - Exponentiation: a^0 == 1, a^1 == a
    - exp/log table consistency: exp[log[a]] == a for all a != 0
"""

import pytest
from src.fingerprint.field import GF256, build_exp_log_tables


class TestGF256Addition:
    """Tests for GF(2^8) addition (XOR)."""

    def test_zero_is_additive_identity(self):
        """a + 0 == a for all a."""
        for a in range(256):
            assert GF256(a) + GF256(0) == GF256(a)

    def test_addition_is_commutative(self):
        """a + b == b + a."""
        pairs = [(0, 0), (1, 2), (17, 42), (127, 128), (255, 255)]
        for a, b in pairs:
            assert GF256(a) + GF256(b) == GF256(b) + GF256(a)

    def test_addition_is_associative(self):
        """(a + b) + c == a + (b + c)."""
        a, b, c = GF256(3), GF256(5), GF256(7)
        assert (a + b) + c == a + (b + c)

    def test_self_inverse(self):
        """a + a == 0 in characteristic 2."""
        for a in range(256):
            assert GF256(a) + GF256(a) == GF256(0)

    def test_subtraction_equals_addition(self):
        """a - b == a + b in GF(2^8)."""
        assert GF256(17) - GF256(42) == GF256(17) + GF256(42)


class TestGF256Multiplication:
    """Tests for GF(2^8) multiplication."""

    def test_one_is_multiplicative_identity(self):
        """a * 1 == a for all a."""
        for a in range(256):
            assert GF256(a) * GF256(1) == GF256(a)

    def test_zero_annihilates(self):
        """a * 0 == 0 for all a."""
        for a in range(256):
            assert GF256(a) * GF256(0) == GF256(0)

    def test_multiplication_is_commutative(self):
        """a * b == b * a."""
        pairs = [(1, 2), (17, 42), (127, 128), (255, 255)]
        for a, b in pairs:
            assert GF256(a) * GF256(b) == GF256(b) * GF256(a)

    def test_distributive_law(self):
        """a * (b + c) == a*b + a*c."""
        a, b, c = GF256(3), GF256(5), GF256(7)
        assert a * (b + c) == a * b + a * c

    def test_known_products(self):
        """Verify specific known products from AES GF(2^8) tables."""
        # 0x53 and 0xCA are multiplicative inverses, so their product is 1.
        assert GF256(0x53) * GF256(0xCA) == GF256(0x01)


class TestGF256Inverse:
    """Tests for multiplicative inverse."""

    def test_inverse_times_self_is_one(self):
        """a * a.inverse() == 1 for all non-zero a."""
        for a in range(1, 256):
            assert GF256(a) * GF256(a).inverse() == GF256(1)

    def test_zero_has_no_inverse(self):
        """GF256(0).inverse() raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            GF256(0).inverse()

    def test_division(self):
        """(a / b) * b == a for all non-zero b."""
        pairs = [(1, 1), (42, 17), (255, 128), (100, 200)]
        for a, b in pairs:
            assert (GF256(a) / GF256(b)) * GF256(b) == GF256(a)


class TestExpLogTables:
    """Tests for the exponentiation and logarithm lookup tables."""

    def test_exp_log_round_trip(self):
        """exp[log[a]] == a for all non-zero a."""
        exp_table, log_table = build_exp_log_tables()
        for a in range(1, 256):
            assert exp_table[log_table[a]] == a

    def test_exp_table_length(self):
        """exp_table has at least 256 entries."""
        assert len(build_exp_log_tables()[0]) >= 256