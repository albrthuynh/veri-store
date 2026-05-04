# Bandwidth Benchmark Experiment
## Command from repo root:
```pwsh
python scripts\benchmark_bandwidth.py --sizes 256 4096 --csv .tmp\bandwidth_sample.csv --md .tmp\bandwidth_sample.md
```

## Bandwidth Benchmark Results

| label | object_size_bytes | client_to_servers_bytes | servers_to_client_bytes | total_bytes | overhead_vs_object | note |
| --- | --- | --- | --- | --- | --- | --- |
| veri-store-put | 256 | 3160 | 660 | 3820 | 14.921875 | Actual PUT fan-out to n=5 servers. |
| veri-store-get-current | 256 | 0 | 3525 | 3525 | 13.76953125 | Current client requests and parses all 5 fragment responses. |
| veri-store-get-minimum | 256 | 0 | 2115 | 2115 | 8.26171875 | Lower bound if GET stopped after the first m=3 valid fragments. |
| replication-3x-put | 256 | 1131 | 159 | 1290 | 5.0390625 | Baseline assumes full-object PUT to 3 replicas using the same JSON+base64 transport style. |
| replication-3x-get | 256 | 0 | 424 | 424 | 1.65625 | Healthy-case GET contacting 1 replica(s); replication factor is 3. |
| replication-5x-put | 256 | 1885 | 265 | 2150 | 8.3984375 | Baseline assumes full-object PUT to 5 replicas using the same JSON+base64 transport style. |
| replication-5x-get | 256 | 0 | 424 | 424 | 1.65625 | Healthy-case GET contacting 1 replica(s); replication factor is 5. |
| veri-store-put | 4096 | 11690 | 660 | 12350 | 3.01513671875 | Actual PUT fan-out to n=5 servers. |
| veri-store-get-current | 4096 | 0 | 12055 | 12055 | 2.943115234375 | Current client requests and parses all 5 fragment responses. |
| veri-store-get-minimum | 4096 | 0 | 7233 | 7233 | 1.765869140625 | Lower bound if GET stopped after the first m=3 valid fragments. |
| replication-3x-put | 4096 | 16494 | 159 | 16653 | 4.065673828125 | Baseline assumes full-object PUT to 3 replicas using the same JSON+base64 transport style. |
| replication-3x-get | 4096 | 0 | 5545 | 5545 | 1.353759765625 | Healthy-case GET contacting 1 replica(s); replication factor is 3. |
| replication-5x-put | 4096 | 27490 | 265 | 27755 | 6.776123046875 | Baseline assumes full-object PUT to 5 replicas using the same JSON+base64 transport style. |
| replication-5x-get | 4096 | 0 | 5545 | 5545 | 1.353759765625 | Healthy-case GET contacting 1 replica(s); replication factor is 5. |

## Discussion
The results show that veri-store's bandwidth overhead is highly sensitive to object size. For the 256-byte object, veri-store performs worse than both 3x and 5x replication on both `PUT` and `GET`: the fixed cost of sending base64-encoded fragment data plus the full `fpcc_json` to each server dominates the transfer. In other words, for very small objects, the protocol metadata overwhelms any storage-efficiency benefit from erasure coding.

At 4kb, the expected erasure-coding advantage begins to appear on writes. Veri-store's `PUT` cost is 12,350 bytes (~12kb), which is lower than both 3x replication (16,653 bytes, ~16.26kb) and 5x replication (27,755 bytes, ~27.1kb). However, reads remain relatively expensive in the current implementation because the client requests all five fragment responses and then verifies them locally; even the lower-bound estimate that stops after three valid fragments still exceeds the replication baseline. Overall, these measurements suggest that veri-store is already competitive for medium-size writes, but retrieval bandwidth would improve if the client avoided downloading unnecessary fragment responses or if verification metadata were made more compact.
