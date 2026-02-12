"""
erasure -- Reed-Solomon erasure coding over GF(2^8).

Implements the m-of-n threshold scheme: a data block B is split into n
fragments such that any m fragments suffice to reconstruct B.

Default parameters from the project README:
    m = 3   (reconstruction threshold)
    n = 5   (total fragments: n = m + 2*f where f=1 is fault tolerance)
    f = 1   (tolerated erasures / Byzantine faults)

The encoding matrix is a Cauchy (or systematic Vandermonde) matrix over
GF(2^8).  The `galois` library provides optimised GF arithmetic.

Public API:
    encode(data, n, m)  -> list of n equal-length byte fragments
    decode(fragments)   -> reconstructed data bytes
    CodingMatrix        -> the Cauchy matrix construction (from matrix.py)
"""

from .encoder import encode
from .decoder import decode
from .matrix import CodingMatrix

# Default coding parameters (3-of-5 scheme).
DEFAULT_M: int = 3
DEFAULT_N: int = 5
