#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC40 STRIPE SANDBOX READINESS VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Ensure .env.stripe.sandbox is ignored in Git
echo "Running Check 1: Git ignore verification..."
if git check-ignore -q .env.stripe.sandbox; then
    echo "  [PASS] .env.stripe.sandbox is correctly ignored by git."
else
    echo "  [FAIL] .env.stripe.sandbox is NOT ignored by git! Add it to .gitignore."
    exit 1
fi

# Check 2: Run Telemetry Truth Compliance Audit
echo "Running Check 2: Telemetry Truth compliance audit..."
bash scripts/telemetry_truth_check.sh
echo "  [PASS] Telemetry Truth compliance audit passed."

# Check 3: Run Playwright E2E Stripe Sandbox Readiness test
echo "Running Check 3: Playwright E2E Stripe Sandbox test..."
npx playwright test tests/e2e/rc40-stripe-readiness.spec.ts
echo "  [PASS] Playwright E2E test passed."

echo "=================================================="
echo ">> SUCCESS: All RC40 Stripe Sandbox checks PASS!"
echo "=================================================="
