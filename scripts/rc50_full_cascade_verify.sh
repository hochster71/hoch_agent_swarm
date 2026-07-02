#!/usr/bin/env bash
# scripts/rc50_full_cascade_verify.sh
# Runs full verification cascade for RC50, RC49, RC48, RC47, RC46, RC45, RC44, RC43, RC41, RC40, RC39, and RC34.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
echo "STARTING FULL VERIFICATION CASCADE (RC34 - RC52.1)"
echo "=========================================================="

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

# 1. Start uvicorn server
echo "Killing any process listening on port 8765..."
lsof -ti :8765 | xargs kill -9 2>/dev/null || true
sleep 1

echo "Starting fresh PERT cockpit server in background..."
uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_cascade.log 2>&1 &
SERVER_PID=$!

# Wait for server to wake up
echo "Waiting for PERT server to wake up..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8765/health >/dev/null; then
        echo "PERT server is active."
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "Error: PERT server failed to start."
        exit 1
    fi
    sleep 1
done

# 1.5 Refresh telemetry truth cascade to ensure all files have fresh timestamps
echo "Refreshing telemetry truth cascade..."
bash scripts/rc49_5_refresh_truth_cascade.sh

# 2. Run Playwright E2E test suite for all cascade targets
echo "Running Playwright E2E cascade tests..."
npx playwright test \
    tests/e2e/rc52_1-hoch-pods-space-swarm-theater.spec.ts \
    tests/e2e/rc52-governed-execution-runner.spec.ts \
    tests/e2e/rc51-execution-approval-queue.spec.ts \
    tests/e2e/rc50_1-hoch-hasf-soccer-pipeline.spec.ts \
    tests/e2e/rc50-ai-business-structure.spec.ts \
    tests/e2e/rc49_7-compute-node-pruning.spec.ts \
    tests/e2e/rc49_6-hoch-pods-visual-fidelity.spec.ts \
    tests/e2e/rc49_5-telemetry-truth-freshness.spec.ts \
    tests/e2e/rc49-hoch-pod-scheduler.spec.ts \
    tests/e2e/rc48-hoch-pods-architecture.spec.ts \
    tests/e2e/rc47-epic-fury-admin-access.spec.ts \
    tests/e2e/rc46-revenue-action-queue.spec.ts \
    tests/e2e/rc45-revenue-readiness.spec.ts \
    tests/e2e/rc44-epic-fury-flowchart.spec.ts \
    tests/e2e/rc43-telemetry-freshness.spec.ts \
    tests/e2e/rc41-worker-telemetry-accuracy.spec.ts \
    tests/e2e/rc40-compute-gap-pert.spec.ts \
    tests/e2e/rc39-telemetry-truth.spec.ts \
    tests/e2e/rc39-qa-audit-alignment.spec.ts

# 3. Run RC34 verification script
echo "Running RC34 verification script..."
bash scripts/rc34_usage_guardrail_verify.sh

echo "=========================================================="
echo "CASCADE SUCCESS: All verification gates (RC34-RC52.1) PASS!"
echo "=========================================================="
