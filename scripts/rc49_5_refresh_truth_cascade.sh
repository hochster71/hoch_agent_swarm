#!/usr/bin/env bash
# scripts/rc49_5_refresh_truth_cascade.sh
# Deterministic cascade refresher for telemetry truth and freshness authority.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "HOCH TELEMETRY TRUTH FRESHNESS CASCADE"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

echo "0. Running Soccer Onboarding Audit..."
python3 scripts/hoch_hasf_soccer_onboarding_audit.py

echo "1. Running Project Revenue Readiness Audit..."
python3 scripts/project_revenue_readiness_audit.py

echo "2. Generating Revenue Action Queue..."
python3 scripts/generate_revenue_action_queue.py

echo "3. Generating HOCH PODS Runtime State..."
python3 scripts/generate_hoch_pods_runtime_state.py

echo "4. Collecting HOCH Compute Node Health..."
python3 scripts/collect_hoch_compute_node_health.py

echo "5. Running HOCH Pods Scheduler..."
python3 scripts/schedule_hoch_pods.py

echo "6. Running Autonomous Cadence Check..."
python3 scripts/has_autonomous_cadence.py || true

echo "=================================================="
echo "[SUCCESS] Freshness cascade complete."
echo "=================================================="
