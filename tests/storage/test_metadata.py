"""
test_metadata.py -- Unit tests for ObjectMetadata serialization.

Covers:
    - to_dict() / from_dict() round-trip
    - last_verified_at is None by default and serializes correctly
    - mark_verified() updates last_verified_at to approximately now
"""

import pytest
from datetime import datetime
from src.storage.metadata import ObjectMetadata


class TestObjectMetadataRoundTrip:
    """Serialization round-trip tests."""

    def test_to_dict_and_back(self):
        """from_dict(to_dict(m)) == m for a typical metadata record."""
        # TODO: meta = ObjectMetadata(
        #           block_id="abc", total_n=5, threshold_m=3,
        #           original_length=100, fpcc='{"hashes": []}',
        #           stored_indices=[0, 1])
        #       assert ObjectMetadata.from_dict(meta.to_dict()) == meta
        ...

    def test_last_verified_at_none_round_trip(self):
        """last_verified_at=None survives serialization."""
        # TODO: meta = ObjectMetadata(..., last_verified_at=None)
        #       assert ObjectMetadata.from_dict(meta.to_dict()).last_verified_at is None
        ...

    def test_mark_verified_sets_timestamp(self):
        """mark_verified() sets last_verified_at to a recent datetime."""
        # TODO: meta = ObjectMetadata(...)
        #       before = datetime.utcnow()
        #       meta.mark_verified()
        #       after = datetime.utcnow()
        #       assert before <= meta.last_verified_at <= after
        ...
