#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC39 QA/AUDIT ALIGNMENT VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Ensure required evidence files are present
echo "Checking evidence files for RC30, RC32, and RC36..."
for f in "docs/evidence/compute/rc30-final-verification.md" \
         "docs/evidence/pert/rc32-has-hasf-pert-command-center.md" \
         "docs/evidence/compute/rc36-worker-visibility-utilization-dashboard.md"; do
    if [ ! -f "$f" ]; then
        echo "  [FAIL] Missing required evidence file: $f"
        exit 1
    fi
    echo "  [OK] Found evidence file: $f"
done

# Check 2: Run Telemetry Truth Compliance Audit
echo "Running Check 2: Telemetry Truth schema audit..."
bash scripts/telemetry_truth_check.sh
echo "  [PASS] Telemetry Truth schema audit passed."

# Check 3: Run Playwright E2E QA/Audit Alignment test
echo "Running Check 3: Playwright E2E QA/Audit Alignment test..."
npx playwright test tests/e2e/rc39-qa-audit-alignment.spec.ts
echo "  [PASS] Playwright E2E test passed."

echo "=================================================="
echo ">> SUCCESS: All RC39 QA/Audit Alignment checks PASS!"
echo "=================================================="
