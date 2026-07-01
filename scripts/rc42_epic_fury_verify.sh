#!/usr/bin/env bash
# scripts/rc42_epic_fury_verify.sh — Comprehensive verification cascade for RC42
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC42 EPIC FURY CSP AUDIT VERIFICATION"
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

# Check 3: Content Security Policy Audit
echo "Running Check 3: Content Security Policy static audit..."
python3 scripts/epic_fury_csp_audit.py
echo "  [PASS] Content Security Policy audit passed."

# Check 4: Run Telemetry Truth Compliance Audit
echo "Running Check 4: Telemetry Truth compliance audit..."
bash scripts/telemetry_truth_check.sh
echo "  [PASS] Telemetry Truth compliance audit passed."

# Check 5: Run Playwright E2E Epic Fury test
echo "Running Check 5: Playwright E2E Epic Fury test..."
npx playwright test tests/e2e/rc42-epic-fury-csp-audit.spec.ts
echo "  [PASS] Playwright E2E test passed."

# Check 6: Port 3012 Public Exposure Check
echo "Running Check 6: Port 3012 Public Exposure Check..."
if python3 -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('50.116.41.183', 3012))" 2>/dev/null; then
    echo "  [FAIL] Port 3012 is reachable from public IP!"
    exit 1
else
    echo "  [PASS] Port 3012 is closed/blocked to public access."
fi

echo "=================================================="
echo ">> SUCCESS: All RC42 Epic Fury checks PASS!"
echo "=================================================="
