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
#   VERI_STORE_TOKEN=test-token (default: test-token)
#   PYTHON_BIN=./.venv/bin/python (default: auto-detect ./.venv/bin/python, then ./venv/bin/python)
#
# Each server logs to stdout. Stop with Ctrl+C.

DATA_DIR="${DATA_DIR:-./data}"
HOST="${HOST:-127.0.0.1}"
VERI_STORE_TOKEN="${VERI_STORE_TOKEN:-test-token}"

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x "./.venv/bin/python" ]]; then
    PYTHON_BIN="./.venv/bin/python"
  elif [[ -x "./venv/bin/python" ]]; then
    PYTHON_BIN="./venv/bin/python"
  else
    echo "ERROR: no project Python interpreter found in ./.venv/bin/python or ./venv/bin/python"
    echo "Tip: create or restore the virtualenv first."
    exit 1
  fi
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: python interpreter not found at ${PYTHON_BIN}"
  echo "Tip: set PYTHON_BIN to the project's virtualenv Python."
  exit 1
fi

cleanup() {
  # Kill all child processes in this process group.
  trap - INT TERM EXIT
  kill 0 || true
}
trap cleanup INT TERM EXIT

for id in 1 2 3 4 5; do
  port=$((5000 + id))
  echo "Starting server ${id} on ${HOST}:${port} (DATA_DIR=${DATA_DIR})"
  SERVER_ID="${id}" DATA_DIR="${DATA_DIR}" VERI_STORE_TOKEN="${VERI_STORE_TOKEN}" \
    "${PYTHON_BIN}" -m uvicorn src.network.server:app --host "${HOST}" --port "${port}" &
done

wait
