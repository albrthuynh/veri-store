# Verification Time Experiment
## Command from repo root:
```pwsh
python scripts\benchmark_verification_time.py --sizes 256 1024 4096 16384 65536 --repetitions 5000 --warmup 500 --csv .tmp\verification_time_sample.csv --md .tmp\verification_time_sample.md
```

## Verification Time Benchmark Results

| label | verification_path | object_size_bytes | fragment_size_bytes | fragment_index | repetitions | warmup | avg_us | p50_us | p95_us | min_us | max_us | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| verification-data-fragment | hash+fingerprint | 256 | 86 | 0 | 2000 | 200 | 67.65445 | 67.0 | 69.005 | 64.8 | 191.2 | Representative data fragment with index 0; indices < m perform both checks. |
| verification-parity-fragment | hash-only | 256 | 86 | 3 | 2000 | 200 | 0.9014500000000001 | 0.9 | 0.9 | 0.8 | 3.5 | Representative parity fragment with index 3; indices >= m skip the fingerprint check. |
| verification-data-fragment | hash+fingerprint | 4096 | 1366 | 0 | 2000 | 200 | 1032.5953 | 1021.3 | 1080.155 | 970.7 | 1896.4 | Representative data fragment with index 0; indices < m perform both checks. |
| verification-parity-fragment | hash-only | 4096 | 1366 | 3 | 2000 | 200 | 1.4163 | 1.4 | 1.5 | 1.3 | 5.9 | Representative parity fragment with index 3; indices >= m skip the fingerprint check. |

## Discussion
The results show a sharp difference between veri-store's two verification paths. For parity fragments, which perform only the SHA-256 hash check, per-fragment verification time stays extremely low: about 0.9 microseconds for 256-byte objects and about 1.4 microseconds for 4096-byte objects. In contrast, data fragments, which perform both the hash check and the GF(256) fingerprint check, are much more expensive: about 67.7 microseconds at 256 bytes and about 1032.6 microseconds at 4096 bytes.

This means verification cost is driven primarily by the fingerprint computation, and it grows with fragment size much more noticeably than the hash-only path. In practical terms, veri-store's integrity checking is asymmetric: parity-fragment verification is almost negligible, while data-fragment verification is the main computational cost during retrieval and auditing. Even so, the measured times are still on the order of microseconds to about 1 millisecond per fragment in this sample, which suggests the verification logic is likely practical for moderate object sizes but should still be treated as a real cost in performance discussions.
