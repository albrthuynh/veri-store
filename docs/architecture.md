# veri-store Architecture

## Overview

veri-store is a distributed object storage system that combines **Reed-Solomon
erasure coding** with **homomorphic fingerprint verification** to provide
both fault tolerance and Byzantine integrity guarantees.

Reference paper: *Verifying Distributed Erasure-Coded Data*,
Hendricks, Ganger, and Reiter, PODC 2007.

---

## Coding Parameters

| Symbol | Meaning                                  | Default |
|--------|------------------------------------------|---------|
| `m`    | Reconstruction threshold (data fragments)| 3       |
| `n`    | Total fragments (`n = m + 2f`)           | 5       |
| `f`    | Fault tolerance (`f = (n - m) / 2`)      | 1       |

With `m=3, n=5, f=1`:
- Any **3** fragments reconstruct the full block.
- The system tolerates **1** Byzantine fault (corrupt/lying server).
- The system tolerates up to **2** crash faults (unavailable servers).

---

## Module Dependency Graph

```
examples/  ──►  network/client.py
                    │
                    ▼
            network/server.py
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   erasure/encoder        verification/verifier
   erasure/decoder              │
          │               verification/cross_checksum
          ▼                     │
   erasure/matrix         verification/oracle
                                │
                         fingerprint/fingerprint
                                │
                     ┌──────────┴──────────┐
                     ▼                     ▼
            fingerprint/polynomial  fingerprint/field
```

Each layer depends only on layers below it; there are **no circular imports**.

---

## Data Flow: PUT (Dispersal)

```
Client                         Server_i (i = 0..n-1)
  │
  │  data = b"..."
  │
  ├─► erasure.encode(data, n, m)
  │         │
  │         └─► [Fragment_0, Fragment_1, ..., Fragment_{n-1}]
  │
  ├─► FingerprintedCrossChecksum.generate(fragments)
  │         │
  │         ├─► h_i = SHA-256(d_i)  for each i
  │         ├─► r = Oracle(h_0 || ... || h_{n-1})
  │         └─► phi_j = fp(r, d_j)  for j < m
  │
  ├─► HTTP PUT /fragments/{block_id}/{i}   ──►  Verifier.check(i, d_i, fpcc)
  │         body: { fragment_data, fpcc_json, ... }    │
  │                                                     ▼
  │                                              FragmentStore.put(record)
  │
  └─► Return block_id to caller
```

---

## Data Flow: GET (Retrieval)

```
Client                         Server_i
  │
  ├─► HTTP GET /fragments/{block_id}/{i}  for each i (parallel)
  │         │
  │         └─► FragmentStore.get(block_id, i)
  │                     └─► GetFragmentResponse { fragment_data, fpcc_json }
  │
  ├─► For each response: Verifier.check(i, decoded_data, fpcc)
  │         ├─► CONSISTENT  → accept fragment
  │         └─► any failure → discard, try next server
  │
  ├─► Collect first m verified fragments
  │
  └─► erasure.decode(verified_fragments)  →  original data
```

---

## Security Model

### Threat: Byzantine Server
A Byzantine server may return any bytes it chooses for a stored fragment.

**Detection mechanism:**
1. **Hash check**: `h_i' = SHA-256(returned data)` must match `fpcc.hashes[i]`.
2. **Fingerprint check** (for indices `i < m`): `fp(r, returned data)` must
   match `fpcc.fingerprints[i]`.

A corrupt fragment passes both checks only if:
- A hash collision occurs (probability ≤ 2^{-256} with SHA-256), **or**
- The fingerprint check collides (probability ≤ 1/q = 1/256 per check).

By Theorem 3.4, a server returning any inconsistent fragment is detected
except with probability **at most 1/256**.

### Threat: Crash Fault
A server may be unreachable.  The client simply retries other servers and
decodes from any `m` responding servers.

### Threat: Replay / Substitution
A server holding old or wrong-block fragments is caught by the hash check,
since the fpcc hashes are block-specific.

---

## File Layout

```
veri-store/
├── src/
│   ├── fingerprint/      GF(2^8) arithmetic + division fingerprint
│   ├── erasure/          Reed-Solomon encode / decode
│   ├── storage/          On-disk fragment store + metadata
│   ├── verification/     fpcc generation + server-side verifier
│   └── network/          FastAPI server + httpx client
├── tests/                Mirrors src/ structure
├── docs/                 This file + api.md
└── examples/             Runnable demo scripts
```

---

## Key Data Structures

### `Fragment` (erasure.encoder)
```
index           : int    — fragment index in [0, n)
data            : bytes  — raw coded bytes (length = ceil(len(data)/m))
block_id        : str    — SHA-256 hex digest of original data
total_n         : int    — n
threshold_m     : int    — m
original_length : int    — len(original data) before padding
```

### `FingerprintedCrossChecksum` (verification.cross_checksum)
```
hashes          : list[bytes]   — SHA-256(d_i) for i in [0,n)
fingerprints    : list[GF256]   — fp(r, d_j) for j in [0,m)
r               : GF256         — Oracle(hashes)
n               : int
m               : int
```
