"""
test_oracle.py -- Unit tests for the RandomOracle.

Covers:
    - derive() is deterministic for the same hashes
    - derive() returns a GF256 element in [0, 255]
    - derive() raises ValueError for empty hash list
    - hash_fragment() returns a 32-byte SHA-256 digest
    - hash_fragment() is deterministic
    - Different fragment data produces different hashes (probabilistic)
"""

import pytest
from src.verification.oracle import RandomOracle
from src.fingerprint.field import GF256


class TestRandomOracleDerive:
    """Tests for RandomOracle.derive()."""

    def test_deterministic(self):
        """Same fragment hashes always produce the same r."""
        # TODO: hashes = [b"\\x00" * 32, b"\\xFF" * 32, b"\\xAB" * 32]
        #       assert RandomOracle.derive(hashes) == RandomOracle.derive(hashes)
        ...

    def test_returns_gf256(self):
        """derive() returns a GF256 element."""
        # TODO: hashes = [b"\\x00" * 32]
        #       r = RandomOracle.derive(hashes)
        #       assert isinstance(r, GF256)
        ...

    def test_empty_hashes_raises(self):
        """derive() raises ValueError for an empty list."""
        # TODO: with pytest.raises(ValueError): RandomOracle.derive([])
        ...

    def test_different_hashes_likely_different_r(self):
        """Different hash vectors should (usually) produce different r values."""
        # TODO: r1 = RandomOracle.derive([b"\\x00" * 32])
        #       r2 = RandomOracle.derive([b"\\xFF" * 32])
        #       assert r1 != r2  # highly likely for different inputs
        ...


class TestHashFragment:
    """Tests for RandomOracle.hash_fragment()."""

    def test_returns_32_bytes(self):
        """hash_fragment() returns a 32-byte digest."""
        # TODO: assert len(RandomOracle.hash_fragment(b"data")) == 32
        ...

    def test_deterministic(self):
        """Same data produces the same hash."""
        # TODO: assert RandomOracle.hash_fragment(b"same") == RandomOracle.hash_fragment(b"same")
        ...

    def test_different_data_different_hash(self):
        """Different data should produce different hashes."""
        # TODO: assert RandomOracle.hash_fragment(b"a") != RandomOracle.hash_fragment(b"b")
        ...
