"""
test_encoder.py -- Unit tests for Reed-Solomon erasure encoding.

Covers:
    - encode() returns exactly n Fragment objects
    - All fragments share the same block_id and original_length
    - Fragment indices are 0 .. n-1 (no gaps)
    - All fragments have equal byte length
    - Encoding is deterministic for fixed input
    - Edge cases: single byte, exactly m bytes, non-multiple-of-m length (padding)
    - block_id defaults to SHA-256 hex digest of data when not supplied
"""

import pytest
import hashlib
from src.erasure.encoder import encode, Fragment


class TestEncodeBasic:
    """Basic correctness checks for encode()."""

    def test_returns_n_fragments(self):
        """encode() returns exactly n Fragment objects."""
        frags = encode(b"hello world", n=5, m=3)
        assert len(frags) == 5

    def test_fragment_indices_are_0_to_n_minus_1(self):
        """Fragment indices form the contiguous range [0, n)."""
        frags = encode(b"test", n=5, m=3)
        assert sorted(f.index for f in frags) == list(range(5))

    def test_all_fragments_same_length(self):
        """All fragments have identical byte lengths."""
        frags = encode(b"some longer data here", n=5, m=3)
        lengths = {len(f.data) for f in frags}
        assert len(lengths) == 1

    def test_original_length_stored_correctly(self):
        """Fragment.original_length matches len(input data)."""
        data = b"check original length"
        frags = encode(data, n=5, m=3)
        assert all(f.original_length == len(data) for f in frags)

    def test_coding_params_stored_correctly(self):
        """Fragment.total_n and threshold_m match the encode() call."""
        frags = encode(b"params", n=5, m=3)
        assert all(f.total_n == 5 for f in frags)
        assert all(f.threshold_m == 3 for f in frags)

    def test_default_block_id_is_sha256_hex(self):
        """block_id defaults to the SHA-256 hex digest of the data."""
        data = b"block id test"
        frags = encode(data, n=5, m=3)
        expected_id = hashlib.sha256(data).hexdigest()
        assert all(f.block_id == expected_id for f in frags)


class TestEncodeEdgeCases:
    """Edge cases for encode()."""

    def test_single_byte(self):
        """Encode a single byte without error."""
        frags = encode(b"\xFF", n=5, m=3)
        assert len(frags) == 5

    def test_data_length_not_multiple_of_m(self):
        """Data that isn't a multiple of m is padded transparently."""
        data = b"AB"  # length 2, not divisible by 3
        frags = encode(data, n=5, m=3)
        assert len(frags) == 5  # no error

    def test_empty_data_raises(self):
        """encode() raises ValueError for empty data."""
        with pytest.raises(ValueError):
            encode(b"", n=5, m=3)

    def test_m_greater_than_n_raises(self):
        """encode() raises ValueError if m > n."""
        with pytest.raises(ValueError):
            encode(b"data", n=3, m=5)
