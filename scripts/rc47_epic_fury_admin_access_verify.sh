#!/usr/bin/env bash
# scripts/rc47_epic_fury_admin_access_verify.sh
# Verification runner for RC47: Epic Fury Admin Access, Founder Entitlement, and Internal Preview Mode.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "RC47: Verification of Epic Fury Admin Access"
echo "============================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

EPIC_FURY_DIR="/Users/michaelhoch/epic-fury-build/epic-fury-2026"
EPIC_PID=""
SERVER_PID=""

# Cleanup handler
cleanup() {
    if [ -n "$EPIC_PID" ]; then
        echo "Stopping the background Epic Fury server..."
        kill -9 "$EPIC_PID" || true
    fi
    if [ -n "$SERVER_PID" ]; then
        echo "Stopping the background PERT cockpit server..."
        kill -9 "$SERVER_PID" || true
    fi
}
trap cleanup EXIT

# 1. Start Epic Fury in background on port 3003 with preview variables active
echo "Starting Epic Fury Next.js app in background..."
cd "$EPIC_FURY_DIR"
EPIC_FURY_INTERNAL_PREVIEW_ENABLED=true \
EPIC_FURY_ADMIN_EMAILS=michael.b.hoch@gmail.com \
EPIC_FURY_QA_EMAILS=qa@example.com \
EPIC_FURY_STRIPE_TEST_MODE=true \
NEXT_PUBLIC_EPIC_FURY_INTERNAL_PREVIEW_ENABLED=true \
NEXT_PUBLIC_EPIC_FURY_STRIPE_TEST_MODE=true \
npm run dev > /tmp/epic_fury_dev_rc47.log 2>&1 &
EPIC_PID=$!

echo "Waiting for Epic Fury server to boot..."
sleep 6

# Return to project root
cd "$PROJECT_ROOT"

# 2. Check if PERT cockpit server is running
if ! curl -s -m 2 http://127.0.0.1:8765/ >/dev/null; then
    echo "Starting PERT cockpit server in background..."
    uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_rc47.log 2>&1 &
    SERVER_PID=$!
    sleep 3
else
    echo "PERT cockpit server is already running."
fi

# 3. Run project revenue readiness audit
echo "Running project revenue readiness audit..."
python3 scripts/project_revenue_readiness_audit.py

# 4. Run revenue action queue generator
echo "Running revenue action queue generator..."
python3 scripts/generate_revenue_action_queue.py

# 5. Check evidence files existence
echo "Checking results and evidence documents..."
if [ ! -f "docs/evidence/business/epic-fury-admin-access-audit.md" ]; then
    echo "  [FAIL] epic-fury-admin-access-audit.md not found!"
    exit 1
fi
echo "  [PASS] Admin access audit evidence report exists."

# 6. Run Playwright E2E verification test
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc47-epic-fury-admin-access.spec.ts --reporter=list

echo "============================================="
echo "RC47 Verification complete: PASS"
echo "============================================="
