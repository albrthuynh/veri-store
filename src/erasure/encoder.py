"""
encoder.py -- Reed-Solomon erasure encoding.

Takes a raw data block and produces n equal-length byte fragments using the
Cauchy encoding matrix.  Fragments are labelled by their index (0 to n-1) so
that the decoder knows which rows to use for reconstruction.

Encoding steps:
    1. Pad data to a multiple of m bytes (chunk size = ceil(len(data) / m)).
    2. Split data into m equal-length chunks.
    3. For each byte position across chunks, apply the n×m encoding matrix.
    4. Return n fragments, each of the same byte length as one chunk.

The `reedsolo` library may be used as a reference or replaced by a direct
Cauchy-matrix implementation via the `galois` library.
"""

from __future__ import annotations
from dataclasses import dataclass


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
        ValueError: If data is empty, or if m > n, or if n + m > 256
                    (Cauchy matrix constraint).
    """
    # TODO: 1. Validate arguments (m <= n, n+m <= 256, data non-empty).
    # TODO: 2. Compute block_id = SHA-256(data).hex() if block_id is empty.
    # TODO: 3. Pad data so that len(data) is a multiple of m.
    # TODO: 4. Split padded data into m equal-length byte chunks.
    # TODO: 5. Build CodingMatrix(m, n).
    # TODO: 6. For each byte position, apply encoding matrix across chunks.
    # TODO: 7. Collect results into n Fragment objects.
    ...


def _pad(data: bytes, m: int) -> bytes:
    """Pad data with zero bytes to the next multiple of m.

    Args:
        data: Original byte string.
        m:    Chunk count (row dimension of the encoding matrix).

    Returns:
        Padded bytes of length ceil(len(data) / m) * m.
    """
    # TODO: Compute remainder and append b'\\x00' * padding_needed.
    ...
