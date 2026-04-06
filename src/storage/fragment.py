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
import base64


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
        fpcc_json (str | None): The full fpcc JSON string, stored for debugging
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
    fpcc_json: str | None = None

    def to_dict(self) -> dict:
        """ Serialize the fragment record to a JSON-compatible dictionary. """
        return {
            "index": self.index,
            "data": base64.b64encode(self.data).decode("ascii"),
            "block_id": self.block_id,
            "total_n": self.total_n,
            "threshold_m": self.threshold_m,
            "original_length": self.original_length,
            "received_at": self.received_at.isoformat(),
            "verification_status": self.verification_status.value,
            "fpcc_digest": self.fpcc_digest,
            "fpcc_json": self.fpcc_json,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FragmentRecord:
        """ Deserialize a FragmentRecord from a dictionary. """
        data = base64.b64decode(d["data"])
        received_at = datetime.fromisoformat(d["received_at"])
        verification_status = VerificationStatus(d["verification_status"])

        fpcc_digest = d.get("fpcc_digest")
        if fpcc_digest is not None and not isinstance(fpcc_digest, str):
            raise ValueError("fpcc_digest must be a string or None")

        fpcc_json = d.get("fpcc_json")
        if fpcc_json is not None and not isinstance(fpcc_json, str):
            raise ValueError("fpcc_json must be a string or None")


        return cls(
            index=int(d["index"]),
            data=data,
            block_id=str(d["block_id"]),
            total_n=int(d["total_n"]),
            threshold_m=int(d["threshold_m"]),
            original_length=int(d["original_length"]),
            received_at=received_at,
            verification_status=verification_status,
            fpcc_digest=fpcc_digest,
            fpcc_json=fpcc_json,
        )
