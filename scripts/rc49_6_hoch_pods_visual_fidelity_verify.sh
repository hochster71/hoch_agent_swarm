#!/usr/bin/env bash
# scripts/rc49_6_hoch_pods_visual_fidelity_verify.sh
# E2E verification runner for RC49.6: HOCH PODS Visual Fidelity & Launch Animation Hardening.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
# Playwright execution header
echo "RC49.6: Verification of HOCH PODS Visual Fidelity & Cockpit Layout"
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
uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc49_6.log 2>&1 &
SERVER_PID=$!
sleep 4

# 2. Run Playwright E2E verification tests
echo "Running Playwright E2E verification test for Visual Fidelity..."
npx playwright test tests/e2e/rc49_6-hoch-pods-visual-fidelity.spec.ts --reporter=list

echo "Running Playwright E2E regression test for RC48 HOCH PODS Architecture..."
npx playwright test tests/e2e/rc48-hoch-pods-architecture.spec.ts --reporter=list

echo "Running Playwright E2E regression test for RC49 HOCH Pod Scheduler..."
npx playwright test tests/e2e/rc49-hoch-pod-scheduler.spec.ts --reporter=list

echo "Running Playwright E2E regression test for RC49.5 Telemetry Truth & Stripe Sandbox..."
npx playwright test tests/e2e/rc49_5-telemetry-truth-freshness.spec.ts --reporter=list

echo "============================================="
echo "RC49.6 Verification complete: PASS"
echo "============================================="
