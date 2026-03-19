#!/usr/bin/env bash
set -euo pipefail

# Launch 5 veri-store FastAPI servers (IDs 1..5) on ports 5001..5005.
#
# Usage:
#   ./scripts/run_servers.sh
#
# Optional env vars:
#   DATA_DIR=./data   (default: ./data)
#   HOST=127.0.0.1    (default: 127.0.0.1)
#
# Each server logs to stdout. Stop with Ctrl+C.

DATA_DIR="${DATA_DIR:-./data}"
HOST="${HOST:-127.0.0.1}"

cleanup() {
  # Kill all child processes in this process group.
  trap - INT TERM EXIT
  kill 0 || true
}
trap cleanup INT TERM EXIT

for id in 1 2 3 4 5; do
  port=$((5000 + id))
  echo "Starting server ${id} on ${HOST}:${port} (DATA_DIR=${DATA_DIR})"
  SERVER_ID="${id}" DATA_DIR="${DATA_DIR}" \
    uvicorn src.network.server:app --host "${HOST}" --port "${port}" &
done

wait

