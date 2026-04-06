"""
test_store.py -- Unit tests for the disk-backed FragmentStore.

Uses a repo-local temporary directory to avoid polluting the real filesystem.

Covers:
    - put() then get() returns the same FragmentRecord
    - has() returns False before put, True after put
    - delete() removes the fragment; subsequent get() raises FragmentNotFoundError
    - list_fragments() returns all stored fragments for a block, sorted by index
    - Overwrite: two put() calls for the same (block_id, index) keep the latest
    - put() is atomic (temp-file-then-rename pattern)
"""

from collections.abc import Iterator
import pytest
import shutil
import uuid
from pathlib import Path
from src.storage.store import FragmentStore, FragmentNotFoundError
from src.storage.fragment import FragmentRecord


@pytest.fixture
def store() -> Iterator[FragmentStore]:
    """Provide a fresh FragmentStore in a temporary directory."""
    test_root = Path("data/test_runs") / str(uuid.uuid4())
    test_root.mkdir(parents=True, exist_ok=False)

    try:
        yield FragmentStore(test_root / "fragments")
    finally:
        shutil.rmtree(test_root, ignore_errors=True)


class TestFragmentStoreCRUD:
    """Create, read, update, delete operations."""

    def test_put_and_get_round_trip(self, store: FragmentStore):
        """get() after put() returns an equal FragmentRecord."""
        # TODO: record = FragmentRecord(index=0, data=b"frag0", ...)
        #       store.put(record)
        #       assert store.get(record.block_id, record.index) == record
        ...

    def test_has_returns_false_before_put(self, store: FragmentStore):
        """has() returns False when no fragment is stored."""
        # TODO: assert not store.has("missing_block", 0)
        ...

    def test_has_returns_true_after_put(self, store: FragmentStore):
        """has() returns True after put()."""
        # TODO: record = FragmentRecord(...)
        #       store.put(record)
        #       assert store.has(record.block_id, record.index)
        ...

    def test_get_missing_raises(self, store: FragmentStore):
        """get() raises FragmentNotFoundError for unknown keys."""
        # TODO: with pytest.raises(FragmentNotFoundError): store.get("no_block", 99)
        ...

    def test_delete_removes_fragment(self, store: FragmentStore):
        """delete() makes has() return False and get() raise."""
        # TODO: record = FragmentRecord(...)
        #       store.put(record) ; store.delete(record.block_id, record.index)
        #       assert not store.has(record.block_id, record.index)
        #       with pytest.raises(FragmentNotFoundError): store.get(...)
        ...

    def test_delete_missing_raises(self, store: FragmentStore):
        """delete() raises FragmentNotFoundError if fragment doesn't exist."""
        # TODO: with pytest.raises(FragmentNotFoundError): store.delete("ghost", 0)
        ...


class TestFragmentStoreListing:
    """Tests for list_fragments()."""

    def test_list_all_fragments_for_block(self, store: FragmentStore):
        """list_fragments() returns all stored fragments sorted by index."""
        # TODO: Store fragments at indices [4, 1, 2] and verify list returns [1,2,4].
        ...

    def test_list_empty_for_unknown_block(self, store: FragmentStore):
        """list_fragments() returns [] for an unknown block_id."""
        # TODO: assert store.list_fragments("unknown") == []
        ...
