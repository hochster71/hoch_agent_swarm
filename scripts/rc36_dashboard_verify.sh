#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC36 WORKER VISIBILITY DASHBOARD VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Run RC35 verification script
echo "Running Check 1: RC35 Verification gates..."
bash scripts/rc35_compute_expansion_verify.sh
echo "  [PASS] RC35 gates passed."

# Check 2: Query /api/pert/data and verify tailnet_workers payload exists
echo "Running Check 2: Verify tailnet_workers payload is returned by pert API..."
API_RESPONSE=$(curl -s http://127.0.0.1:8765/api/pert/data)
if echo "$API_RESPONSE" | grep -q '"tailnet_workers"'; then
    echo "  [PASS] pert data API payload contains tailnet_workers."
else
    echo "  [FAIL] pert data API payload is missing tailnet_workers!"
    exit 1
fi

# Check 3: Run RC36 E2E Playwright test
echo "Running Check 3: Playwright Worker Dashboard E2E test..."
npx playwright test tests/e2e/rc36-worker-dashboard.spec.ts
echo "  [PASS] Playwright E2E test passed."

# Check 4: Check git status
echo "Running Check 4: Git working directory state..."
if git status --short | grep -E -v "^?? logs/|task.md|walkthrough.md|implementation_plan.md|hoch_|docs/evidence/runtime/" | grep -q -v "^$"; then
    echo "  [FAIL] Git working tree is dirty!"
    git status --short
    exit 1
fi
echo "  [PASS] Git working directory clean."

echo "=================================================="
echo ">> SUCCESS: All RC36 Worker Visibility & Utilization Dashboard checks PASS!"
echo "=================================================="
