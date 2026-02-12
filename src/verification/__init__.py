"""
verification -- Fingerprinted cross-checksum (fpcc) protocol.

This package implements the core integrity protocol from Section 3 of
Hendricks, Ganger, and Reiter (PODC 2007).

Concept:
    After encoding a data block B into n fragments d_0 ... d_{n-1}, the client
    computes a *fingerprinted cross-checksum* (fpcc):

        fpcc = (h_0, ..., h_{n-1}, phi_0, ..., phi_{m-1})

    where:
        h_i   = SHA-256(d_i)                    -- hash of each fragment
        r     = oracle(h_0 || ... || h_{n-1})   -- pseudorandom evaluation point
        phi_j = fp(r, d_j)  for j in [0, m)    -- fingerprints of first m fragments

    A server holding fragment d_i can verify its consistency without seeing
    other fragments: it recomputes h_i, checks it matches the stored hash, and
    if i < m it also checks fp(r, d_i) == phi_i.

Public API:
    FingerprintedCrossChecksum  -- fpcc data structure (from cross_checksum.py)
    RandomOracle                -- deterministic r derivation (from oracle.py)
    Verifier                    -- server-side consistency check (from verifier.py)
"""

from .cross_checksum import FingerprintedCrossChecksum
from .oracle import RandomOracle
from .verifier import Verifier, VerificationResult
