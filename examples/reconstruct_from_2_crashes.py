from __future__ import annotations

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

from src.network.client import ServerAddress, VeriStoreClient

N = 5
M = 3
PORT_BASE = 5101
DEMO_TOKEN = "test-token"
CRASHED_SERVER_IDS = [4, 5]
SERVERS = [
    ServerAddress(server_id=i + 1, host="127.0.0.1", port=PORT_BASE + i)
    for i in range(N)
]


def start_servers(data_dir: Path) -> list[subprocess.Popen]:
    procs: list[subprocess.Popen] = []
    for server in SERVERS:
        env = os.environ.copy()
        env["SERVER_ID"] = str(server.server_id)
        env["DATA_DIR"] = str(data_dir)
        env["VERI_STORE_TOKEN"] = DEMO_TOKEN
        env.pop("BYZANTINE_INDICES", None)

        print(f"[SETUP]  Starting server {server.server_id} on port {server.port}")
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


def stop_selected(procs: list[subprocess.Popen], server_ids: list[int]) -> None:
    for server_id in server_ids:
        proc = procs[server_id - 1]
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        print(f"[CRASH]  Server {server_id} stopped.")


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
    data_dir = Path(tempfile.mkdtemp(prefix="veri-store-crash2-"))
    procs = start_servers(data_dir)
    client = VeriStoreClient(servers=SERVERS, m=M, timeout=5.0, token=DEMO_TOKEN)

    try:
        wait_for_servers(client)

        data = b"Crash tolerance demo: this object survives two server crashes."
        key = f"crash2_success_{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

        print(
            f"[CONFIG] Coding scheme: n={N}, m={M}. "
            f"Any {M} verified fragments reconstruct the object."
        )
        print(
            f"[ENCODE] client.put() will split the object into {N} fragments "
            "and generate FPCC verification metadata."
        )
        print(f"[PUT]    Storing {len(data)} bytes under key '{key}'.")
        client.put(key, data)
        print(f"[PUT]    All {N} servers accepted their fragments.\n")

        print("[CRASH]  Simulating crashes for servers 4 and 5.")
        stop_selected(procs, CRASHED_SERVER_IDS)
        health = client.health_check()
        available = sum(1 for ok in health.values() if ok)
        print(f"[HEALTH] Availability after crashes: {health}\n")

        print(
            "[VERIFY] client.get() will verify each returned fragment before "
            "using it for decode."
        )
        print(
            f"[THRESH] {available} servers remain available; "
            f"{M} verified fragments are required."
        )
        print(f"[GET]    Attempting reconstruction with {available}/{N} servers.")
        t0 = time.perf_counter()
        retrieved = client.get(key)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if retrieved != data:
            print("[FAIL]   Reconstructed bytes do not match the original object.")
            sys.exit(1)

        print("[OK]     Reconstruction succeeded after 2 crashes.")
        print(
            "[DECODE] The decoder rebuilt the original bytes from the "
            "verified fragment set."
        )
        print(
            f"[OK]     Recovered from exactly {M} available fragments in {elapsed_ms:.1f} ms."
        )
        print("[RESULT] PASS")
    finally:
        stop_all(procs)
        shutil.rmtree(data_dir, ignore_errors=True)
        print("\n[SETUP]  Servers stopped and temporary data removed.")


if __name__ == "__main__":
    main()
