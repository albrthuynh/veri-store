"""
basic_store_retrieve.py -- Minimal end-to-end demo: PUT then GET.

This demo starts 5 local servers automatically if they are not already
running on ports 5001..5005.

Usage:
    VERI_STORE_TOKEN=test-token python examples/basic_store_retrieve.py

Expected output:
    [SETUP]  Starting server 1 on port 5001
    ...
    [SETUP]  All 5 servers healthy.
    [PUT]    Dispersing 'hello_world_...' (13 bytes) to 5 servers...
    [PUT]    Stored block: hello_world_...
    [GET]    Retrieving 'hello_world_...' ...
    [GET]    Reconstructed: b'Hello, world!'
    [OK]     Retrieved data matches original.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.network.client import ServerAddress, VeriStoreClient


DEFAULT_SERVERS = [
    ServerAddress(server_id=i + 1, host="127.0.0.1", port=5001 + i)
    for i in range(5)
]


def require_token() -> str:
    token = os.environ.get("VERI_STORE_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "Missing VERI_STORE_TOKEN. Start the servers with a shared token and "
            "run this script with the same environment variable."
        )
    return token


def start_servers(token: str) -> list[subprocess.Popen]:
    procs: list[subprocess.Popen] = []
    data_dir = ROOT / "data"

    for server in DEFAULT_SERVERS:
        env = os.environ.copy()
        env["SERVER_ID"] = str(server.server_id)
        env["DATA_DIR"] = str(data_dir)
        env["VERI_STORE_TOKEN"] = token
        env.pop("BYZANTINE_INDICES", None)

        print(f"[SETUP]  Starting server {server.server_id} on port {server.port}")
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.network.server:app",
                "--host",
                server.host,
                "--port",
                str(server.port),
                "--log-level",
                "warning",
            ],
            env=env,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append(proc)

    return procs


def stop_servers(procs: list[subprocess.Popen]) -> None:
    for proc in procs:
        proc.terminate()
    for proc in procs:
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def wait_for_servers(client: VeriStoreClient, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        health = client.health_check()
        if health and all(health.values()):
            print(f"[SETUP]  All {len(health)} servers healthy.")
            return
        time.sleep(0.3)
    raise RuntimeError("Servers did not become healthy within timeout.")


def main() -> None:
    token = require_token()
    client = VeriStoreClient(servers=DEFAULT_SERVERS, m=3, token=token, timeout=5.0)
    spawned_procs: list[subprocess.Popen] = []

    try:
        health = client.health_check()
        if not health or not all(health.values()):
            spawned_procs = start_servers(token)

        wait_for_servers(client)

        data = b"Hello, world!"
        key = f"hello_world_{int(time.time())}"

        print(f"[PUT]    Dispersing '{key}' ({len(data)} bytes) to 5 servers...")
        block_id = client.put(key, data)
        print(f"[PUT]    Stored block: {block_id}")

        print(f"[GET]    Retrieving '{key}' ...")
        retrieved = client.get(key)
        print(f"[GET]    Reconstructed: {retrieved!r}")

        assert retrieved == data, "Retrieved data does not match original!"
        print("[OK]     Retrieved data matches original.")

        client.delete(key)
        print("[DELETE] Cleanup request sent.")
    finally:
        if spawned_procs:
            stop_servers(spawned_procs)
            print("[SETUP]  Servers stopped.")


if __name__ == "__main__":
    main()
