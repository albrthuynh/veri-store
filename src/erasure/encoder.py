from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .matrix import CodingMatrix


@dataclass
class Fragment:
    index: int
    data: bytes
    block_id: str
    total_n: int
    threshold_m: int
    original_length: int


def encode(
    data: bytes,
    n: int = 5,
    m: int = 3,
    block_id: str = "",
) -> list[Fragment]:
    if not data:
        raise ValueError("data must not be empty")

    coding_matrix = CodingMatrix(m=m, n=n)

    if not block_id:
        block_id = hashlib.sha256(data).hexdigest()

    # Pad data so that it splits evenly into m chunks.
    padded_data = _pad(data, m)

    # Split padded data into m equal-length chunks.
    chunk_size = len(padded_data) // m
    byte_chunks: list[bytes] = []
    for chunk_index in range(m):
        start = chunk_index * chunk_size
        end = start + chunk_size
        byte_chunks.append(padded_data[start:end])

    fragment_outputs = [bytearray() for _ in range(n)]

    for byte_position in range(chunk_size):
        stripe: list[int] = []
        for chunk in byte_chunks:
            stripe.append(chunk[byte_position])

        codeword = coding_matrix.encode(stripe)

        for fragment_index, encoded_byte in enumerate(codeword):
            fragment_outputs[fragment_index].append(encoded_byte)

    # Collect fragment buffers into Fragment objects with shared metadata.
    fragments: list[Fragment] = []
    for fragment_index, fragment_data in enumerate(fragment_outputs):
        fragments.append(
            Fragment(
                index=fragment_index,
                data=bytes(fragment_data),
                block_id=block_id,
                total_n=n,
                threshold_m=m,
                original_length=len(data),
            )
        )
    return fragments


def _pad(data: bytes, m: int) -> bytes:
    remainder = len(data) % m
    padding_needed = (m - remainder) % m
    return data + (b"\x00" * padding_needed)
