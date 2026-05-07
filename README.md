This is a project made by Albert and Mac for CS588

## Important Values:
- m-of-n: A block of data B can be split into n fragments in such a way that it can be rebuilt with only m of the fragments.
- f: The number of fragments which can be unavailable for the system to still work (fault tolerance)
- n: total number of fragments
- m: minimum number of fragments needed to reconstruct the data block
- m $\geq$ f + 1
- n = m + 2f



## Libraries to use:
- [hashlib](https://docs.python.org/3/library/hashlib.html) - for running hash algorithms (including SHA256) in Python
- [cryptography](https://pypi.org/project/cryptography/) - various cryptographic primitives for Python
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
│   ├── reconstruct_from_2_crashes.py     # Reconstruct after 2 crashed servers
│   ├── fail_with_3_crashes.py            # Fail closed after 3 crashed servers
│   ├── byzantine_detection_demo.py       # Reconstruct with 1 Byzantine server
│   └── fail_with_2_byzantine_nodes.py    # Fail closed with 2 Byzantine servers
├── pyproject.toml
└── requirements.txt
```

## Reconstruction Demos

Each script starts the needed local veri-store servers automatically, runs its scenario, prints whether the expected behavior occurred, and stops the servers before exiting.

- `examples/reconstruct_from_2_crashes.py`: Shows that the original object can be reconstructed when 2 of 5 servers crash.
- `examples/fail_with_3_crashes.py`: Shows that reconstruction fails closed when 3 of 5 servers crash.
- `examples/byzantine_detection_demo.py`: Shows that one Byzantine server returning corrupt fragment bytes is detected and the original object is still reconstructed.
- `examples/fail_with_2_byzantine_nodes.py`: Shows that reconstruction fails closed when two Byzantine servers leave too few verified fragments.

Install dependencies once before running the demos:

```bash
python3 -m pip install -r requirements.txt
```

Run a demo with whichever Python environment you use:

```bash
# If you use a local venv directory:
venv/bin/python examples/reconstruct_from_2_crashes.py

# If your environment is already activated:
python examples/reconstruct_from_2_crashes.py

# On Windows PowerShell with a venv directory:
.\venv\Scripts\python.exe .\examples\reconstruct_from_2_crashes.py

# If you don't use a venv:
python3 examples/reconstruct_from_2_crashes.py
python3 examples/fail_with_3_crashes.py
python3 examples/byzantine_detection_demo.py
python3 examples/fail_with_2_byzantine_nodes.py
```

Replace `examples/reconstruct_from_2_crashes.py` with any of the other three demo paths to run that scenario.
