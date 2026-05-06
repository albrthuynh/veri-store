"""
encoder.py -- Systematic MDS erasure encoding over GF(2^8).

Takes a raw data block and produces n equal-length byte fragments using the
project-owned coding matrix.  Fragments are labelled by their index (0 to n-1)
so that the decoder knows which rows to use for reconstruction.

Encoding steps:
    1. Pad data to a multiple of m bytes (chunk size = ceil(len(data) / m)).
    2. Split data into m equal-length chunks.
    3. For each byte position across chunks, apply the n x m encoding matrix.
    4. Return n fragments, each of the same byte length as one chunk.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .matrix import CodingMatrix


@dataclass
class Fragment:
    """A single encoded fragment produced by the encoder.

    Attributes:
        index (int):  Fragment index in [0, n).  Identifies which server
                      should store this fragment.
        data  (bytes): The raw bytes of the fragment (one chunk row of the
                       coded codeword).
        block_id (str): Identifier for the originating data block (e.g. SHA-256
                        hash of the original data, or a user-supplied key).
        total_n (int): Total number of fragments n in the coding scheme.
        threshold_m (int): Minimum fragments m needed for reconstruction.
        original_length (int): Byte length of the pre-padding original data.
                               Required for correct unpadding on decode.
    """

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
    """Encode a data block into n erasure-coded fragments.

    Args:
        data:     The raw data bytes to encode.  May be any length > 0.
        n:        Total number of fragments to produce (default 5).
        m:        Reconstruction threshold — any m fragments suffice
                  to recover `data` (default 3).
        block_id: Caller-supplied identifier for this block.  If empty,
                  defaults to the hex digest of SHA-256(data).

    Returns:
        A list of n Fragment objects, in index order [0 .. n-1].

    Raises:
        ValueError: If data is empty, or if m > n, or if n + m > 256.
    """
    if not data:
        raise ValueError("data must not be empty")

    coding_matrix = CodingMatrix(m=m, n=n)

    if not block_id:
        block_id = hashlib.sha256(data).hexdigest()

    # Pad data so that len(data) is a multiple of m.
    padded_data = _pad(data, m)

    # Split padded data into m equal-length byte chunks.
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

    # Collect results into n Fragment objects.
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
    """Pad data with zero bytes to the next multiple of m.

    Args:
        data: Original byte string.
        m:    Chunk count (row dimension of the encoding matrix).

    Returns:
        Padded bytes of length ceil(len(data) / m) * m.
    """
    remainder = len(data) % m
    padding_needed = (m - remainder) % m
    return data + (b"\x00" * padding_needed)
