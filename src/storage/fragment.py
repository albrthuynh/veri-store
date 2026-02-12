"""
fragment.py -- Server-side fragment record model.

Extends the encoder's Fragment with fields that the storage server tracks:
receipt timestamp, verification status, and the FPCC associated with the block.

This model is what gets persisted to disk and returned in GET responses.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class VerificationStatus(Enum):
    """Lifecycle of a fragment's integrity check.

    UNVERIFIED  -- Fragment has been stored but not yet checked against fpcc.
    VALID       -- Fragment passed the most recent consistency check.
    INVALID     -- Fragment failed verification (possible Byzantine corruption).
    """
    UNVERIFIED = "unverified"
    VALID = "valid"
    INVALID = "invalid"


@dataclass
class FragmentRecord:
    """A fragment as stored and tracked by a veri-store server.

    Attributes:
        index (int):          Fragment index in [0, total_n).
        data (bytes):         Raw fragment bytes.
        block_id (str):       Unique identifier for the originating data block.
        total_n (int):        Total number of fragments in the coding scheme.
        threshold_m (int):    Reconstruction threshold.
        original_length (int):Byte length of the original (unpadded) data block.
        received_at (datetime): UTC timestamp when the fragment arrived.
        verification_status (VerificationStatus): Result of the last fpcc check.
        fpcc_digest (str | None): Hex digest of the fpcc this fragment was
                                   stored with, for re-verification on demand.
    """

    index: int
    data: bytes
    block_id: str
    total_n: int
    threshold_m: int
    original_length: int
    received_at: datetime = field(default_factory=datetime.utcnow)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    fpcc_digest: str | None = None

    def to_dict(self) -> dict:
        """Serialize the fragment record to a JSON-compatible dictionary.

        Returns:
            A dict with all fields serialized to JSON-safe types.
            bytes fields are base64-encoded; datetime is ISO 8601.
        """
        # TODO: Serialize each field. Use base64.b64encode for self.data.
        # TODO: Use received_at.isoformat() for the timestamp.
        ...

    @classmethod
    def from_dict(cls, d: dict) -> FragmentRecord:
        """Deserialize a FragmentRecord from a dictionary.

        Args:
            d: A dict in the format produced by to_dict().

        Returns:
            A FragmentRecord instance.

        Raises:
            KeyError:   If a required field is missing.
            ValueError: If a field value is malformed.
        """
        # TODO: Decode base64 data, parse ISO datetime, map string to enum.
        ...
