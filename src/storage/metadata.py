from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ObjectMetadata:
    block_id: str
    total_n: int
    threshold_m: int
    original_length: int
    fpcc: str
    stored_indices: list[int] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_verified_at: datetime | None = None

    def to_dict(self) -> dict:
        """ Serialize to a JSON-compatible dictionary. """
        return {
            "block_id": self.block_id,
            "total_n": self.total_n,
            "threshold_m": self.threshold_m,
            "original_length": self.original_length,
            "fpcc": self.fpcc,
            "stored_indices": list(self.stored_indices),
            "created_at": self.created_at.isoformat(),
            "last_verified_at": (
                self.last_verified_at.isoformat()
                if self.last_verified_at is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, d: dict) -> ObjectMetadata:
        """ Deserialize from a dictionary. returning a ObjectMetadata instance """
        last_verified_raw: Any = d.get("last_verified_at", None)
        last_verified_at = (
            datetime.fromisoformat(last_verified_raw)
            if isinstance(last_verified_raw, str)
            else None
        )

        return cls(
            block_id=str(d["block_id"]),
            total_n=int(d["total_n"]),
            threshold_m=int(d["threshold_m"]),
            original_length=int(d["original_length"]),
            fpcc=str(d["fpcc"]),
            stored_indices=[int(i) for i in d.get("stored_indices", [])],
            created_at=datetime.fromisoformat(d["created_at"]),
            last_verified_at=last_verified_at,
        )

    def mark_verified(self) -> None:
        """Update last_verified_at to the current UTC time."""
        self.last_verified_at = datetime.utcnow()
