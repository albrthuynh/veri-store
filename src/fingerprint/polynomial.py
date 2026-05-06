from __future__ import annotations
from typing import Sequence
from .field import GF256


class Polynomial:
    def __init__(self, coeffs: Sequence[GF256 | int]) -> None:
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
        return cls([GF256(b) for b in data])

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(self, point: GF256) -> GF256:
        result = GF256(0)
        for coeff in reversed(self.coeffs):
            result = result * point + coeff
        return result

    # ------------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------------

    def __add__(self, other: Polynomial) -> Polynomial:
        n = max(len(self.coeffs), len(other.coeffs))
        result = []
        for i in range(n):
            a = self.coeffs[i] if i < len(self.coeffs) else GF256(0)
            b = other.coeffs[i] if i < len(other.coeffs) else GF256(0)
            result.append(a + b)
        return Polynomial(result)

    def __sub__(self, other: Polynomial) -> Polynomial:
        return self + other

    def __mul__(self, other: Polynomial | GF256) -> Polynomial:
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
        for i in range(len(self.coeffs) - 1, -1, -1):
            if self.coeffs[i].value != 0:
                return i
        return -1

    def to_bytes(self) -> bytes:
        return bytes(c.value for c in self.coeffs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Polynomial):
            return False
        return self.coeffs == other.coeffs

    def __repr__(self) -> str:
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
