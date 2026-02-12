"""
test_cross_checksum.py -- Unit tests for FingerprintedCrossChecksum (fpcc).

Covers:
    - generate() produces n hashes and m fingerprints
    - hashes match SHA-256 of each fragment's data
    - fingerprints match fp(r, d_j) for j < m
    - r in the fpcc equals RandomOracle.derive(hashes)
    - to_json() / from_json() round-trip preserves all fields
    - digest() returns a stable hex string for the same fpcc
"""

import pytest
import hashlib
from src.erasure.encoder import encode
from src.verification.cross_checksum import FingerprintedCrossChecksum
from src.verification.oracle import RandomOracle
from src.fingerprint.fingerprint import fingerprint


class TestFPCCGenerate:
    """Tests for FingerprintedCrossChecksum.generate()."""

    def test_correct_number_of_hashes_and_fingerprints(self):
        """fpcc has n hashes and m fingerprints."""
        # TODO: frags = encode(b"test block", n=5, m=3)
        #       fpcc = FingerprintedCrossChecksum.generate(frags)
        #       assert len(fpcc.hashes) == 5
        #       assert len(fpcc.fingerprints) == 3
        ...

    def test_hashes_match_sha256(self):
        """Each fpcc hash equals SHA-256 of the corresponding fragment."""
        # TODO: frags = encode(b"hash check", n=5, m=3)
        #       fpcc = FingerprintedCrossChecksum.generate(frags)
        #       for i, frag in enumerate(frags):
        #           expected = hashlib.sha256(frag.data).digest()
        #           assert fpcc.hashes[i] == expected
        ...

    def test_fingerprints_match_fp_function(self):
        """Each stored fingerprint equals fp(r, d_j) for j < m."""
        # TODO: frags = encode(b"fp check", n=5, m=3)
        #       fpcc = FingerprintedCrossChecksum.generate(frags)
        #       for j in range(3):
        #           expected = fingerprint(fpcc.r, frags[j].data)
        #           assert fpcc.fingerprints[j] == expected
        ...

    def test_r_matches_oracle(self):
        """The stored r equals RandomOracle.derive(hashes)."""
        # TODO: frags = encode(b"oracle check", n=5, m=3)
        #       fpcc = FingerprintedCrossChecksum.generate(frags)
        #       expected_r = RandomOracle.derive(fpcc.hashes)
        #       assert fpcc.r == expected_r
        ...


class TestFPCCSerialization:
    """Tests for to_json() / from_json() round-trip."""

    def test_json_round_trip(self):
        """from_json(to_json(fpcc)) == fpcc (structural equality)."""
        # TODO: frags = encode(b"serialize me", n=5, m=3)
        #       fpcc = FingerprintedCrossChecksum.generate(frags)
        #       assert FingerprintedCrossChecksum.from_json(fpcc.to_json()) == fpcc
        ...

    def test_digest_is_stable(self):
        """digest() returns the same hex string for the same fpcc."""
        # TODO: frags = encode(b"digest test", n=5, m=3)
        #       fpcc = FingerprintedCrossChecksum.generate(frags)
        #       assert fpcc.digest() == fpcc.digest()
        ...
