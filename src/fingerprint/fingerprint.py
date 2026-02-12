"""
fingerprint.py -- Division-based homomorphic fingerprinting (Theorem 2.3).

The fingerprint of a data block d at evaluation point r is:

    fp(r, d) = d(r)   where d is treated as a polynomial over GF(2^8)

This is the "evaluation fingerprint" variant.  The critical property:

    fp(r, alpha * d1 + beta * d2) = alpha * fp(r, d1) + beta * fp(r, d2)

That is, fp is *linear* in the data, which mirrors the linearity of
Reed-Solomon codes.  A server holding fragment d_i can be checked against a
fingerprinted cross-checksum without the client reconstructing the full block.

References:
    Hendricks, Ganger, Reiter (PODC 2007), Theorem 2.3 and Definition 2.4
"""

from __future__ import annotations
from .field import GF256
from .polynomial import Polynomial


def fingerprint(r: GF256, data: bytes) -> GF256:
    """Compute the homomorphic fingerprint of data at evaluation point r.

    Treats `data` as a polynomial d(x) over GF(2^8) (each byte is a
    coefficient) and evaluates it at the field point r:

        fp(r, data) = d(r)  in GF(2^8)

    Args:
        r:    Evaluation point drawn from GF(2^8).  Should be chosen via the
              random oracle (see verification.oracle) to prevent forgery.
        data: The raw bytes of the data block (or fragment) to fingerprint.

    Returns:
        A GF256 element representing the fingerprint.
    """
    # TODO: 1. Build Polynomial.from_bytes(data)
    # TODO: 2. Return poly.evaluate(r)
    ...


def random_point(seed: bytes) -> GF256:
    """Derive a pseudorandom evaluation point r from a seed using SHA-256.

    This acts as a random oracle mapping seed -> r in GF(2^8).  The seed
    should be a commitment to all fragment hashes so that the point r is
    unpredictable until after the fragments are fixed.

    Args:
        seed: Arbitrary bytes used as the oracle input (typically the
              concatenation of all fragment hash digests).

    Returns:
        A GF256 element to use as the fingerprint evaluation point.
    """
    # TODO: 1. Compute SHA-256(seed)
    # TODO: 2. Take the first byte of the digest as the field element.
    # TODO: Note: Using only 1 byte gives q=256 and a collision probability
    #       of 1/256 per check (Theorem 3.4).  Document this clearly.
    ...


def verify_homomorphic_property(
    r: GF256,
    data1: bytes,
    data2: bytes,
    coefficients: tuple[GF256, GF256],
) -> bool:
    """Sanity-check that the linearity property holds for given inputs.

    Verifies:
        fp(r, a*d1 XOR b*d2) == a*fp(r,d1) XOR b*fp(r,d2)

    This function is intended for testing and debugging only.

    Args:
        r:            Evaluation point.
        data1:        First data block (bytes, same length as data2).
        data2:        Second data block (bytes, same length as data1).
        coefficients: A pair (a, b) of GF256 scalars.

    Returns:
        True if the homomorphic property holds, False otherwise.

    Raises:
        ValueError: If data1 and data2 have different lengths.
    """
    # TODO: 1. Compute the fingerprint of the linear combination on the left.
    # TODO: 2. Compute the linear combination of fingerprints on the right.
    # TODO: 3. Return left == right.
    ...
