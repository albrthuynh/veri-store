from __future__ import annotations

from .encoder import Fragment
from .matrix import CodingMatrix


def decode(fragments: list[Fragment]) -> bytes:
    if not fragments:
        raise ValueError("At least one fragment is required")

    # All fragments must describe the same encoded block.
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

    if len(fragments) < m:
        raise ValueError(f"Need at least {m} fragments to decode, got {len(fragments)}")

    # Decode with exactly m fragments; extra valid fragments are not needed.
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

    # Remove zero padding added during encoding.
    padded_data = b"".join(bytes(chunk) for chunk in byte_chunks)
    return padded_data[:original_length]


class DecodingError(Exception):
    pass
