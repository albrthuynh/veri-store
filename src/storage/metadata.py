"""
metadata.py -- Object-level metadata for stored blocks.

The client generates metadata at dispersal time and stores it alongside (or
out-of-band from) the fragments.  Servers may also maintain per-block metadata
to answer listing queries without deserializing all fragment files.

ObjectMetadata captures:
    - Coding parameters (m, n, original length)
    - The fingerprinted cross-checksum (fpcc) for integrity verification
    - Which fragment indices this server holds
    - Creation and last-verification timestamps
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ObjectMetadata:
    """Metadata record for a single stored object (data block).

    Attributes:
        block_id (str):          Unique identifier (SHA-256 of original data).
        total_n (int):           Total coded fragments.
        threshold_m (int):       Reconstruction threshold.
        original_length (int):   Byte length of original (unpadded) data.
        fpcc (str):              JSON-serialized fingerprinted cross-checksum.
                                 See verification.cross_checksum for the format.
        stored_indices (list[int]): Fragment indices held by this server.
        created_at (datetime):   UTC time the block was first dispersed.
        last_verified_at (datetime | None): UTC time of last successful fpcc check.
    """

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
        if self.last_verified_at is None:
            return None

        return {
            "block_id": self.block_id,
            "total_n": self.total_n,
            "threshold_m": self.threshold_m,
            "original_length": self.original_length,
            "fpcc": self.fpcc,
            "stored_indices": list(self.stored_indices),
            "created_at": self.created_at.isoformat(),
            "last_verified_at": self.last_verified_at.isoformat()
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
