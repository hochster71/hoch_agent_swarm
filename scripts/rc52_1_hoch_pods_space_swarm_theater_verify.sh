#!/usr/bin/env bash
# scripts/rc52_1_hoch_pods_space_swarm_theater_verify.sh
# E2E verification runner for RC52.1: HOCH PODS Space Swarm Theater

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
# Prevent fake greening
echo "RC52.1: E2E and Design Verification of Space Swarm Theater"
echo "=========================================================="

if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Ensure telemetry files exist and are refreshed
echo "Refreshing telemetry truth cascade..."
bash scripts/rc49_5_refresh_truth_cascade.sh

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

uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc52_1.log 2>&1 &
SERVER_PID=$!

echo "Waiting for cockpit server to respond..."
for i in {1..15}; do
    if curl -s http://127.0.0.1:8765/health >/dev/null; then
        echo "Cockpit server is active."
        break
    fi
    sleep 1
done

if ! curl -s http://127.0.0.1:8765/health >/dev/null; then
    echo "ERROR: Server failed to start."
    cat /tmp/pert_server_rc52_1.log
    exit 1
fi

echo "Running Space Swarm Theater Playwright E2E spec..."
npx playwright test tests/e2e/rc52_1-hoch-pods-space-swarm-theater.spec.ts

echo "Running Parallel Mirror Integrity Verification..."
uv run python scripts/has_parallel_mirror_verify.py

echo "Running Working Tree Dirty State Verification..."
bash scripts/rc29_release_verify.sh

echo "=========================================================="
echo "RC52.1 Verification complete: PASS"
echo "=========================================================="
