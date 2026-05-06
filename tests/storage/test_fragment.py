import base64
from datetime import datetime
from src.storage.fragment import FragmentRecord, VerificationStatus


class TestFragmentRecordRoundTrip:
    """Serialization round-trip tests."""

    def test_to_dict_and_back(self):
        """from_dict(to_dict(r)) == r for a typical record."""
        record = FragmentRecord(
            index=2,
            data=b"\xde\xad\xbe\xef",
            block_id="abc",
            total_n=5,
            threshold_m=3,
            original_length=100,
        )
        assert FragmentRecord.from_dict(record.to_dict()) == record

    def test_data_is_base64_in_dict(self):
        """The 'data' key in to_dict() is a base64 string, not raw bytes."""
        record = FragmentRecord(
            index=0,
            data=b"bytes",
            block_id="id",
            total_n=5,
            threshold_m=3,
            original_length=5,
        )
        data = record.to_dict()
        assert isinstance(data["data"], str)
        assert base64.b64decode(data["data"]) == b"bytes"

    def test_verification_status_round_trip(self):
        """VerificationStatus enum survives to_dict / from_dict."""
        record = FragmentRecord(
            index=1,
            data=b"valid",
            block_id="status-block",
            total_n=5,
            threshold_m=3,
            original_length=5,
            verification_status=VerificationStatus.VALID,
        )
        restored = FragmentRecord.from_dict(record.to_dict())
        assert restored.verification_status == VerificationStatus.VALID

    def test_timestamp_round_trip(self):
        """received_at timestamp survives serialization as ISO 8601."""
        record = FragmentRecord(
            index=4,
            data=b"time",
            block_id="timestamp-block",
            total_n=5,
            threshold_m=3,
            original_length=4,
            received_at=datetime(2025, 1, 1, 12, 0),
        )
        restored = FragmentRecord.from_dict(record.to_dict())
        assert restored.received_at == record.received_at
