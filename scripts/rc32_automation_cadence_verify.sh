#!/usr/bin/env bash
# ==============================================================================
# scripts/rc32_automation_cadence_verify.sh
# ==============================================================================
# Revised RC32 Verification Script.
# Runs the full automation cadence verification suite in order:
#   1. rc31_sustainment_verify.sh
#   2. has_parallel_mirror_verify.sh
#   3. rc32_pert_command_center_verify.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "======================================================================"
echo "        RC32 Automation Cadence & Dashboard Verification"
echo "======================================================================"

FAILED=0

# Helper to run and log status
run_check() {
    local script_name="$1"
    local name="$2"
    echo "Running check: ${name}..."
    if bash "$PROJECT_ROOT/${script_name}"; then
        echo "  [PASS] ${name}"
    else
        echo "  [FAIL] ${name}"
        FAILED=1
    fi
}

run_check "scripts/rc31_sustainment_verify.sh" "Check 1: Production Sustainment Verification"
run_check "scripts/has_parallel_mirror_verify.sh" "Check 2: Parallel Mirror Verification"
run_check "scripts/rc32_pert_command_center_verify.sh" "Check 3: PERT Command Center Live Verification"

echo "======================================================================"
if [ "${FAILED}" -eq 0 ]; then
    echo "  >> SUCCESS: RC32 Autonomous Cadence & Dashboard checks passed completely!"
    echo "======================================================================"
    exit 0
else
    echo "  >> FAILURE: One or more verification checks failed."
    echo "======================================================================"
    exit 1
fi
