from __future__ import annotations

IRREDUCIBLE_POLY: int = 0x11B

# Pre-compute the multiplicative inverse table for all non-zero elements.
_INVERSE_TABLE = [0] * 256
for _a in range(1, 256):
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
    def __init__(self, value: int) -> None:
        self.value = value & 0xFF

    # ------------------------------------------------------------------
    # Arithmetic operators
    # ------------------------------------------------------------------

    def __add__(self, other: GF256) -> GF256:
        return GF256(self.value ^ other.value)

    def __sub__(self, other: GF256) -> GF256:
        return self + other

    def __mul__(self, other: GF256) -> GF256:
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
        if other.value == 0:
            raise ZeroDivisionError("division by zero in GF(2^8)")
        return self * other.inverse()

    def __pow__(self, exp: int) -> GF256:
        result = GF256(1)
        base = GF256(self.value)
        while exp > 0:
            if exp & 1:
                result = result * base
            base = base * base
            exp >>= 1
        return result

    def inverse(self) -> GF256:
        if self.value == 0:
            raise ZeroDivisionError(
                "zero element has no multiplicative inverse in GF(2^8)"
            )
        return GF256(_INVERSE_TABLE[self.value])

    # ------------------------------------------------------------------
    # Comparison and representation
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GF256):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"GF256(Hexadecimal: 0x{self.value:02X}, Decimal: {self.value}, Binary: {self.value:08b})"

    def __int__(self) -> int:
        return self.value


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def build_exp_log_tables(
    poly: int = IRREDUCIBLE_POLY, generator: int = 0x03
) -> tuple[list[int], list[int]]:
    exp_table = [0] * 256
    log_table = [0] * 256

    def _mul_mod(a: int, b: int) -> int:
        result = 0
        x = a
        y = b
        while y > 0:
            if y & 1:
                result ^= x
            y >>= 1
            x <<= 1
            if x & 0x100:
                x ^= poly
        return result & 0xFF

    x = 1
    for i in range(255):
        exp_table[i] = x
        log_table[x] = i
        # Use a primitive generator so powers enumerate all 255 non-zero values.
        # In the AES field (poly=0x11B), 0x03 is primitive while 0x02 is not.
        x = _mul_mod(x, generator)

    exp_table[255] = 1

    return exp_table, log_table


# Module-level precomputed tables for O(1) GF arithmetic
_EXP, _LOG = build_exp_log_tables()


# Fast int arithmetic
def gf_add(a: int, b: int) -> int:
    return a ^ b


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[(_LOG[a] + _LOG[b]) % 255]


def gf_div(a: int, b: int) -> int:
    if b == 0:
        raise ZeroDivisionError("division by zero in GF(2^8)")
    if a == 0:
        return 0
    return _EXP[(_LOG[a] - _LOG[b]) % 255]


def gf_inv(a: int) -> int:
    if a == 0:
        raise ZeroDivisionError("zero element has no multiplicative inverse in GF(2^8)")
    return _INVERSE_TABLE[a]
