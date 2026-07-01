#!/bin/bash
# launch.sh — Production Startup Launch Script for CLAWDE Control Tower
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export PYTHONPATH="$BASE_DIR"

echo "[launch] Verifying python environment..."
if [ ! -d "$BASE_DIR/.venv" ]; then
    echo "[launch] ERROR: Virtual environment not found at $BASE_DIR/.venv"
    exit 1
fi

source "$BASE_DIR/.venv/bin/activate"

# Inject environment variables from environment.env if present
if [ -f "$BASE_DIR/runtime/environment.env" ]; then
    echo "[launch] Loading environment configurations..."
    export $(grep -v '^#' "$BASE_DIR/runtime/environment.env" | xargs)
fi

echo "[launch] Launching FastAPI backend server on port 8000..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "[launch] Launching dashboard cockpit interface on port 8085..."
# Note: Static assets are pre-compiled and served via python http server or proxy
python3 -m http.server 8085 --directory "$BASE_DIR/frontend/dist" &
FRONTEND_PID=$!

# Trap signals to ensure clean shutdown of child processes
cleanup() {
    echo "[launch] Shutting down services..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup SIGINT SIGTERM EXIT

wait
