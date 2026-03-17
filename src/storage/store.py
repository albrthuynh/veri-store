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
import json
import os

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
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, set[int]] = {}
        self._rebuild_index_from_disk()

    def _rebuild_index_from_disk(self) -> None:
        """Best-effort rebuild of the in-memory index by scanning base_dir."""
        self._index.clear()
        try:
            for p in self.base_dir.rglob("fragment_*.json"):
                if not p.is_file():
                    continue
                block_id = p.parent.name
                try:
                    idx = int(p.stem.removeprefix("fragment_"))
                except Exception:
                    continue
                self._index.setdefault(block_id, set()).add(idx)
        except OSError:
            pass

    def put(self, record: FragmentRecord) -> None:
        """Persist a fragment record to disk.

        Writes atomically by serialising to a temp file then renaming.

        Args:
            record: The FragmentRecord to store.

        Raises:
            IOError: If the file cannot be written.
        """
        block_dir = self.base_dir / record.block_id
        block_dir.mkdir(parents=True, exist_ok=True)

        final_path = self._fragment_path(record.block_id, record.index)
        tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")

        payload = record.to_dict()
        data = json.dumps(payload, sort_keys=True).encode("utf-8")

        try:
            with open(tmp_path, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, final_path)
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass

        self._index.setdefault(record.block_id, set()).add(record.index)

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
        path = self._fragment_path(block_id, index)
        if not path.exists():
            raise FragmentNotFoundError((block_id, index))
        try:
            raw = path.read_text(encoding="utf-8")
            return FragmentRecord.from_dict(json.loads(raw))
        except FileNotFoundError:
            raise FragmentNotFoundError((block_id, index))

    def delete(self, block_id: str, index: int) -> None:
        """Remove a stored fragment.

        Args:
            block_id: Identifier for the data block.
            index:    Fragment index.

        Raises:
            FragmentNotFoundError: If the fragment does not exist.
        """
        path = self._fragment_path(block_id, index)
        if not path.exists():
            raise FragmentNotFoundError((block_id, index))
        try:
            path.unlink()
        except FileNotFoundError:
            raise FragmentNotFoundError((block_id, index))

        indices = self._index.get(block_id)
        if indices is not None:
            indices.discard(index)
            if not indices:
                self._index.pop(block_id, None)

        block_dir = self.base_dir / block_id
        try:
            if block_dir.exists() and not any(block_dir.iterdir()):
                block_dir.rmdir()
        except OSError:
            pass

    def list_fragments(self, block_id: str) -> list[FragmentRecord]:
        """Return all stored fragments for a given block.

        Args:
            block_id: Identifier for the data block.

        Returns:
            A list of FragmentRecord objects, sorted by index.
            Empty list if no fragments are stored for this block.
        """
        block_dir = self.base_dir / block_id
        if not block_dir.exists():
            return []
        records: list[FragmentRecord] = []
        for p in block_dir.glob("fragment_*.json"):
            try:
                raw = p.read_text(encoding="utf-8")
                records.append(FragmentRecord.from_dict(json.loads(raw)))
            except Exception:
                continue
        records.sort(key=lambda r: r.index)
        return records

    def has(self, block_id: str, index: int) -> bool:
        """Check whether a specific fragment is stored.

        Args:
            block_id: Identifier for the data block.
            index:    Fragment index.

        Returns:
            True if the fragment file exists, False otherwise.
        """
        return self._fragment_path(block_id, index).exists()

    def _fragment_path(self, block_id: str, index: int) -> Path:
        """Compute the file path for a fragment.

        Args:
            block_id: Identifier for the data block.
            index:    Fragment index.

        Returns:
            A Path object for the fragment's JSON file.
        """
        return self.base_dir / block_id / f"fragment_{index}.json"

    def fragment_count(self) -> int:
        """Return the number of stored fragments (fast path)."""
        return sum(len(v) for v in self._index.values())

    def list_indices(self, block_id: str) -> list[int]:
        """Return stored indices for a block from in-memory state."""
        return sorted(self._index.get(block_id, set()))


class FragmentNotFoundError(KeyError):
    """Raised when a requested fragment does not exist in the store."""
