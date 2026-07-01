#!/usr/bin/env bash
# scripts/rc48_hoch_pods_architecture_verify.sh
# Verification runner for RC48: HOCH PODS Secure Runtime Architecture and Animated Pod Theater.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC48: Verification of HOCH PODS Architecture & Theater"
echo "============================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

SERVER_PID=""

# Cleanup handler
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping the background PERT cockpit server..."
        kill -9 "$SERVER_PID" || true
    fi
}
trap cleanup EXIT

# 1. Compile HOCH PODS runtime state
echo "Compiling HOCH PODS runtime state..."
python3 scripts/generate_hoch_pods_runtime_state.py

# 2. Check architecture & compliance documents exist
echo "Checking compliance and architecture documentation..."
docs=(
    "docs/architecture/hoch-pods-secure-agent-runtime-architecture.md"
    "docs/architecture/hoch-pods-compliant-topology.md"
    "docs/security/hoch-pods-control-mapping.md"
    "docs/evidence/runtime/hoch-pods-runtime-evidence.md"
)

for doc in "${docs[@]}"; do
    if [ ! -f "$doc" ]; then
        echo "  [FAIL] Document $doc is missing!"
        exit 1
    fi
    echo "  [PASS] Found: $doc"
done

# 3. Check data files exist
data_files=(
    "has_live_project_tracker/data/hoch_pods_registry.json"
    "has_live_project_tracker/data/hoch_pods_runtime_state.json"
)

for df in "${data_files[@]}"; do
    if [ ! -f "$df" ]; then
        echo "  [FAIL] Data file $df is missing!"
        exit 1
    fi
    echo "  [PASS] Found: $df"
done

# 4. Check if PERT cockpit server is running
if ! curl -s -m 2 http://127.0.0.1:8765/ >/dev/null; then
    echo "Starting PERT cockpit server in background..."
    uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc48.log 2>&1 &
    SERVER_PID=$!
    sleep 3
else
    echo "PERT cockpit server is already running."
fi

# 5. Run Playwright E2E verification test
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc48-hoch-pods-architecture.spec.ts --reporter=list

echo "============================================="
echo "RC48 Verification complete: PASS"
echo "============================================="
