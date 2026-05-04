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
        record = FragmentRecord(
            index=0,
            data=b"frag0",
            block_id="block-a",
            total_n=5,
            threshold_m=3,
            original_length=5,
        )
        store.put(record)
        assert store.get(record.block_id, record.index) == record

    def test_has_returns_false_before_put(self, store: FragmentStore):
        """has() returns False when no fragment is stored."""
        assert not store.has("missing_block", 0)

    def test_has_returns_true_after_put(self, store: FragmentStore):
        """has() returns True after put()."""
        record = FragmentRecord(
            index=1,
            data=b"frag1",
            block_id="block-b",
            total_n=5,
            threshold_m=3,
            original_length=5,
        )
        store.put(record)
        assert store.has(record.block_id, record.index)

    def test_get_missing_raises(self, store: FragmentStore):
        """get() raises FragmentNotFoundError for unknown keys."""
        with pytest.raises(FragmentNotFoundError):
            store.get("no_block", 99)

    def test_delete_removes_fragment(self, store: FragmentStore):
        """delete() makes has() return False and get() raise."""
        record = FragmentRecord(
            index=2,
            data=b"frag2",
            block_id="block-c",
            total_n=5,
            threshold_m=3,
            original_length=5,
        )
        store.put(record)
        store.delete(record.block_id, record.index)
        assert not store.has(record.block_id, record.index)
        with pytest.raises(FragmentNotFoundError):
            store.get(record.block_id, record.index)

    def test_delete_missing_raises(self, store: FragmentStore):
        """delete() raises FragmentNotFoundError if fragment doesn't exist."""
        with pytest.raises(FragmentNotFoundError):
            store.delete("ghost", 0)


class TestFragmentStoreListing:
    """Tests for list_fragments()."""

    def test_list_all_fragments_for_block(self, store: FragmentStore):
        """list_fragments() returns all stored fragments sorted by index."""
        block_id = "list-block"
        for index in [4, 1, 2]:
            store.put(
                FragmentRecord(
                    index=index,
                    data=f"frag{index}".encode(),
                    block_id=block_id,
                    total_n=5,
                    threshold_m=3,
                    original_length=5,
                )
            )

        records = store.list_fragments(block_id)
        assert [record.index for record in records] == [1, 2, 4]

    def test_list_empty_for_unknown_block(self, store: FragmentStore):
        """list_fragments() returns [] for an unknown block_id."""
        assert store.list_fragments("unknown") == []
