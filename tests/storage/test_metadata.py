from datetime import datetime
from src.storage.metadata import ObjectMetadata


class TestObjectMetadataRoundTrip:
    """Serialization round-trip tests."""

    def test_to_dict_and_back(self):
        """from_dict(to_dict(m)) == m for a typical metadata record."""
        created_at = datetime(2025, 1, 1, 12, 0, 0)
        verified_at = datetime(2025, 1, 1, 12, 5, 0)
        meta = ObjectMetadata(
            block_id="abc",
            total_n=5,
            threshold_m=3,
            original_length=100,
            fpcc='{"hashes": []}',
            stored_indices=[0, 1],
            created_at=created_at,
            last_verified_at=verified_at,
        )
        assert ObjectMetadata.from_dict(meta.to_dict()) == meta

    def test_last_verified_at_none_round_trip(self):
        """last_verified_at=None survives serialization."""
        meta = ObjectMetadata(
            block_id="none-case",
            total_n=5,
            threshold_m=3,
            original_length=42,
            fpcc='{"hashes": []}',
            stored_indices=[2, 4],
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            last_verified_at=None,
        )
        restored = ObjectMetadata.from_dict(meta.to_dict())
        assert restored.last_verified_at is None

    def test_mark_verified_sets_timestamp(self):
        """mark_verified() sets last_verified_at to a recent datetime."""
        meta = ObjectMetadata(
            block_id="verify-case",
            total_n=5,
            threshold_m=3,
            original_length=64,
            fpcc='{"hashes": []}',
        )
        before = datetime.utcnow()
        meta.mark_verified()
        after = datetime.utcnow()
        assert meta.last_verified_at is not None
        assert before <= meta.last_verified_at <= after
