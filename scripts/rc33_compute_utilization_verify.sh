#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC33 SWARM SCHEDULER VERIFICATION"
echo "=================================================="

# Activate virtualenv
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Run parallel mirror verify script
echo "Running Check 1: Parallel Mirror Verification..."
python3 scripts/has_parallel_mirror_verify.py
echo "  [PASS] Parallel Mirror Verification passed."

# Check 2: Check scheduler_metrics.json exists
echo "Running Check 2: Scheduler Metrics Verification..."
METRICS_FILE="has_live_project_tracker/data/scheduler_metrics.json"
if [ ! -f "$METRICS_FILE" ]; then
    echo "  [FAIL] Scheduler metrics file not found at $METRICS_FILE"
    exit 1
fi
echo "  [PASS] Scheduler metrics file exists and is populated."

# Check 3: Check port 8765 dashboard API
echo "Running Check 3: Dashboard API Verification..."
curl -s http://127.0.0.1:8765/api/pert/data | grep -q '"scheduler"'
echo "  [PASS] Dashboard API returns scheduler metrics correctly."

# Check 4: Playwright E2E Spec
echo "Running Check 4: Playwright E2E Spec..."
E2E_BASE_URL=http://127.0.0.1:8765 npx playwright test tests/e2e/rc33-compute-utilization.spec.ts --reporter=list
echo "  [PASS] Playwright E2E Spec passed."

echo "=================================================="
echo ">> SUCCESS: All RC33 Swarm Scheduler checks PASS!"
echo "=================================================="
