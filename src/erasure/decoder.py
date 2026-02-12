"""
decoder.py -- Reed-Solomon erasure decoding.

Reconstructs the original data block from any m (or more) of the n encoded
fragments using the inverse of the Cauchy sub-matrix corresponding to the
available fragment indices.

Decoding steps:
    1. Select exactly m fragments (discard extras).
    2. Extract the m×m sub-matrix of the Cauchy encoding matrix for the
       chosen fragment indices.
    3. Invert the sub-matrix over GF(2^8).
    4. Multiply the inverse by the m fragment vectors to recover the m
       original data chunks.
    5. Concatenate chunks and strip padding to recover the original data.
"""

from __future__ import annotations
from .encoder import Fragment


def decode(fragments: list[Fragment]) -> bytes:
    """Reconstruct the original data from a sufficient set of fragments.

    Args:
        fragments: A list of at least m Fragment objects for the same block.
                   Extra fragments beyond m are ignored.  Fragments may be
                   provided in any order; their .index field identifies them.

    Returns:
        The original data bytes (with padding stripped).

    Raises:
        ValueError: If fewer than m fragments are provided, or if the
                    fragments belong to different blocks (mismatched block_id
                    or coding parameters).
        DecodingError: If the selected sub-matrix is singular (should not
                       happen for a well-formed Cauchy matrix).
    """
    # TODO: 1. Validate that all fragments share the same block_id, n, m.
    # TODO: 2. Check len(fragments) >= m.
    # TODO: 3. Sort fragments by index; pick the first m.
    # TODO: 4. Rebuild CodingMatrix(m, n), extract sub-matrix for chosen indices.
    # TODO: 5. Invert the sub-matrix.
    # TODO: 6. Apply inverse to fragment data byte-column by byte-column.
    # TODO: 7. Concatenate m data chunks and strip trailing zero padding using
    #          fragment.original_length.
    ...


class DecodingError(Exception):
    """Raised when decoding fails due to an irrecoverable inconsistency.

    This may indicate Byzantine corruption: two fragments with the same index
    but different data, or a sub-matrix that unexpectedly cannot be inverted.
    """
