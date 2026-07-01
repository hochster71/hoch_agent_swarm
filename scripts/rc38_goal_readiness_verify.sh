#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC38 GOAL READINESS VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Run RC37 verification script
echo "Running Check 1: RC37 Verification gates..."
bash scripts/rc37_dispatch_verify.sh
echo "  [PASS] RC37 gates passed."

# Check 2: Query /api/pert/data and verify monetization payload exists
echo "Running Check 2: Verify monetization payload is returned by pert API..."
API_RESPONSE=$(curl -s http://127.0.0.1:8765/api/pert/data)
if echo "$API_RESPONSE" | grep -q '"monetization"'; then
    echo "  [PASS] pert data API payload contains monetization details."
else
    echo "  [FAIL] pert data API payload is missing monetization details!"
    exit 1
fi

# Check 3: Run RC38 E2E Playwright test
echo "Running Check 3: Playwright Goal Forecast & Monetization E2E test..."
npx playwright test tests/e2e/rc38-goal-readiness.spec.ts
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
echo ">> SUCCESS: All RC38 Goal Completion Forecast & Monetization Readiness checks PASS!"
echo "=================================================="
