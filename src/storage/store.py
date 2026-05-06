from __future__ import annotations
from pathlib import Path
import json
import os
import tempfile
import uuid

from .fragment import FragmentRecord


class FragmentStore:
    """Persists fragment records on disk."""

    def __init__(self, base_dir: str | Path) -> None:
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
        block_dir = self.base_dir / record.block_id
        block_dir.mkdir(parents=True, exist_ok=True)

        final_path = self._fragment_path(record.block_id, record.index)

        payload = record.to_dict()
        data = json.dumps(payload, sort_keys=True).encode("utf-8")

        tmp_path: Path | None = None
        try:
            # Give each writer its own temp file so concurrent writes to the same fragment do not contend on a shared *.tmp pathname.
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=block_dir,
                prefix=f"{final_path.name}.{uuid.uuid4().hex}.",
                suffix=".tmp",
                delete=False,
            ) as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
                tmp_path = Path(f.name)

            os.replace(tmp_path, final_path)
        finally:
            if tmp_path is not None:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink()
                except OSError:
                    pass

        self._index.setdefault(record.block_id, set()).add(record.index)

    def get(self, block_id: str, index: int) -> FragmentRecord:
        path = self._fragment_path(block_id, index)
        if not path.exists():
            raise FragmentNotFoundError((block_id, index))
        try:
            raw = path.read_text(encoding="utf-8")
            return FragmentRecord.from_dict(json.loads(raw))
        except FileNotFoundError:
            raise FragmentNotFoundError((block_id, index))

    def delete(self, block_id: str, index: int) -> None:
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
        return self._fragment_path(block_id, index).exists()

    def _fragment_path(self, block_id: str, index: int) -> Path:
        return self.base_dir / block_id / f"fragment_{index}.json"

    def fragment_count(self) -> int:
        """Return the number of stored fragments (fast path)."""
        return sum(len(v) for v in self._index.values())

    def list_indices(self, block_id: str) -> list[int]:
        """Return stored indices for a block from in-memory state."""
        return sorted(self._index.get(block_id, set()))


class FragmentNotFoundError(KeyError):
    """Raised when a requested fragment does not exist in the store."""
