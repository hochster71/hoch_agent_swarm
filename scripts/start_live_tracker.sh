#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load env defaults
export TRACKER_PORT=${TRACKER_PORT:-3001}
export UI_USER=${UI_USER:-admin}
export UI_PASS=${UI_PASS:-change-this-password}

echo "=================================================="
echo "STARTING HAS/HASF LIVE PROJECT TRACKER"
echo "=================================================="
echo "Port:       $TRACKER_PORT"
echo "Username:   $UI_USER"
echo "Password:   $UI_PASS"
echo "Project:    $PROJECT_ROOT"

# Check if port is already in use
if lsof -nP -iTCP:$TRACKER_PORT -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[ERROR] Port $TRACKER_PORT is already in use! Kill the process or set TRACKER_PORT."
    exit 1
fi

# Run background process
cd "$PROJECT_ROOT/has_live_project_tracker"
nohup node server.js > tracker.log 2>&1 &
TRACKER_PID=$!

echo "[SUCCESS] Live Tracker started in background (PID: $TRACKER_PID)."
echo "URL: http://localhost:$TRACKER_PORT"
echo "Log file: $PROJECT_ROOT/has_live_project_tracker/tracker.log"
