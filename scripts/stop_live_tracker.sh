#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TRACKER_PORT=${TRACKER_PORT:-3001}

echo "=================================================="
echo "STOPPING HAS/HASF LIVE PROJECT TRACKER"
echo "=================================================="
echo "Port: $TRACKER_PORT"

PID=$(lsof -t -iTCP:$TRACKER_PORT -sTCP:LISTEN || true)
if [ -n "$PID" ]; then
    echo "Found tracker process with PID: $PID. Sending SIGTERM..."
    kill "$PID"
    echo "[SUCCESS] Stopped tracker process on port $TRACKER_PORT."
else
    echo "No running process found on port $TRACKER_PORT."
fi
