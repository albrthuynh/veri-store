This is a project made by Albert and Mac for CS588

## Important Values:
- m-of-n: A block of data B can be split into n fragments in such a way that it can be rebuilt with only m of the fragments.
- f: The number of fragments which can be unavailable for the system to still work (fault tolerance)
- m $\geq$ f + 1
- n = m + 2f

## Libraries to use:
- [hashlib](https://docs.python.org/3/library/hashlib.html) - for running hash algorithms (including SHA256) in Python
- [cryptography](https://pypi.org/project/cryptography/) - various cryptographic primitives for Python
- [galois](https://pypi.org/project/galois/) - finite field arithmetic
- [numpy](https://numpy.org/) - efficient array operations for polynomial manipulation

## Project Structure

```
veri-store/
├── src/
│   ├── fingerprint/          # Homomorphic fingerprinting over GF(2^8)
│   │   ├── field.py          #   GF256 arithmetic (add, mul, inverse)
│   │   ├── polynomial.py     #   Polynomial evaluation and division
│   │   └── fingerprint.py    #   fp(r, data) and random oracle
│   ├── erasure/              # Reed-Solomon erasure coding (m-of-n)
│   │   ├── matrix.py         #   Cauchy encoding matrix over GF(2^8)
│   │   ├── encoder.py        #   encode(data, n, m) → n Fragment objects
│   │   └── decoder.py        #   decode(fragments) → original bytes
│   ├── storage/              # Server-side fragment persistence
│   │   ├── fragment.py       #   FragmentRecord model + VerificationStatus
│   │   ├── store.py          #   Disk-backed CRUD store
│   │   └── metadata.py       #   Per-object metadata (fpcc reference, indices)
│   ├── verification/         # Fingerprinted cross-checksum (fpcc) protocol
│   │   ├── oracle.py         #   Random oracle: SHA-256(hashes) → GF256 point
│   │   ├── cross_checksum.py #   FingerprintedCrossChecksum generation + serde
│   │   └── verifier.py       #   Server-side hash + fingerprint consistency check
│   └── network/              # HTTP dispersal / retrieval protocol
│       ├── protocol.py       #   Pydantic request/response models
│       ├── server.py         #   FastAPI server (PUT, GET, DELETE, /health)
│       └── client.py         #   VeriStoreClient (put, get, delete)
├── tests/                    # Unit tests mirroring src/ structure
│   ├── fingerprint/
│   ├── erasure/
│   ├── storage/
│   ├── verification/
│   └── network/
├── docs/
│   ├── architecture.md       # Data flow diagrams, security model
│   └── api.md                # REST endpoint reference
├── examples/
│   ├── basic_store_retrieve.py      # End-to-end PUT → GET demo
│   ├── fault_tolerance_demo.py      # Survive 2-server crash
│   └── byzantine_detection_demo.py  # Detect corrupt fragment
├── pyproject.toml
└── requirements.txt
```