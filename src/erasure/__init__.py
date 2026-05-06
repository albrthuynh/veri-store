"""
erasure -- Systematic MDS erasure coding over GF(2^8).

Implements the m-of-n threshold scheme: a data block B is split into n
fragments such that any m fragments suffice to reconstruct B.

Default parameters from the project README:
    m = 3   (reconstruction threshold)
    n = 5   (total fragments: n = m + 2*f where f=1 is fault tolerance)
    f = 1   (tolerated erasures / Byzantine faults)

The encoding matrix is a project-owned systematic Cauchy-derived matrix over
GF(2^8), using the finite-field arithmetic in src.fingerprint.field.

Public API:
    encode(data, n, m)  -> list of n equal-length byte fragments
    decode(fragments)   -> reconstructed data bytes
    CodingMatrix        -> the systematic MDS matrix construction
"""

from .encoder import encode
from .decoder import decode, DecodingError
from .matrix import CodingMatrix

# Default coding parameters (3-of-5 scheme).
DEFAULT_M: int = 3
DEFAULT_N: int = 5
