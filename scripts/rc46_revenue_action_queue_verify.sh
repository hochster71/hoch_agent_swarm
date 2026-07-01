#!/usr/bin/env bash
# scripts/rc46_revenue_action_queue_verify.sh
# Verification runner for RC46 Revenue Action Queue and Critical Path Autopilot.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC46: Verification of Revenue Action Queue"
echo "============================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check if PERT cockpit server is running
SERVER_PID=""
if ! curl -s -m 2 http://127.0.0.1:8765/ >/dev/null; then
    echo "Starting PERT cockpit server in background..."
    uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc46.log 2>&1 &
    SERVER_PID=$!
    sleep 3
else
    echo "PERT cockpit server is already running."
fi

# Cleanup handler to stop server on exit
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping the background PERT cockpit server..."
        kill -9 "$SERVER_PID" || true
    fi
}
trap cleanup EXIT

# 1. Run revenue readiness audit and queue generator
echo "Running project revenue readiness audit..."
python3 scripts/project_revenue_readiness_audit.py

echo "Running revenue action queue generator..."
python3 scripts/generate_revenue_action_queue.py

# 2. Check evidence files existence
echo "Checking results and evidence documents..."
if [ ! -f "has_live_project_tracker/data/revenue_action_queue.json" ]; then
    echo "  [FAIL] revenue_action_queue.json not found!"
    exit 1
fi
if [ ! -f "docs/evidence/business/revenue-action-queue.md" ]; then
    echo "  [FAIL] docs/evidence/business/revenue-action-queue.md not found!"
    exit 1
fi
echo "  [PASS] Revenue action queue registry and markdown report exist."

# 3. Run Playwright E2E verification test
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc46-revenue-action-queue.spec.ts --reporter=list

echo "============================================="
echo "RC46 Verification complete: PASS"
echo "============================================="
