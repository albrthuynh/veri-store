"""
fingerprint -- Homomorphic fingerprinting over GF(2^8).

This package implements the division-based fingerprinting scheme described in
Theorem 2.3 of Hendricks, Ganger, and Reiter (PODC 2007).

A fingerprint fp(r, d) is computed by treating a data block d as a polynomial
over GF(2^8) evaluated at a random point r.  The key property is:

    fp(r, d1 + d2) = fp(r, d1) + fp(r, d2)          (additive homomorphism)

This lets a verifier check that an erasure-coded fragment is consistent with a
stored fingerprint *without* reconstructing the full block.

Public API:
    GF256          -- field element type (from field.py)
    Polynomial     -- polynomial over GF(2^8) (from polynomial.py)
    fingerprint    -- fp(r, data) -> GF256 (from fingerprint.py)
"""

from .field import GF256
from .polynomial import Polynomial
from .fingerprint import fingerprint, random_point
