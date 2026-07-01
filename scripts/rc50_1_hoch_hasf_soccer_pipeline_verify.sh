#!/usr/bin/env bash
# scripts/rc50_1_hoch_hasf_soccer_pipeline_verify.sh
# E2E verification runner for RC50.1: Onboard Downloads/hoch_hasf_soccer into HAS/HASF Pipeline.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC50.1: Verification of HOCH HASF Soccer Pipeline"
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
uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc50_1.log 2>&1 &
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
        cat /tmp/pert_server_rc50_1.log
        exit 1
    fi
    sleep 1
done

# 2. Run the onboarding audit, readiness audit, queue generator, and brief generator
echo "Running audits and brief generators..."
uv run python scripts/hoch_hasf_soccer_onboarding_audit.py
uv run python scripts/project_revenue_readiness_audit.py
uv run python scripts/generate_revenue_action_queue.py
uv run python scripts/generate_finance_operations_brief.py
bash scripts/rc49_5_refresh_truth_cascade.sh

# 3. Run Playwright E2E verification test for RC50.1
echo "Running Playwright E2E verification test for RC50.1..."
npx playwright test tests/e2e/rc50_1-hoch-hasf-soccer-pipeline.spec.ts

echo "============================================="
echo "RC50.1 Verification complete: PASS"
echo "============================================="
