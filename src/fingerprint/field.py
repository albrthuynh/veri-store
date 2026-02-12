"""
field.py -- Arithmetic in GF(2^8), the finite field with 256 elements.

Elements are bytes (integers 0-255).  Addition is XOR; multiplication uses the
standard AES irreducible polynomial x^8 + x^4 + x^3 + x + 1 (0x11B) unless a
different modulus is provided.

This field is the coefficient domain for all fingerprint polynomials.

References:
    - Hendricks et al. (2007), Section 2: field F_q with q = 2^8
    - AES specification (FIPS 197) for GF(2^8) multiplication tables
"""

from __future__ import annotations


# TODO: Replace with the irreducible polynomial chosen for veri-store.
#       AES uses 0x11B (x^8 + x^4 + x^3 + x + 1); verify this is appropriate.
IRREDUCIBLE_POLY: int = 0x11B


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
        # TODO: Validate and mask value to 8 bits.
        ...

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
        # TODO: Implement XOR addition.
        ...

    def __sub__(self, other: GF256) -> GF256:
        """Field subtraction: identical to addition in characteristic 2 (XOR).

        Args:
            other: Another GF(2^8) element.

        Returns:
            A new GF256 element (same as __add__ in GF(2^8)).
        """
        # TODO: Subtraction == addition in GF(2^k).
        ...

    def __mul__(self, other: GF256) -> GF256:
        """Field multiplication modulo the irreducible polynomial.

        Uses the standard shift-and-XOR (Russian peasant) algorithm.

        Args:
            other: Another GF(2^8) element.

        Returns:
            A new GF256 element equal to (self * other) mod IRREDUCIBLE_POLY.
        """
        # TODO: Implement carry-less multiplication with reduction.
        ...

    def __truediv__(self, other: GF256) -> GF256:
        """Field division: self * other^{-1}.

        Args:
            other: A non-zero GF(2^8) element.

        Returns:
            A new GF256 element.

        Raises:
            ZeroDivisionError: If other is the zero element.
        """
        # TODO: Compute multiplicative inverse via Fermat's little theorem
        #       (other^(254) in GF(2^8)) or extended Euclidean algorithm.
        ...

    def __pow__(self, exp: int) -> GF256:
        """Exponentiation by repeated squaring in GF(2^8).

        Args:
            exp: Non-negative integer exponent.

        Returns:
            A new GF256 element equal to self^exp.
        """
        # TODO: Implement square-and-multiply.
        ...

    def inverse(self) -> GF256:
        """Multiplicative inverse via Fermat's little theorem: self^(q-2).

        In GF(2^8), q = 256, so the inverse is self^254.

        Returns:
            A new GF256 element such that self * result == GF256(1).

        Raises:
            ZeroDivisionError: If self is the zero element.
        """
        # TODO: return self ** 254
        ...

    # ------------------------------------------------------------------
    # Comparison and representation
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """Equality check based on integer value."""
        # TODO: Compare .value attributes.
        ...

    def __hash__(self) -> int:
        """Hash based on integer value (needed for use in sets/dicts)."""
        # TODO: return hash(self.value)
        ...

    def __repr__(self) -> str:
        """Human-readable representation."""
        # TODO: return f"GF256(0x{self.value:02X})"
        ...

    def __int__(self) -> int:
        """Convert to plain Python int."""
        # TODO: return self.value
        ...


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
    # TODO: Build tables by repeatedly multiplying the generator (0x02).
    ...
