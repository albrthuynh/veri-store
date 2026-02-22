## Erasure Coding Fundamentals

- Erasure coding is a method used to protect data in distributed storage systems
- Splits data into smaller pieces and adds extra pieces called ==parity==
- Pieces are scattered across various storage nodes for redundancy
- If some pieces are missing or damaged, the original data can still be reconstructed

- We need to decide how many data and parity fragments to make
- Provides strong fault tolerance while keeping storage use efficient

## Library Chosen

For this project we will use the reedsolo library.
The main reason for this is that the functions it provides makes it easy for us to 
really focus on the system design aspect

``` python
encode(data: bytes) -> List[bytes] (length 5),

decode(fragments: Dict[int, bytes]) -> bytes (any 3 indices).
```

This makes us really focus on fpcc, HTTP flows, crash/Byzantine scanerios, and 
performance graphs.

### Some pros
- Focused Reed–Solomon codec: designed to turn byte strings into RS codewords and back.
- Less general math, more “just make RS work”; easier to drop in for a quick encode/decode API.
- Really good for this use case since it is a final project, built to demonstrate simple
erasure coding procedure

### Some cons
- Not as great for understanding the math
- Not as fast as other libraries like galois

---

## High Level Architecture

```
                ┌───────────────────────────┐
                │           Client          │
                │  - PUT/GET/DELETE API     │
                │  - RS encode/decode (k=3) │
                │  - fpcc build/verify      │
                └───────────┬───────────────┘
                            │ HTTP (localhost)
     ┌──────────────────────┼─────────────────────────┐
     │                      │                         │
┌────▼─────┐          ┌────▼─────┐              ┌────▼─────┐
│ Shard S1 │          │ Shard S2 │     ...      │ Shard S5 │
│ port 5001│          │ port 5002│              │ port 5005│
│ stores:  │          │ stores:  │              │ stores:  │
│ - frag i │          │ - frag i │              │ - frag i │
│ - fpcc   │          │ - fpcc   │              │ - fpcc   │
│ - meta   │          │ - meta   │              │ - meta   │
└──────────┘          └──────────┘              └──────────┘
```

What each shard server stores per object version:
- fragment_i (the shard’s fragment, i ∈ {1..5})
- fpcc (fingerprinted cross-checksum: cc[1..n] hashes + fp[1..m] fingerprints) 
- minimal metadata: object key, version, size, timestamp

### Request flows (AVID-FP style)

**1) PUT (write / dispersal)**  
Goal: send fragment_i + fpcc to each server; each server verifies and stores.

- Client reads bytes → (optional) stripes → RS encode (k=3, n=5).
- Client hashes each fragment to get cc[1..5], sets r = H(cc[1]||…||cc[5]), and builds fingerprints fp[1..3] for the first k data fragments.
- Client sends to each shard Si: object_key, version, fragment_i, fpcc.
- Each server verifies fragment vs fpcc (hash + homomorphic fingerprint check), stores (fragment_i, fpcc, meta), responds ACK(stored=true).

*Success:* For crash tolerance, wait for 3 acks (any 3 fragments suffice to reconstruct). For extra confidence in a Byzantine demo, wait for ≥4 acks; GET will verify anyway. Treat every PUT as versioned (monotonic version or content hash) for idempotency.

**2) GET (read / retrieval)**  
Goal: agree on one fpcc, then collect 3 fragments consistent with it.

- Client queries all servers: GET /objects/{key}/latest.
- Each server returns its stored fpcc (and optionally its fragment).
- Client picks a “winner” fpcc by majority (or “first fpcc that appears ≥2 times” in a small setup).
- Client gathers fragments until it has 3 that match that fpcc: check hash(fragment_i) == cc[i] and the fingerprint relation. RS decode → return bytes.

Even if a server returns a bad fragment, it fails the fpcc check and is discarded.

**3) DELETE**  
- **Tombstone:** client writes a tombstone manifest (special fpcc record) to all servers. Servers mark “deleted” so GET returns 404; fragments can be garbage-collected later. For a class project, tombstone is usually cleaner and consistent under failures.

### Fault model (3-of-5 demo)

- **n=5, k=3:** up to 2 missing shards → still decode (need any 3).
- **Byzantine:** fpcc (hash + homomorphic fingerprint) lets us detect and reject bad fragments. In practice: tolerate 1 malicious shard as long as we can get 3 consistent fragments from honest shards. With n=5, m=3 this is the f=1 regime (one Byzantine shard).

### Minimal API surface

**Shard server:**  
`POST /objects/{key}/{version}/fragment/{i}` (body: fragment_bytes, fpcc) → stored;  
`GET /objects/{key}/{version}/status` → has_fragment, has_fpcc;  
`GET /objects/{key}/{version}/fragment/{i}` → fragment_bytes, fpcc;  
`DELETE /objects/{key}/{version}` → deleted or tombstoned.

**Client CLI:**  
`put <file> --key <k>`, `get --key <k> --out <file>`, `delete --key <k>`.

### Where homomorphic fingerprinting sits

Server on PUT: “Is my fragment consistent with this fpcc for my index i?” Client on GET: same check, then decode. Clean separation.