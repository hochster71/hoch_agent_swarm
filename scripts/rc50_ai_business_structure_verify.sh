#!/usr/bin/env bash
# scripts/rc50_ai_business_structure_verify.sh
# E2E verification runner for RC50: HASF AI Executive Leadership and Finance Operations Structure.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC50: Verification of HASF AI Executive Leadership & Finance Operations"
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

# 1. Restart PERT cockpit server to apply fresh code
echo "Killing any process listening on port 8765..."
lsof -ti :8765 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Starting fresh PERT cockpit server in background..."
uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc50.log 2>&1 &
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
        cat /tmp/pert_server_rc50.log
        exit 1
    fi
    sleep 1
done

# 2. Generate the Finance Operations Brief to ensure files are populated and fresh
echo "Generating Finance Operations Brief..."
uv run python scripts/generate_finance_operations_brief.py
bash scripts/rc49_5_refresh_truth_cascade.sh

# 3. Run Playwright E2E verification test for RC50
echo "Running Playwright E2E verification test for RC50..."
npx playwright test tests/e2e/rc50-ai-business-structure.spec.ts

echo "============================================="
echo "RC50 Verification complete: PASS"
echo "============================================="
