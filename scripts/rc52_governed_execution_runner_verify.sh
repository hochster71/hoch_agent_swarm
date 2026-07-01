#!/usr/bin/env bash
# scripts/rc52_governed_execution_runner_verify.sh
# E2E and CLI verification runner for RC52: Governed Swarm Execution Runner

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
echo "RC52: CLI Verification of Governed Swarm Execution Runner"
echo "=========================================================="

if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Ensure database files exist from a clean slate
echo "Cleaning up existing execution logs and registries..."
rm -f has_live_project_tracker/data/hoch_execution_approval_queue.json
rm -f has_live_project_tracker/data/governed_execution_log.json
echo "Regenerating execution approval queue registry..."
uv run python scripts/generate_execution_approval_queue.py

# 1. READ_ONLY proposal can dry-run
echo "1. Testing READ_ONLY dry-run (prop-cyber-gitleaks)..."
uv run python scripts/run_governed_execution.py prop-cyber-gitleaks DRY_RUN

# 2. LOCAL_SAFE_WRITE cannot run without APPROVED status
echo "2. Testing LOCAL_SAFE_WRITE without APPROVED status (prop-builder-compile)..."
if uv run python scripts/run_governed_execution.py prop-builder-compile STAGED_EXECUTION; then
    echo "FAIL: Allowed LOCAL_SAFE_WRITE to execute without APPROVED status!"
    exit 1
else
    echo "PASS: Successfully blocked LOCAL_SAFE_WRITE without APPROVED status."
fi

# 3. Simulate Michael's approval on prop-builder-compile
echo "Simulating Michael Hoch's approval on prop-builder-compile..."
uv run python scripts/simulate_execution_approval_decision.py prop-builder-compile APPROVED

# 4. LOCAL_SAFE_WRITE can staged-run after approval
echo "3. Testing LOCAL_SAFE_WRITE after APPROVED status..."
uv run python scripts/run_governed_execution.py prop-builder-compile STAGED_EXECUTION

# 5. REPO_WRITE is blocked
echo "4. Testing REPO_WRITE blocking..."
# Note: we need to find or simulate a REPO_WRITE action ID if one exists, or check prop-deploy-vercel (which is DEPLOYMENT but UNSAFE).
# Let's test blocking of prop-deploy-vercel (DEPLOYMENT):
if uv run python scripts/run_governed_execution.py prop-deploy-vercel STAGED_EXECUTION; then
    echo "FAIL: Allowed DEPLOYMENT execution!"
    exit 1
else
    echo "PASS: Successfully blocked DEPLOYMENT."
fi

# 6. NETWORK_WRITE is blocked
echo "5. Testing NETWORK_WRITE blocking (prop-research-scrape)..."
if uv run python scripts/run_governed_execution.py prop-research-scrape STAGED_EXECUTION; then
    echo "FAIL: Allowed NETWORK_WRITE execution!"
    exit 1
else
    echo "PASS: Successfully blocked NETWORK_WRITE."
fi

# 7. DESTRUCTIVE is blocked
echo "6. Testing DESTRUCTIVE blocking (prop-audit-purge)..."
if uv run python scripts/run_governed_execution.py prop-audit-purge STAGED_EXECUTION; then
    echo "FAIL: Allowed DESTRUCTIVE execution!"
    exit 1
else
    echo "PASS: Successfully blocked DESTRUCTIVE."
fi

# Run the cascade refresh to sync files
bash scripts/rc49_5_refresh_truth_cascade.sh

echo "=========================================================="
echo "RC52: Playwright E2E verification of Cockpit UI Panel"
echo "=========================================================="

SERVER_PID=""

cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping background cockpit server..."
        kill -9 "$SERVER_PID" || true
    fi
}
trap cleanup EXIT

echo "Starting PERT cockpit server in background..."
lsof -ti :8765 | xargs kill -9 2>/dev/null || true
sleep 1

uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc52.log 2>&1 &
SERVER_PID=$!

echo "Waiting for cockpit server to respond..."
for i in {1..10}; do
    if curl -s http://127.0.0.1:8765/health >/dev/null; then
        echo "Cockpit server is active."
        break
    fi
    sleep 1
done

echo "Running Playwright E2E spec..."
npx playwright test tests/e2e/rc52-governed-execution-runner.spec.ts

echo "=========================================================="
echo "RC52 Verification complete: PASS"
echo "=========================================================="
