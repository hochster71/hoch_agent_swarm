#!/usr/bin/env bash
# scripts/rc49_5_telemetry_truth_verify.sh
# E2E verification runner for RC49.5: Telemetry Truth, Freshness Authority, and Stripe Sandbox.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC49.5: Verification of Telemetry Truth & Stripe Sandbox"
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

# 1. Run Refresh Truth Cascade
echo "Running Refresh Truth Cascade..."
bash scripts/rc49_5_refresh_truth_cascade.sh

# 2. Run Stripe Sandbox config check
echo "Running Stripe Sandbox config check..."
python3 scripts/verify_stripe_sandbox_config.py

# 3. Restart PERT cockpit server to apply fresh code
echo "Killing any process listening on port 8765..."
lsof -ti :8765 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Starting fresh PERT cockpit server in background..."
uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc49_5.log 2>&1 &
SERVER_PID=$!
sleep 4

# 4. Run Playwright E2E verification test
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc49_5-telemetry-truth-freshness.spec.ts --reporter=list

echo "============================================="
echo "RC49.5 Verification complete: PASS"
echo "============================================="
