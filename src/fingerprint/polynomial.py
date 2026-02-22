"""
polynomial.py -- Polynomials with coefficients in GF(2^8).

A polynomial is stored as a list of GF256 coefficients in little-endian order:
    coeffs[0] + coeffs[1]*x + coeffs[2]*x^2 + ...

This representation is used both for data blocks (each byte is a coefficient)
and for the division fingerprint computation (polynomial evaluation / modular
reduction).

Key operations needed by the fingerprinting scheme:
    - Evaluate a polynomial at a field point: p(r)
    - Divide p(x) by a degree-1 factor (x - r) for the division method
    - Add / subtract two polynomials coefficient-wise
"""

from __future__ import annotations
from typing import Sequence
from .field import GF256


class Polynomial:
    """A polynomial over GF(2^8).

    Attributes:
        coeffs (list[GF256]): Coefficients in little-endian order.
            coeffs[i] is the coefficient of x^i.
    """

    def __init__(self, coeffs: Sequence[GF256 | int]) -> None:
        """Construct a polynomial from a sequence of coefficients.

        Args:
            coeffs: Coefficients in little-endian order.  Plain ints are
                    automatically wrapped in GF256.

        Example:
            Polynomial([1, 0, 1])  ->  1 + x^2  over GF(2^8)
        """
        if not coeffs:
            self.coeffs = [GF256(0)]
            return
        wrapped = [c if isinstance(c, GF256) else GF256(c) for c in coeffs]
        # Strip trailing zero coefficients, keeping at least one term.
        while len(wrapped) > 1 and wrapped[-1].value == 0:
            wrapped.pop()
        self.coeffs = wrapped

    @classmethod
    def from_bytes(cls, data: bytes) -> Polynomial:
        """Interpret a byte string as a polynomial over GF(2^8).

        Each byte d[i] becomes the coefficient of x^i.

        Args:
            data: Raw bytes representing the data block.

        Returns:
            A Polynomial whose evaluation encodes the data block.
        """
        return cls([GF256(b) for b in data])

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, point: GF256) -> GF256:
        """Evaluate the polynomial at a field point using Horner's method.

        Horner's method computes p(r) in O(deg) multiplications:
            p(r) = c0 + r*(c1 + r*(c2 + ... + r*cn))

        Args:
            point: The evaluation point r in GF(2^8).

        Returns:
            p(r) as a GF256 element.
        """
        result = GF256(0)
        for coeff in reversed(self.coeffs):
            result = result * point + coeff
        return result

    # ------------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------------

    def __add__(self, other: Polynomial) -> Polynomial:
        """Add two polynomials coefficient-wise (XOR in GF(2^8)).

        Args:
            other: Another Polynomial.

        Returns:
            A new Polynomial equal to self + other.
        """
        n = max(len(self.coeffs), len(other.coeffs))
        result = []
        for i in range(n):
            a = self.coeffs[i] if i < len(self.coeffs) else GF256(0)
            b = other.coeffs[i] if i < len(other.coeffs) else GF256(0)
            result.append(a + b)
        return Polynomial(result)

    def __sub__(self, other: Polynomial) -> Polynomial:
        """Subtract two polynomials (identical to addition in char 2).

        Args:
            other: Another Polynomial.

        Returns:
            A new Polynomial equal to self - other.
        """
        return self + other

    def __mul__(self, other: Polynomial | GF256) -> Polynomial:
        """Multiply two polynomials, or scale by a field element.

        Args:
            other: Another Polynomial, or a GF256 scalar.

        Returns:
            A new Polynomial equal to self * other.
        """
        if isinstance(other, GF256):
            return Polynomial([c * other for c in self.coeffs])
        # Schoolbook polynomial multiplication.
        result = [GF256(0)] * (len(self.coeffs) + len(other.coeffs) - 1)
        for i, a in enumerate(self.coeffs):
            for j, b in enumerate(other.coeffs):
                result[i + j] = result[i + j] + a * b
        return Polynomial(result)

    # ------------------------------------------------------------------
    # Division for the fingerprinting scheme
    # ------------------------------------------------------------------

    def divide_by_linear(self, root: GF256) -> tuple[Polynomial, GF256]:
        """Divide self by (x - root) using synthetic division.

        Returns the quotient q and remainder r such that:
            self(x) = q(x) * (x - root) + r

        In GF(2^8), (x - root) == (x + root) because subtraction is XOR.

        Args:
            root: The root r of the linear factor (x - r).

        Returns:
            (quotient, remainder) where remainder is a GF256 element
            and quotient is a Polynomial of degree deg(self) - 1.
        """
        n = len(self.coeffs)
        if n == 1:
            return Polynomial([GF256(0)]), self.coeffs[0]

        # Process coefficients from highest degree to lowest.
        carry = self.coeffs[-1]
        quotient_big_endian = [carry]

        for i in range(n - 2, 0, -1):
            carry = self.coeffs[i] + root * carry
            quotient_big_endian.append(carry)

        remainder = self.coeffs[0] + root * carry
        quotient_big_endian.reverse()  # convert to little-endian
        return Polynomial(quotient_big_endian), remainder

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def degree(self) -> int:
        """Degree of the polynomial (index of the leading non-zero coefficient).

        Returns:
            The degree, or -1 for the zero polynomial.
        """
        for i in range(len(self.coeffs) - 1, -1, -1):
            if self.coeffs[i].value != 0:
                return i
        return -1

    def to_bytes(self) -> bytes:
        """Serialize coefficients to a byte string (little-endian).

        Returns:
            Bytes object where byte i is the coefficient of x^i.
        """
        return bytes(c.value for c in self.coeffs)

    def __eq__(self, other: object) -> bool:
        """Equality check (coefficient-wise)."""
        if not isinstance(other, Polynomial):
            return False
        return self.coeffs == other.coeffs

    def __repr__(self) -> str:
        """Human-readable polynomial representation."""
        terms = []
        for i, c in reversed(list(enumerate(self.coeffs))):
            if c.value == 0:
                continue
            if i == 0:
                terms.append(f"{c.value}")
            elif i == 1:
                terms.append(f"x" if c.value == 1 else f"{c.value}x")
            else:
                terms.append(f"x^{i}" if c.value == 1 else f"{c.value}x^{i}")
        return " + ".join(terms) if terms else "0"