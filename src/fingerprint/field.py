"""
field.py -- Arithmetic in GF(2^8), the finite field with 256 elements.

Elements are bytes (integers 0-255).  Addition is XOR; multiplication uses the
standard AES irreducible polynomial x^8 + x^4 + x^3 + x + 1 (0x11B).

This field is the coefficient domain for all fingerprint polynomials.

References:
    - Hendricks et al. (2007), Section 2: field F_q with q = 2^8
    - AES specification (FIPS 197) for GF(2^8) multiplication tables
"""

from __future__ import annotations


IRREDUCIBLE_POLY: int = 0x11B

# Pre-compute the multiplicative inverse table for all non-zero elements.
_INVERSE_TABLE = [0] * 256
for _a in range (1, 256):
    for _b in range(1, 256):
        _result, _x, _y = 0, _a, _b

        while _y > 0:
            if _y & 1:
                _result ^= _x
            _y >>= 1
            _x <<= 1

            if _x & 0x100:
                _x ^= IRREDUCIBLE_POLY
        if _result == 1:
            _INVERSE_TABLE[_a] = _b
            break

class GF256:
    """An element of GF(2^8).

    Wraps a single byte value and overloads arithmetic operators so that code
    using field elements reads like ordinary algebra.

    Attributes:
        value (int): The integer representation of the field element (0-255).
    """

    def __init__(self, value: int) -> None:
        """Create a GF(2^8) element.

        Args:
            value: Integer in [0, 255].  Values outside this range are reduced
                   modulo 256 (i.e., only the low 8 bits are kept).
        """
        self.value = value & 0xFF

    # ------------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------------

    def __add__(self, other: GF256) -> GF256:
        """Field addition: XOR of the two byte values.

        Addition in GF(2^8) is bitwise XOR because the characteristic is 2.

        Args:
            other: Another GF(2^8) element.

        Returns:
            A new GF256 element equal to self XOR other.
        """
        return GF256(self.value ^ other.value)

    def __sub__(self, other: GF256) -> GF256:
        """Field subtraction: identical to addition in characteristic 2 (XOR).

        Args:
            other: Another GF(2^8) element.

        Returns:
            A new GF256 element (same as __add__ in GF(2^8)).
        """
        return self + other

    def __mul__(self, other: GF256) -> GF256:
        """Field multiplication modulo the irreducible polynomial.

        Uses the standard shift-and-XOR (Russian peasant) algorithm.

        Args:
            other: Another GF(2^8) element.

        Returns:
            A new GF256 element equal to (self * other) mod IRREDUCIBLE_POLY.
        """
        self_int = self.value
        other_int = other.value
        result = 0

        while other_int > 0:
            if other_int & 1:
                result ^= self_int
            
            other_int >>= 1
            self_int <<= 1
            if self_int & 0x100:
                self_int ^= IRREDUCIBLE_POLY

        return GF256(result)


    def __truediv__(self, other: GF256) -> GF256:
        """Field division: self * other^{-1}.

        Args:
            other: A non-zero GF(2^8) element.

        Returns:
            A new GF256 element.

        Raises:
            ZeroDivisionError: If other is the zero element.
        """
        if other.value == 0:
            raise ZeroDivisionError("division by zero in GF(2^8)")
        return self * other.inverse()

    def __pow__(self, exp: int) -> GF256:
        """Exponentiation by repeated squaring in GF(2^8).

        Args:
            exp: Non-negative integer exponent.

        Returns:
            A new GF256 element equal to self^exp.
        """
        result = GF256(1)
        base = GF256(self.value)
        while exp > 0:
            if exp & 1:
                result = result * base
            base = base * base
            exp >>= 1
        return result

    def inverse(self) -> GF256:
        """Multiplicative inverse via Fermat's little theorem: self^(q-2).

        In GF(2^8), q = 256, so the inverse is self^254.

        Returns:
            A new GF256 element such that self * result == GF256(1).

        Raises:
            ZeroDivisionError: If self is the zero element.
        """
        if self.value == 0:
            raise ZeroDivisionError("zero element has no multiplicative inverse in GF(2^8)")
        return GF256(_INVERSE_TABLE[self.value])

    # ------------------------------------------------------------------
    # Comparison and representation
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """Equality check based on integer value."""
        if not isinstance(other, GF256):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash based on integer value (needed for use in sets/dicts)."""
        return hash(self.value)

    def __repr__(self) -> str:
        """Human-readable representation."""
        return f"GF256(Hexadecimal: 0x{self.value:02X}, Decimal: {self.value}, Binary: {self.value:08b})"

    def __int__(self) -> int:
        """Convert to plain Python int."""
        return self.value

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def build_exp_log_tables(poly: int = IRREDUCIBLE_POLY) -> tuple[list[int], list[int]]:
    """Pre-compute exponentiation and logarithm tables for GF(2^8).

    These tables make multiplication O(1) via exp/log lookup:
        a * b = exp[(log[a] + log[b]) % 255]

    Args:
        poly: The irreducible polynomial (default: 0x11B).

    Returns:
        A (exp_table, log_table) pair, each a list of length 256.
        exp_table[i] = g^i mod poly where g=2 is the primitive element.
        log_table[v] = i such that g^i = v  (log_table[0] is undefined).
    """
    exp_table = [0] * 256
    log_table = [0] * 256

    x = 1
    for i in range(255):
        exp_table[i] = x
        log_table[x] = i
        x <<= 1
        if x & 0x100:
            x ^= IRREDUCIBLE_POLY

    exp_table[255] = 1  # g^255 == g^0 == 1 (the group has order 255)

    return exp_table, log_table
