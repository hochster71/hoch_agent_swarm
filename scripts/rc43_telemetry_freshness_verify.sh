#!/bin/bash
set -e

# Make sure we're in the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo "============================================="
echo "RC43: Verification of Telemetry Freshness Authority"
echo "============================================="

# Ensure backend server is running on 8765
echo "Checking if PERT cockpit server is running..."
if ! curl -s -m 2 http://127.0.0.1:8765/ >/dev/null; then
    echo "Starting PERT cockpit server in background..."
    uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_verify.log 2>&1 &
    SERVER_PID=$!
    # Wait for server to boot
    sleep 3
else
    echo "PERT cockpit server is already running."
fi

# Run the python compliance audit script
echo "Running freshness dynamic audit..."
uv run python scripts/telemetry_freshness_audit.py

# Run the Playwright spec
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc43-telemetry-freshness.spec.ts

echo "============================================="
echo "RC43 Verification complete: PASS"
echo "============================================="

# Clean up server if we started it
if [ ! -z "$SERVER_PID" ]; then
    echo "Stopping the background PERT cockpit server..."
    kill $SERVER_PID
fi
