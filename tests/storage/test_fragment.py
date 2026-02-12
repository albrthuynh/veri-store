"""
test_fragment.py -- Unit tests for FragmentRecord serialization.

Covers:
    - to_dict() produces a dict with all expected keys
    - from_dict(to_dict(record)) round-trip recovers the original record
    - bytes fields are base64-encoded in the dict
    - VerificationStatus enum survives round-trip as a string
    - Timestamps survive round-trip as ISO 8601 strings
"""

import pytest
from datetime import datetime
from src.storage.fragment import FragmentRecord, VerificationStatus


class TestFragmentRecordRoundTrip:
    """Serialization round-trip tests."""

    def test_to_dict_and_back(self):
        """from_dict(to_dict(r)) == r for a typical record."""
        # TODO: r = FragmentRecord(
        #           index=2, data=b"\\xDE\\xAD\\xBE\\xEF", block_id="abc",
        #           total_n=5, threshold_m=3, original_length=100)
        #       assert FragmentRecord.from_dict(r.to_dict()) == r
        ...

    def test_data_is_base64_in_dict(self):
        """The 'data' key in to_dict() is a base64 string, not raw bytes."""
        # TODO: import base64
        #       r = FragmentRecord(index=0, data=b"bytes", block_id="id",
        #                          total_n=5, threshold_m=3, original_length=5)
        #       d = r.to_dict()
        #       assert isinstance(d["data"], str)
        #       assert base64.b64decode(d["data"]) == b"bytes"
        ...

    def test_verification_status_round_trip(self):
        """VerificationStatus enum survives to_dict / from_dict."""
        # TODO: r = FragmentRecord(..., verification_status=VerificationStatus.VALID)
        #       assert FragmentRecord.from_dict(r.to_dict()).verification_status == VerificationStatus.VALID
        ...

    def test_timestamp_round_trip(self):
        """received_at timestamp survives serialization as ISO 8601."""
        # TODO: r = FragmentRecord(... , received_at=datetime(2025, 1, 1, 12, 0))
        #       assert FragmentRecord.from_dict(r.to_dict()).received_at == r.received_at
        ...
