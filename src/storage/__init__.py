"""
storage -- Local fragment storage and object metadata management.

Each storage server maintains a local on-disk store of the fragments it is
responsible for.  This package separates three concerns:

    fragment.py  -- The in-memory Fragment model (mirrors erasure.encoder.Fragment)
                    with server-side additions (receipt timestamp, verification status).
    store.py     -- Disk-backed key-value store: write/read/delete fragment files.
    metadata.py  -- Object-level metadata: which fragments exist, coding parameters,
                    and the associated fingerprinted cross-checksum (fpcc).

Public API:
    FragmentRecord   -- Server-side fragment model (from fragment.py)
    FragmentStore    -- Persistent storage backend (from store.py)
    ObjectMetadata   -- Per-object metadata record (from metadata.py)
"""

from .fragment import FragmentRecord
from .store import FragmentStore
from .metadata import ObjectMetadata
