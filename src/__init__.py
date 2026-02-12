"""
veri-store: Distributed erasure-coded object storage with homomorphic fingerprint verification.

Based on: "Verifying Distributed Erasure-Coded Data"
          Hendricks, Ganger, and Reiter (PODC 2007)

Modules:
    fingerprint   -- GF(2^8) arithmetic and division-based homomorphic fingerprinting
    erasure       -- Reed-Solomon encoding and decoding (m-of-n)
    storage       -- Local fragment storage and metadata management
    verification  -- Fingerprinted cross-checksum (fpcc) generation and verification
    network       -- HTTP server and client for the dispersal/retrieval protocol
"""
