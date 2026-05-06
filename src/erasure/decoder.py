"""
decoder.py -- Systematic MDS erasure decoding over GF(2^8).

Reconstructs the original data block from any m (or more) of the n encoded
fragments using the inverse of the Cauchy sub-matrix corresponding to the
available fragment indices.

Decoding steps:
    1. Select exactly m fragments (discard extras).
    2. Extract the m x m sub-matrix of the coding matrix for the
       chosen fragment indices.
    3. Invert the sub-matrix over GF(2^8).
    4. Multiply the inverse by the m fragment vectors to recover the m
       original data chunks.
    5. Concatenate chunks and strip padding to recover the original data.
"""

from __future__ import annotations

from .encoder import Fragment
from .matrix import CodingMatrix


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
                    or coding parameters), or duplicate fragment indices are
                    provided.
        DecodingError: If the selected sub-matrix is singular (should not
                       happen for a well-formed coding matrix).
    """
    if not fragments:
        raise ValueError("At least one fragment is required")

    # Validate that all fragments share the same block_id, n, m.
    block_id = fragments[0].block_id
    n = fragments[0].total_n
    m = fragments[0].threshold_m
    original_length = fragments[0].original_length

    seen_indices: set[int] = set()
    for fragment in fragments:
        if (
            fragment.block_id != block_id
            or fragment.total_n != n
            or fragment.threshold_m != m
        ):
            raise ValueError("Fragments have mismatched block_id or coding parameters")

        if len(fragment.data) != len(fragments[0].data):
            raise ValueError("Fragments have inconsistent data lengths")

        if fragment.index < 0 or fragment.index >= n:
            raise ValueError("Fragment index is out of range")

        if fragment.index in seen_indices:
            raise ValueError("Fragments contain duplicate indices")

        seen_indices.add(fragment.index)

    # Check len(fragments) >= m.
    if len(fragments) < m:
        raise ValueError(f"Need at least {m} fragments to decode, got {len(fragments)}")

    # Sort fragments by index; pick the first m.
    sorted_fragments = sorted(fragments, key=lambda f: f.index)[:m]
    chunk_size = len(sorted_fragments[0].data)
    fragment_indices = [fragment.index for fragment in sorted_fragments]

    coding_matrix = CodingMatrix(m=m, n=n)
    try:
        decoding_matrix = coding_matrix.submatrix(fragment_indices).invert()
    except ValueError as error:
        raise DecodingError("Could not invert erasure coding sub-matrix") from error

    byte_chunks = [bytearray() for _ in range(m)]
    for byte_position in range(chunk_size):
        received_symbols: list[int] = []
        for fragment in sorted_fragments:
            received_symbols.append(fragment.data[byte_position])

        decoded_stripe = decoding_matrix.encode(received_symbols)
        for chunk_index, decoded_byte in enumerate(decoded_stripe):
            byte_chunks[chunk_index].append(decoded_byte)

    # Concatenate m data chunks and strip trailing zero padding using original_length.
    padded_data = b"".join(bytes(chunk) for chunk in byte_chunks)
    return padded_data[:original_length]


class DecodingError(Exception):
    """Raised when decoding fails due to an irrecoverable inconsistency.

    This may indicate Byzantine corruption: two fragments with the same index
    but different data, or a sub-matrix that unexpectedly cannot be inverted.
    """
    pass
