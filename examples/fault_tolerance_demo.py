"""
fault_tolerance_demo.py -- Demonstrate crash fault tolerance.

Shows that the system can reconstruct a stored object even when f=1 servers
are unavailable (crash fault).  With n=5, m=3, f=1:
    - Store an object across all 5 servers.
    - Simulate 2 server crashes (stop responding).
    - Retrieve the object using only the 3 remaining servers.

Prerequisites:
    Start all 5 servers (see basic_store_retrieve.py header).

Usage:
    python examples/fault_tolerance_demo.py

Expected output:
    [PUT]   Stored 'fault_test' on all 5 servers.
    [CRASH] Simulating crash: servers 4 and 5 are now unreachable.
    [GET]   Attempting retrieval with only 3 of 5 servers...
    [GET]   Successfully reconstructed data from 3 fragments.
    [OK]    Fault tolerance confirmed: 2-server crash tolerated.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.network.client import RetrievalError, ServerAddress, VeriStoreClient


def _find_server_pids(server_id: int) -> list[int]:
    """Find uvicorn PIDs for a specific veri-store server ID by port."""
    port = 5000 + server_id
    result = subprocess.run(
        ["ps", "-eo", "pid,args"],
        capture_output=True,
        text=True,
        check=True,
    )
    pids: list[int] = []
    for line in result.stdout.splitlines():
        if "uvicorn src.network.server:app" not in line:
            continue
        if f"--port {port}" not in line:
            continue
        pid_str = line.strip().split(maxsplit=1)[0]
        try:
            pids.append(int(pid_str))
        except ValueError:
            continue
    return pids


def simulate_crash(server_ids: list[int]) -> None:
    """Stop the servers with the given IDs by sending SIGTERM."""
    for server_id in server_ids:
        pids = _find_server_pids(server_id)
        if not pids:
            print(f"[CRASH] WARN: no running process found for server {server_id}.")
            continue
        for pid in pids:
            os.kill(pid, signal.SIGTERM)
        print(f"[CRASH] Stopped server {server_id} (pid(s): {pids}).")


def main() -> None:
    """Run the fault tolerance demonstration with simple recovery metrics."""
    all_servers = [ServerAddress(i + 1, host="127.0.0.1", port=5001 + i) for i in range(5)]
    client = VeriStoreClient(servers=all_servers, m=3, timeout=2.0)

    data = b"This data should survive server crashes."
    key = f"fault_test_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    print("[PUT]   Storing data on all 5 servers...")
    client.put(key, data)
    print(f"[PUT]   Stored '{key}' on all 5 servers.")

    print("[CRASH] Simulating crash: servers 4 and 5 are now unreachable.")
    simulate_crash([4, 5])
    time.sleep(0.8)

    health = client.health_check()
    fragments_lost = sum(1 for ok in health.values() if not ok)
    print(f"[HEALTH] Server availability after crash: {health}")

    print("[GET]   Attempting retrieval with only 3 of 5 servers...")
    started = time.perf_counter()
    try:
        retrieved = client.get(key)
        recovery_time_s = time.perf_counter() - started
        assert retrieved == data
        success_rate = 1.0
        print("[GET]   Successfully reconstructed data from 3 fragments.")
        print("[OK]    Fault tolerance confirmed: 2-server crash tolerated.")
    except RetrievalError:
        recovery_time_s = time.perf_counter() - started
        success_rate = 0.0
        raise

    # Graceful degradation check: delete should not raise with crashed servers.
    client.delete(key)
    print("[DELETE] Completed cleanup request despite crashed servers.")

    print(
        "[METRICS] "
        f"success_rate={success_rate:.2f}, "
        f"fragments_lost={fragments_lost}, "
        f"recovery_time_s={recovery_time_s:.4f}"
    )


if __name__ == "__main__":
    main()
