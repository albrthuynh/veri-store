"""
store.py -- Disk-backed key-value store for fragment records.

Each server persists fragments under a configurable base directory:

    <base_dir>/
        <block_id>/
            fragment_<index>.json   -- JSON-serialized FragmentRecord

Fragments are addressed by (block_id, fragment_index).  The store provides
CRUD operations and an iterator over all stored fragments for a given block.

Thread safety: individual file writes are atomic via write-then-rename, but
concurrent access from multiple threads is not otherwise guarded.  The server
layer is responsible for serialising access if needed.
"""

from __future__ import annotations
from pathlib import Path
from .fragment import FragmentRecord


class FragmentStore:
    """Persists and retrieves FragmentRecord objects on disk.

    Attributes:
        base_dir (Path): Root directory for all fragment storage.
    """

    def __init__(self, base_dir: str | Path) -> None:
        """Initialise the store, creating base_dir if it does not exist.

        Args:
            base_dir: Path to the root storage directory.
        """
        # TODO: Store base_dir as a Path, call mkdir(parents=True, exist_ok=True).
        ...

    def put(self, record: FragmentRecord) -> None:
        """Persist a fragment record to disk.

        Writes atomically by serialising to a temp file then renaming.

        Args:
            record: The FragmentRecord to store.

        Raises:
            IOError: If the file cannot be written.
        """
        # TODO: 1. Build the directory path: base_dir / block_id.
        # TODO: 2. mkdir(parents=True, exist_ok=True).
        # TODO: 3. Write record.to_dict() as JSON to a temp file.
        # TODO: 4. Atomically rename temp file to final path.
        ...

    def get(self, block_id: str, index: int) -> FragmentRecord:
        """Retrieve a single fragment by (block_id, index).

        Args:
            block_id: Identifier for the data block.
            index:    Fragment index within the block.

        Returns:
            The deserialized FragmentRecord.

        Raises:
            FragmentNotFoundError: If no fragment is stored for this key.
        """
        # TODO: Read JSON file, return FragmentRecord.from_dict().
        ...

    def delete(self, block_id: str, index: int) -> None:
        """Remove a stored fragment.

        Args:
            block_id: Identifier for the data block.
            index:    Fragment index.

        Raises:
            FragmentNotFoundError: If the fragment does not exist.
        """
        # TODO: Unlink the fragment file.
        # TODO: Remove block directory if now empty.
        ...

    def list_fragments(self, block_id: str) -> list[FragmentRecord]:
        """Return all stored fragments for a given block.

        Args:
            block_id: Identifier for the data block.

        Returns:
            A list of FragmentRecord objects, sorted by index.
            Empty list if no fragments are stored for this block.
        """
        # TODO: Glob all fragment_*.json files under base_dir/block_id/.
        # TODO: Deserialize and return sorted by record.index.
        ...

    def has(self, block_id: str, index: int) -> bool:
        """Check whether a specific fragment is stored.

        Args:
            block_id: Identifier for the data block.
            index:    Fragment index.

        Returns:
            True if the fragment file exists, False otherwise.
        """
        # TODO: Return _fragment_path(block_id, index).exists()
        ...

    def _fragment_path(self, block_id: str, index: int) -> Path:
        """Compute the file path for a fragment.

        Args:
            block_id: Identifier for the data block.
            index:    Fragment index.

        Returns:
            A Path object for the fragment's JSON file.
        """
        # TODO: return self.base_dir / block_id / f"fragment_{index}.json"
        ...


class FragmentNotFoundError(KeyError):
    """Raised when a requested fragment does not exist in the store."""
