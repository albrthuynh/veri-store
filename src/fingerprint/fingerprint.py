from __future__ import annotations

from .field import GF256
from .polynomial import Polynomial


def fingerprint(r: GF256, data: bytes) -> GF256:
    poly = Polynomial.from_bytes(data)
    return poly.evaluate(r)


def random_point(seed: bytes) -> GF256:
    from src.verification.oracle import RandomOracle

    counter = 0

    while True:
        digest = RandomOracle.hash_fragment(seed + counter.to_bytes(4, "big"))
        r = GF256(digest[0])

        if r.value != 0:
            return r

        counter += 1


def verify_homomorphic_property(
    r: GF256,
    data1: bytes,
    data2: bytes,
    coefficients: tuple[GF256, GF256],
) -> bool:
    if len(data1) != len(data2):
        raise ValueError("data1 and data2 must have the same length")

    a, b = coefficients
    combined = bytes((a * GF256(x) + b * GF256(y)).value for x, y in zip(data1, data2))

    left = fingerprint(r, combined)
    right = (a * fingerprint(r, data1)) + (b * fingerprint(r, data2))
    return left == right
