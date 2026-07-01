#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC34 USAGE BUDGET & BUILD GUARDRAILS VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Playwright / RC32 verify
echo "Running Check 1: RC32 Automation Cadence Verification..."
bash scripts/rc32_automation_cadence_verify.sh
echo "  [PASS] RC32 verification passed."

# Check 2: RC33 Swarm Scheduler verify
echo "Running Check 2: RC33 Compute Swarm Scheduler Verification..."
bash scripts/rc33_compute_utilization_verify.sh
echo "  [PASS] RC33 verification passed."

# Check 3: Run ag usage budget check
echo "Running Check 3: AG Usage Budget check..."
bash scripts/ag_usage_budget_check.sh
echo "  [PASS] AG Usage check passed."

# Check 4: Run local compute job queue check
echo "Running Check 4: Local Compute Job Queue check..."
bash scripts/local_compute_job_queue.sh
echo "  [PASS] Job Queue check passed."

# Check 5: Run secure build check
echo "Running Check 5: Secure Build Guardrails check..."
bash scripts/secure_build_guardrail_check.sh
echo "  [PASS] Secure Build check passed."

# Check 6: Check dashboard compatibility files exist
echo "Running Check 6: Metrics JSON files exist..."
if [ ! -f "has_live_project_tracker/data/usage_metrics.json" ] || [ ! -f "has_live_project_tracker/data/guardrail_metrics.json" ] || [ ! -f "has_live_project_tracker/data/job_queue.json" ]; then
    echo "  [FAIL] Missing metrics output files."
    exit 1
fi
echo "  [PASS] Metrics JSON files exist."

echo "=================================================="
echo ">> SUCCESS: All RC34 Usage Budget & Secure Build Guardrail checks PASS!"
echo "=================================================="
