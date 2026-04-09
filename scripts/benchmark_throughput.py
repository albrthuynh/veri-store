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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--objects", type=int, default=20)
    parser.add_argument("--size-bytes", type=int, default=65536)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--start-port", type=int, default=5001)
    parser.add_argument("--servers", type=int, default=5)
    parser.add_argument("--m", type=int, default=3)
    parser.add_argument("--token", type=str, default=os.environ.get("VERI_STORE_TOKEN", ""))
    parser.add_argument("--prefix", type=str, default="throughput")
    return parser.parse_args()


def build_servers(host: str, start_port: int, count: int) -> list[ServerAddress]:
    servers: list[ServerAddress] = []
    for i in range(count):
        servers.append(ServerAddress(server_id=i + 1, host=host, port=start_port + i))
    return servers


def main() -> int:
    args = parse_args()
    if args.objects <= 0:
        raise ValueError("--objects must be > 0")
    if args.size_bytes <= 0:
        raise ValueError("--size-bytes must be > 0")
    if not args.token:
        raise ValueError("Missing token; pass --token or set VERI_STORE_TOKEN")

    servers = build_servers(args.host, args.start_port, args.servers)
    client = VeriStoreClient(servers=servers, m=args.m, token=args.token, timeout=10.0)
    payload = secrets.token_bytes(args.size_bytes)

    stored_keys: list[str] = []
    put_ok = 0
    get_ok = 0

    put_start = time.perf_counter()
    for i in range(args.objects):
        key = f"{args.prefix}_{int(time.time() * 1000)}_{i}"
        try:
            client.put(key, payload)
            stored_keys.append(key)
            put_ok += 1
        except Exception:
            pass
    put_elapsed = time.perf_counter() - put_start

    get_start = time.perf_counter()
    for key in stored_keys:
        try:
            data = client.get(key)
            if data == payload:
                get_ok += 1
        except RetrievalError:
            pass
    get_elapsed = time.perf_counter() - get_start

    for key in stored_keys:
        client.delete(key)

    put_throughput = put_ok / put_elapsed if put_elapsed > 0 else 0.0
    get_throughput = get_ok / get_elapsed if get_elapsed > 0 else 0.0
    total_ops = put_ok + get_ok
    total_elapsed = put_elapsed + get_elapsed
    total_throughput = total_ops / total_elapsed if total_elapsed > 0 else 0.0

    print(f"objects={args.objects} size_bytes={args.size_bytes} put_ok={put_ok} get_ok={get_ok}")
    print(f"put_seconds={put_elapsed:.4f} put_objects_per_sec={put_throughput:.2f}")
    print(f"get_seconds={get_elapsed:.4f} get_objects_per_sec={get_throughput:.2f}")
    print(f"total_seconds={total_elapsed:.4f} total_ops_per_sec={total_throughput:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
