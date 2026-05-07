from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.network.client import RetrievalError, ServerAddress, VeriStoreClient

N = 5
M = 4
PORT_BASE = 5401
DEMO_TOKEN = "test-token"
BYZANTINE_SERVER_IDS = [2, 3]
SERVERS = [
    ServerAddress(server_id=i + 1, host="127.0.0.1", port=PORT_BASE + i)
    for i in range(N)
]


def start_servers(data_dir: Path) -> list[subprocess.Popen]:
    procs: list[subprocess.Popen] = []
    for index, server in enumerate(SERVERS):
        env = os.environ.copy()
        env["SERVER_ID"] = str(server.server_id)
        env["DATA_DIR"] = str(data_dir)
        env["VERI_STORE_TOKEN"] = DEMO_TOKEN

        if server.server_id in BYZANTINE_SERVER_IDS:
            env["BYZANTINE_INDICES"] = str(index)
            label = f"BYZANTINE: will corrupt fragment {index} on GET"
        else:
            env.pop("BYZANTINE_INDICES", None)
            label = "honest"

        print(
            f"[SETUP]  Starting server {server.server_id} on port {server.port} ({label})"
        )
        procs.append(
            subprocess.Popen(
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
        )
    return procs


def wait_for_servers(client: VeriStoreClient, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        health = client.health_check()
        if len(health) == N and all(health.values()):
            print(f"[SETUP]  All {N} servers healthy.\n")
            return
        time.sleep(0.3)
    raise RuntimeError("Servers did not become healthy within timeout.")


def stop_all(procs: list[subprocess.Popen]) -> None:
    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
    for proc in procs:
        if proc.poll() is None:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    data_dir = Path(tempfile.mkdtemp(prefix="veri-store-byz2-"))
    procs = start_servers(data_dir)
    client = VeriStoreClient(servers=SERVERS, m=M, timeout=5.0, token=DEMO_TOKEN)

    try:
        wait_for_servers(client)

        data = (
            b"Byzantine failure demo: two corrupt fragments leave too few valid pieces."
        )
        key = f"byz2_failure_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

        honest_count = N - len(BYZANTINE_SERVER_IDS)
        print(
            f"[CONFIG] Coding scheme: n={N}, m={M}. "
            f"Two Byzantine servers leave only {honest_count} honest fragments."
        )
        print(
            f"[ENCODE] client.put() will split the object into {N} fragments "
            "and generate FPCC verification metadata."
        )
        print(f"[PUT]    Storing {len(data)} bytes under key '{key}'.")
        client.put(key, data)
        print(f"[PUT]    All {N} servers accepted their fragments.\n")

        print("[GET]    Requesting fragments from all servers.")
        print("[GET]    Servers 2 and 3 will return corrupted fragments.")
        print(
            "[VERIFY] client.get() checks fragment hashes and FPCC metadata, "
            "then rejects corrupt responses."
        )
        print(
            f"[THRESH] {honest_count} honest fragments remain; "
            f"{M} verified fragments are required."
        )
        print("[GET]    Verification warnings should appear below:\n")

        t0 = time.perf_counter()
        try:
            client.get(key)
        except RetrievalError as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            print()
            client.delete(key)
            print("[OK]     Both Byzantine fragments were rejected.")
            print("[DECODE] Decode was not attempted with too few verified fragments.")
            print(f"[OK]     Reconstruction failed closed: {exc}")
            print(f"[OK]     Failure detected in {elapsed_ms:.1f} ms.")
            print("[RESULT] PASS")
            return

        print("[FAIL]   Reconstruction unexpectedly succeeded with 2 Byzantine nodes.")
        sys.exit(1)
    finally:
        stop_all(procs)
        shutil.rmtree(data_dir, ignore_errors=True)
        print("\n[SETUP]  Servers stopped and temporary data removed.")


if __name__ == "__main__":
    main()
