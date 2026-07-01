#!/bin/bash
# scripts/rc44_epic_fury_flowchart_verify.sh — Comprehensive verification cascade for RC44
set -e

# Make sure we're in the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo "============================================="
# Make sure we print exactly RC44
echo "RC44: Verification of Epic Fury Audit and dynamic Flowchart"
echo "============================================="

# Ensure backend server is running on 8765
echo "Checking if PERT cockpit server is running..."
if ! curl -s -m 2 http://127.0.0.1:8765/ >/dev/null; then
    echo "Starting PERT cockpit server in background..."
    uv run python -m uvicorn backend.pert_server:app --host 127.0.0.1 --port 8765 > /tmp/pert_server_verify.log 2>&1 &
    SERVER_PID=$!
    # Wait for server to boot
    sleep 3
else
    echo "PERT cockpit server is already running."
fi

# Run the python compliance audit script
echo "Running Epic Fury full code audit..."
uv run python scripts/epic_fury_full_audit.py

# Check that the evidence files exist
echo "Checking evidence documents..."
if [ -f "docs/evidence/business/epic-fury-full-code-audit.md" ] && \
   [ -f "has_live_project_tracker/data/epic_fury_audit_results.json" ]; then
    echo "  [PASS] Audit evidence and JSON results found."
else
    echo "  [FAIL] Missing audit report or results JSON!"
    exit 1
fi

# Run the Playwright spec
echo "Running Playwright E2E verification test..."
npx playwright test tests/e2e/rc44-epic-fury-flowchart.spec.ts

echo "============================================="
echo "RC44 Verification complete: PASS"
echo "============================================="

# Clean up server if we started it
if [ ! -z "$SERVER_PID" ]; then
    echo "Stopping the background PERT cockpit server..."
    kill $SERVER_PID
fi
