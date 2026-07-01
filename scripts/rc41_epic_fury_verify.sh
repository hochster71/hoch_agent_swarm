#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC41 EPIC FURY ONBOARDING VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Verify Epic Fury is in local inventory
echo "Running Check 1: Local inventory registry check..."
if grep -q "Epic-fury-2026-main" has_live_project_tracker/data/local_project_inventory.json; then
    echo "  [PASS] Epic Fury is tracked in the local inventory."
else
    echo "  [FAIL] Epic Fury is NOT tracked in local inventory!"
    exit 1
fi

# Check 2: Verify audit, gap, and PERT model evidence files exist
echo "Running Check 2: Verification of required documentation..."
if [ -f "docs/evidence/business/epic-fury-onboarding-audit.md" ] && \
   [ -f "docs/evidence/business/epic-fury-gap-analysis.md" ] && \
   [ -f "docs/evidence/business/epic-fury-pert-model.md" ]; then
    echo "  [PASS] All onboarding evidence and analysis documents exist."
else
    echo "  [FAIL] One or more onboarding documents are missing!"
    exit 1
fi

# Check 3: Run Telemetry Truth Compliance Audit
echo "Running Check 3: Telemetry Truth compliance audit..."
bash scripts/telemetry_truth_check.sh
echo "  [PASS] Telemetry Truth compliance audit passed."

# Check 4: Run Playwright E2E Onboarding test
echo "Running Check 4: Playwright E2E Epic Fury test..."
npx playwright test tests/e2e/rc41-epic-fury-onboarding.spec.ts
echo "  [PASS] Playwright E2E test passed."

# Check 5: Port 3012 Public Exposure Check
echo "Running Check 5: Port 3012 Public Exposure Check..."
if python3 -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('50.116.41.183', 3012))" 2>/dev/null; then
    echo "  [FAIL] Port 3012 is reachable from public IP!"
    exit 1
else
    echo "  [PASS] Port 3012 is closed/blocked to public access."
fi

echo "=================================================="
echo ">> SUCCESS: All RC41 Epic Fury checks PASS!"
echo "=================================================="
