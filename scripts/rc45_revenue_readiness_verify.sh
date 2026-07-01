#!/usr/bin/env bash
# scripts/rc45_revenue_readiness_verify.sh
# Verification runner for RC45 Multi-Project Revenue Readiness Control Plane.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC45: Verification of Revenue Readiness Control Plane"
echo "============================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check if PERT cockpit server is running
SERVER_PID=""
if ! curl -s -m 2 http://127.0.0.1:8765/ >/dev/null; then
    echo "Starting PERT cockpit server in background..."
    uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc45.log 2>&1 &
    SERVER_PID=$!
    sleep 3
else
    echo "PERT cockpit server is already running."
fi

# Cleanup handler to stop server on exit
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping the background PERT cockpit server..."
        kill -9 "$SERVER_PID" || true
    fi
}
trap cleanup EXIT

# 1. Run full codebase revenue readiness audit
echo "Running project revenue readiness audit..."
python3 scripts/project_revenue_readiness_audit.py

# 2. Check evidence documents existence
echo "Checking registry results and evidence documents..."
if [ ! -f "has_live_project_tracker/data/project_revenue_readiness_results.json" ]; then
    echo "  [FAIL] project_revenue_readiness_results.json not found!"
    exit 1
fi
if [ ! -f "docs/evidence/business/project-revenue-readiness-audit.md" ]; then
    echo "  [FAIL] project-revenue-readiness-audit.md evidence report not found!"
    exit 1
fi
echo "  [PASS] Revenue readiness registry data and reports exist."

# 3. Run Playwright E2E verification test
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc45-revenue-readiness.spec.ts --reporter=list

echo "============================================="
echo "RC45 Verification complete: PASS"
echo "============================================="
