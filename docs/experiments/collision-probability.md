# Summary:
The fingerprint, random oracle, and hash collisions are summarized in the below table:
|              | Samples | Collisions | Rate       | Expected   |
|--------------|--------:|-----------:|-----------:|-----------:|
| Fingerprints | 500,000 |      1,979 | 0.00395800 | 0.00390625 |
| RandomOracle | 500,000 |      1,971 | 0.00394200 | 0.00392157 |
| SHA-256      | 200,000 |          0 | 0.00000000 | 0.00000000 | 

**Note**: SHA-256 tests are meant more as a sanity check, hence the smaller sample sizes.

## Recreation
To run the expermiment, from the repository root, run:
```pwsh
python .\scripts\estimate_collision_probability.py --fingerprint-trials 500000 --oracle-trials 500000 --sha-samples 200000
```

## Results:
=== Collision Probability Experiment ===
fragment_bytes=64
hash_vector_length=5

Fingerprint collisions
  trials:       500000
  collisions:   1979
  empirical:    0.00395800
  expected:     0.00390625
  abs_error:    0.00005175
  std_error:    0.00008880

RandomOracle output collisions
  trials:       500000
  collisions:   1971
  empirical:    0.00394200
  expected:     0.00392157
  abs_error:    0.00002043
  std_error:    0.00008862

SHA-256 duplicate search
  samples:      200000
  duplicates:   0
  unique:       200000

Notes:
  - Fingerprint collisions are expected to occur with probability about 1/256.
  - RandomOracle.derive() outputs one of 255 nonzero GF(2^8) values, so pairwise output collisions should be about 1/255.
  - SHA-256 duplicates are expected to be 0 at these sample sizes; this is only a sanity check, not evidence of practical collision resistance.