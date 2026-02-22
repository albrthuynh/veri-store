"""
test_decoder.py -- Unit tests for Reed-Solomon erasure decoding.

Covers:
    - decode() with all n fragments recovers original data
    - decode() with exactly m fragments recovers original data
    - decode() works for every possible subset of m fragments (any m out of n)
    - decode() strips padding and returns exactly original_length bytes
    - decode() raises ValueError if fewer than m fragments provided
    - decode() raises ValueError if fragments have mismatched block_ids
    - Integration: encode then decode round-trip for various data sizes
"""

import pytest
from itertools import combinations
from src.erasure.encoder import encode
from src.erasure.decoder import decode, DecodingError


class TestDecodeRoundTrip:
    """Encode then decode should recover the exact original data."""

    def test_all_fragments(self):
        """Decode using all n fragments returns original data."""
        data = b"full reconstruction"
        frags = encode(data, n=5, m=3)
        assert decode(frags) == data

    def test_exactly_m_fragments(self):
        """Decode using only the first m fragments returns original data."""
        data = b"threshold reconstruction"
        frags = encode(data, n=5, m=3)
        assert decode(frags[:3]) == data

    def test_every_m_subset(self):
        """Decode succeeds for every possible subset of m fragments."""
        data = b"subset test"
        frags = encode(data, n=5, m=3)
        for subset in combinations(frags, 3):
            assert decode(list(subset)) == data

    def test_preserves_original_length_with_padding(self):
        """Decoded output has exactly original_length bytes (padding stripped)."""
        data = b"AB"  # will be padded during encoding
        frags = encode(data, n=5, m=3)
        assert decode(frags[:3]) == data
        assert len(decode(frags[:3])) == 2

    def test_large_data(self):
        """Round-trip works for 64 KB of random-ish data."""
        data = bytes(range(256)) * 256  # 64 KB
        frags = encode(data, n=5, m=3)
        assert decode(frags[:3]) == data


class TestDecodeErrors:
    """Error handling in decode()."""

    def test_too_few_fragments_raises(self):
        """decode() raises ValueError if fewer than m fragments are provided."""
        frags = encode(b"data", n=5, m=3)
        with pytest.raises(ValueError):
            decode(frags[:2])

    def test_mismatched_block_ids_raises(self):
        """decode() raises ValueError if fragments belong to different blocks."""
        frags_a = encode(b"block a", n=5, m=3, block_id="a")
        frags_b = encode(b"block b", n=5, m=3, block_id="b")
        mixed = frags_a[:2] + frags_b[2:3]
        with pytest.raises(ValueError):
            decode(mixed)

    def test_empty_fragments_raises(self):
        """decode() raises ValueError when given no fragments."""
        with pytest.raises(ValueError):
            decode([])
