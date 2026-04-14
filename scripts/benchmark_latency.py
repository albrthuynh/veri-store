from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.network.client import RetrievalError, ServerAddress, VeriStoreClient


# Usage:
# 1) Start the 5 local servers in another terminal:
#    VERI_STORE_TOKEN=test-token bash scripts/run_servers.sh
#
# 2) Run the end-to-end latency benchmark:
#    VERI_STORE_TOKEN=test-token ./.venv/bin/python3.14 scripts/benchmark_latency.py --objects 20 --size-bytes 65536


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", type=int, default=20)
    parser.add_argument("--size-bytes", type=int, default=65536)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--start-port", type=int, default=5001)
    parser.add_argument("--servers", type=int, default=5)
    parser.add_argument("--m", type=int, default=3)
    parser.add_argument("--token", type=str, default=os.environ.get("VERI_STORE_TOKEN", ""))
    parser.add_argument("--prefix", type=str, default="latency")
    return parser.parse_args()


def build_servers(host: str, start_port: int, count: int) -> list[ServerAddress]:
    return [
        ServerAddress(server_id=i + 1, host=host, port=start_port + i)
        for i in range(count)
    ]


def percentile(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]

    # Linear interpolation keeps percentiles stable for small benchmark sizes.
    rank = (p / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * weight


def summarize_ms(samples: list[float]) -> str:
    if not samples:
        return "count=0 avg_ms=0.00 p50_ms=0.00 p95_ms=0.00 min_ms=0.00 max_ms=0.00"

    avg_ms = (sum(samples) / len(samples)) * 1000.0
    p50_ms = percentile(samples, 50.0) * 1000.0
    p95_ms = percentile(samples, 95.0) * 1000.0
    min_ms = min(samples) * 1000.0
    max_ms = max(samples) * 1000.0
    return (
        f"count={len(samples)} avg_ms={avg_ms:.2f} p50_ms={p50_ms:.2f} "
        f"p95_ms={p95_ms:.2f} min_ms={min_ms:.2f} max_ms={max_ms:.2f}"
    )


def main() -> int:
    args = parse_args()
    if args.objects <= 0:
        raise ValueError("--objects must be > 0")
    if args.size_bytes <= 0:
        raise ValueError("--size-bytes must be > 0")
    if not args.token:
        raise ValueError("Missing token; pass --token or set VERI_STORE_TOKEN")

    client = VeriStoreClient(
        servers=build_servers(args.host, args.start_port, args.servers),
        m=args.m,
        token=args.token,
        timeout=10.0,
    )
    payload = secrets.token_bytes(args.size_bytes)

    stored_keys: list[str] = []
    put_latencies: list[float] = []
    get_latencies: list[float] = []
    put_failures = 0
    get_failures = 0

    for i in range(args.objects):
        key = f"{args.prefix}_{int(time.time() * 1000)}_{i}"

        put_start = time.perf_counter()
        try:
            client.put(key, payload)
            put_latencies.append(time.perf_counter() - put_start)
            stored_keys.append(key)
        except Exception:
            put_failures += 1

    for key in stored_keys:
        get_start = time.perf_counter()
        try:
            data = client.get(key)
            if data == payload:
                get_latencies.append(time.perf_counter() - get_start)
            else:
                get_failures += 1
        except RetrievalError:
            get_failures += 1

    for key in stored_keys:
        client.delete(key)

    print(
        f"objects={args.objects} size_bytes={args.size_bytes} "
        f"put_success={len(put_latencies)} put_failures={put_failures} "
        f"get_success={len(get_latencies)} get_failures={get_failures}"
    )
    print(f"put_latency: {summarize_ms(put_latencies)}")
    print(f"get_latency: {summarize_ms(get_latencies)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
