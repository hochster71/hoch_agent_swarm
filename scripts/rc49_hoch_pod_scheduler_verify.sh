#!/usr/bin/env bash
# scripts/rc49_hoch_pod_scheduler_verify.sh
# Verification runner for RC49: Compute-Aware HOCH PODS Scheduler and Node Health Authority.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC49: Verification of HOCH PODS Compute Scheduler"
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

# 1. Compile Node Health Metrics
echo "Compiling HOCH Compute Node Health..."
python3 scripts/collect_hoch_compute_node_health.py

# 2. Run HOCH Pods Scheduler
echo "Running HOCH Pods Scheduler..."
python3 scripts/schedule_hoch_pods.py

# 3. Check architecture & compliance documents exist
echo "Checking documentation and data files..."
files=(
    "docs/evidence/runtime/hoch-compute-node-health.md"
    "docs/evidence/runtime/hoch-pod-scheduler-evidence.md"
    "has_live_project_tracker/data/hoch_compute_nodes.json"
    "has_live_project_tracker/data/hoch_compute_node_health.json"
    "has_live_project_tracker/data/hoch_pod_schedule.json"
)

for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "  [FAIL] Required file $file is missing!"
        exit 1
    fi
    echo "  [PASS] Found: $file"
done

# 4. Check if PERT cockpit server is running
if ! curl -s -m 2 http://127.0.0.1:8765/ >/dev/null; then
    echo "Starting PERT cockpit server in background..."
    uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc49.log 2>&1 &
    SERVER_PID=$!
    sleep 3
else
    echo "PERT cockpit server is already running."
fi

# 5. Run Playwright E2E verification test
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc49-hoch-pod-scheduler.spec.ts --reporter=list

echo "============================================="
echo "RC49 Verification complete: PASS"
echo "============================================="
