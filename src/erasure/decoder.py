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
from reedsolo import RSCodec, ReedSolomonError


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
    if not fragments:
        raise ValueError("At least one fragment is required")

    # Validate that all fragments share the same block_id, n, m.
    block_id = fragments[0].block_id
    n = fragments[0].total_n
    m = fragments[0].threshold_m
    original_length = fragments[0].original_length

    for f in fragments:
        if f.block_id != block_id or f.total_n != n or f.threshold_m != m:
            raise ValueError("Fragments have mismatched block_id or coding parameters")
        if len(f.data) != len(fragments[0].data):
            raise ValueError("Fragments have inconsistent data lengths")

    # Check len(fragments) >= m.
    if len(fragments) < m:
        raise ValueError(f"Need at least {m} fragments to decode, got {len(fragments)}")

    # Sort fragments by index; pick the first m.
    sorted_fragments = sorted(fragments, key=lambda f: f.index)[:m]
    chunk_size = len(sorted_fragments[0].data)

    # Rebuild RSCodec same as encoder; decode each column with erasures at missing indices.
    rsc = RSCodec(n - m)
    fragment_indices = [f.index for f in sorted_fragments]
    erase_pos = [i for i in range(n) if i not in fragment_indices]

    # For each byte column, build received codeword and decode to get the m-byte stripe.
    byte_chunks = [bytearray() for _ in range(m)]
    for col in range(chunk_size):
        received = bytearray(n)
        for i, f in enumerate(sorted_fragments):
            received[f.index] = f.data[col]
        try:
            decoded_stripe, _, _ = rsc.decode(bytes(received), erase_pos=erase_pos)
        except ReedSolomonError as e:
            raise DecodingError("Reed-Solomon decoding failed") from e
        for j in range(m):
            byte_chunks[j].append(decoded_stripe[j])

    # Concatenate m data chunks and strip trailing zero padding using original_length.
    padded_data = b"".join(bytes(chunk) for chunk in byte_chunks)
    return padded_data[:original_length]


class DecodingError(Exception):
    """Raised when decoding fails due to an irrecoverable inconsistency.

    This may indicate Byzantine corruption: two fragments with the same index
    but different data, or a sub-matrix that unexpectedly cannot be inverted.
    """
    pass
