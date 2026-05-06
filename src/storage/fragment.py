from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import base64


class VerificationStatus(Enum):
    UNVERIFIED = "unverified"
    VALID = "valid"
    INVALID = "invalid"


@dataclass
class FragmentRecord:
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
