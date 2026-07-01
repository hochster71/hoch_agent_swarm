#!/usr/bin/env bash
# scripts/rc51_execution_approval_queue_verify.sh
# E2E verification runner for RC51: Add Autonomous Execution Approval Queue and Safe Write Gates

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC51: Verification of Swarm Execution Approval Queue"
echo "============================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

SERVER_PID=""

# Cleanup handler
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping the background PERT cockpit server..."
        kill -9 "$SERVER_PID" || true
    fi
}
trap cleanup EXIT

# 1. Start PERT cockpit server in background
echo "Killing any process listening on port 8765..."
lsof -ti :8765 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Starting fresh PERT cockpit server in background..."
uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc51.log 2>&1 &
SERVER_PID=$!

# Wait for server to wake up
echo "Waiting for PERT server to wake up..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8765/health >/dev/null; then
        echo "PERT server is active."
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "Error: PERT server failed to start. Logs:"
        cat /tmp/pert_server_rc51.log
        exit 1
    fi
    sleep 1
done

# 2. Run the generators to ensure fresh data
echo "Running proposal generator..."
uv run python scripts/generate_execution_approval_queue.py
bash scripts/rc49_5_refresh_truth_cascade.sh

# 3. Run Playwright E2E verification test for RC51
echo "Running Playwright E2E verification test for RC51..."
npx playwright test tests/e2e/rc51-execution-approval-queue.spec.ts

echo "============================================="
echo "RC51 Verification complete: PASS"
echo "============================================="
