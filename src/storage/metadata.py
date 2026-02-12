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
        """Serialize to a JSON-compatible dictionary.

        Returns:
            All fields as JSON-safe types (datetimes as ISO 8601 strings).
        """
        # TODO: Serialize all fields; handle None for last_verified_at.
        ...

    @classmethod
    def from_dict(cls, d: dict) -> ObjectMetadata:
        """Deserialize from a dictionary.

        Args:
            d: A dict produced by to_dict().

        Returns:
            An ObjectMetadata instance.
        """
        # TODO: Parse ISO datetime strings; handle None for last_verified_at.
        ...

    def mark_verified(self) -> None:
        """Update last_verified_at to the current UTC time."""
        # TODO: self.last_verified_at = datetime.utcnow()
        ...
