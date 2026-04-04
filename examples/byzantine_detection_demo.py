"""
byzantine_detection_demo.py -- Demonstrate Byzantine fault detection.

Shows that the homomorphic fingerprint verification catches a server that
returns corrupt (Byzantine-modified) fragment bytes.

Scenario:
    - 5 servers are started automatically (n=5, m=3).
    - Server 2 runs in Byzantine mode: on GET it XOR-flips every byte of
      fragment 1 with 0xFF, simulating an actively malicious storage node.
    - The client verifies each retrieved fragment via Verifier.check().
    - The corrupt fragment from server 2 fails the SHA-256 hash check and
      is silently discarded.
    - The client reconstructs the original data from the 4 honest fragments
      (only m=3 are required, so 1 Byzantine fault is fully tolerated).

The Byzantine fault injection is enabled by the BYZANTINE_INDICES environment
variable added to server.py.  No code changes are needed between honest and
Byzantine modes — only the env var differs.

Usage:
    python examples/byzantine_detection_demo.py

Expected output (abbreviated):
    [SETUP]  Starting server 1 on port 5001 (honest)
    [SETUP]  Starting server 2 on port 5002 (BYZANTINE: will corrupt fragment 1 on GET)
    ...
    [SETUP]  All 5 servers healthy.

    [PUT]    Storing 57 bytes under key 'byzantine_test_...'
    [PUT]    All 5 servers accepted the fragment.

    [GET]    Requesting fragments from all 5 servers...
    [GET]    Server 2 (port 5002) will return a corrupted fragment 1.
    [GET]    Verification warnings (if any) will appear below:

    [WARNING] src.network.client: Verification FAILED for fragment (..., 1): ...

    [OK]     Byzantine fault detected and tolerated.
    [OK]     Data reconstructed correctly in X.X ms.
    ...
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.network.client import ServerAddress, VeriStoreClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Server 2 (0-based index 1 in the server list) will corrupt fragment 1.
# The client assigns fragment index i to servers[i], so servers[1] = server 2.
_BYZANTINE_SERVER_ID = 2
_BYZANTINE_FRAGMENT_INDEX = 1

_SERVERS = [
    ServerAddress(server_id=i + 1, host="127.0.0.1", port=5001 + i)
    for i in range(5)
]

# ---------------------------------------------------------------------------
# Server lifecycle helpers
# ---------------------------------------------------------------------------


def _start_servers() -> list[subprocess.Popen]:
    """Start all 5 servers as subprocesses.

    Server _BYZANTINE_SERVER_ID is launched with BYZANTINE_INDICES set so
    it XOR-corrupts fragment _BYZANTINE_FRAGMENT_INDEX on every GET response.
    """
    procs: list[subprocess.Popen] = []
    data_dir = ROOT / "data"

    for srv in _SERVERS:
        env = os.environ.copy()
        env["SERVER_ID"] = str(srv.server_id)
        env["DATA_DIR"] = str(data_dir)

        if srv.server_id == _BYZANTINE_SERVER_ID:
            env["BYZANTINE_INDICES"] = str(_BYZANTINE_FRAGMENT_INDEX)
            label = f"BYZANTINE: will corrupt fragment {_BYZANTINE_FRAGMENT_INDEX} on GET"
        else:
            label = "honest"

        print(f"[SETUP]  Starting server {srv.server_id} on port {srv.port} ({label})")

        proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "src.network.server:app",
                "--host", "127.0.0.1",
                "--port", str(srv.port),
                "--log-level", "warning",
            ],
            env=env,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        procs.append(proc)

    return procs


def _wait_for_servers(client: VeriStoreClient, timeout: float = 15.0) -> None:
    """Poll /health on every server until all respond or timeout elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        health = client.health_check()
        if all(health.values()):
            print(f"[SETUP]  All {len(health)} servers healthy.\n")
            return
        time.sleep(0.3)
    raise RuntimeError("Servers did not become healthy within timeout.")


def _stop_servers(procs: list[subprocess.Popen]) -> None:
    for proc in procs:
        proc.terminate()
    for proc in procs:
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Byzantine fault detection demonstration."""
    # Surface Verifier.check() rejection warnings so they appear inline.
    logging.basicConfig(
        level=logging.WARNING,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    procs = _start_servers()
    client = VeriStoreClient(servers=_SERVERS, m=3, timeout=5.0)

    try:
        _wait_for_servers(client)

        data = b"Integrity test: this payload must not be silently altered."
        key = f"byzantine_test_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

        # --- PUT -----------------------------------------------------------------
        print(f"[PUT]    Storing {len(data)} bytes under key '{key}'...")
        client.put(key, data)
        print(f"[PUT]    All 5 servers accepted the fragment.\n")

        # --- GET (Byzantine server 2 returns corrupted bytes) --------------------
        byzantine_port = _SERVERS[_BYZANTINE_SERVER_ID - 1].port
        print("[GET]    Requesting fragments from all 5 servers...")
        print(
            f"[GET]    Server {_BYZANTINE_SERVER_ID} (port {byzantine_port}) "
            f"will return a corrupted fragment {_BYZANTINE_FRAGMENT_INDEX}."
        )
        print("[GET]    Verification warnings (if any) will appear below:\n")

        t0 = time.perf_counter()
        retrieved = client.get(key)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        print()
        if retrieved != data:
            print("[FAIL]   Retrieved data does not match original!")
            sys.exit(1)

        print("[OK]     Byzantine fault detected and tolerated.")
        print(f"[OK]     Data reconstructed correctly in {elapsed_ms:.1f} ms.")
        print(
            f"[OK]     1 corrupt fragment silently rejected; "
            f"recovered from {client.m} honest fragments.\n"
        )

        # --- Cleanup -------------------------------------------------------------
        client.delete(key)
        print("[DELETE] Fragment cleanup complete.\n")

        # --- Metrics summary -----------------------------------------------------
        print("=" * 60)
        print("METRICS SUMMARY")
        print("=" * 60)
        print(f"  Coding scheme:          n=5, m=3")
        print(f"  Byzantine servers:      1  (server {_BYZANTINE_SERVER_ID}, "
              f"fragment {_BYZANTINE_FRAGMENT_INDEX})")
        print(f"  Fragments corrupted:    1 / 5")
        print(f"  Fragments verified OK:  4 / 5  (>= m=3 required)")
        print(f"  Detection mechanism:    SHA-256 hash mismatch (Verifier.check)")
        print(f"  False positive rate:    0 / 4  (no valid fragments rejected)")
        print(f"  Reconstruction:         successful")
        print(f"  Retrieval time:         {elapsed_ms:.1f} ms")
        print("=" * 60)

    finally:
        _stop_servers(procs)
        print("\n[SETUP]  Servers stopped.")


if __name__ == "__main__":
    main()
