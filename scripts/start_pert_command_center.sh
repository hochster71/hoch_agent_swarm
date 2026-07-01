#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT=8765
HOST="127.0.0.1"

echo "=================================================="
echo "STARTING HAS/HASF PERT COMMAND CENTER"
echo "=================================================="
echo "Port: $PORT"
echo "Host: $HOST"
echo "Project Root: $PROJECT_ROOT"

# Check if port is already in use
if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[ERROR] Port $PORT is already in use! Kill the process or select another port."
    exit 1
fi

# Activate virtualenv
if [ -d "$PROJECT_ROOT/.venv" ]; then
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/.venv/bin/activate"
else
    echo "[WARNING] No .venv found in $PROJECT_ROOT. Running with system python."
fi

# Run background process
cd "$PROJECT_ROOT"
mkdir -p logs
nohup uvicorn backend.pert_server:app --host "$HOST" --port "$PORT" > logs/pert_command_center.log 2>&1 &
SERVER_PID=$!

echo "[SUCCESS] PERT Command Center started in background (PID: $SERVER_PID)."
echo "Dashboard: http://$HOST:$PORT"
echo "Log file: $PROJECT_ROOT/logs/pert_command_center.log"
