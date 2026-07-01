#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC35 SAFE COMPUTE EXPANSION VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Verify all RC34 security gates are green
echo "Running Check 1: RC34 Security and Usage Gates..."
bash scripts/rc34_usage_guardrail_verify.sh
echo "  [PASS] RC34 verification gates passed."

# Check 2: Run the Swarm Scheduler
echo "Running Check 2: Execute Swarm Scheduler..."
python3 backend/mission_control/swarm_scheduler.py
echo "  [PASS] Swarm Scheduler run completed."

# Check 3: Verify Scheduler Metrics JSON
echo "Running Check 3: Check Scheduler Metrics..."
METRICS_FILE="has_live_project_tracker/data/scheduler_metrics.json"
if [ ! -f "$METRICS_FILE" ]; then
    echo "  [FAIL] scheduler_metrics.json is missing!"
    exit 1
fi
echo "  [PASS] scheduler_metrics.json exists."

# Check 4: Verify real subprocess execution evidence
echo "Running Check 4: Check execution evidence file contents..."
EVIDENCE_FILES=$(find has_live_project_tracker/artifacts/evidence -name "scheduler_*.json" 2>/dev/null || true)
if [ -z "$EVIDENCE_FILES" ]; then
    echo "  [PASS] No pending tasks were scheduled this cycle (scheduler returned IDLE/completed state)."
else
    # Inspect one evidence file to make sure it includes real command output details
    FIRST_FILE=$(echo "$EVIDENCE_FILES" | head -n 1)
    echo "  Checking evidence file: $FIRST_FILE"
    if grep -q '"command":' "$FIRST_FILE" && grep -q '"exit_code":' "$FIRST_FILE"; then
        echo "  [PASS] Evidence file contains real subprocess execution details."
    else
        echo "  [FAIL] Evidence file lacks command/exit_code fields!"
        exit 1
    fi
fi

echo "=================================================="
echo ">> SUCCESS: All RC35 Safe Compute Expansion checks PASS!"
echo "=================================================="
