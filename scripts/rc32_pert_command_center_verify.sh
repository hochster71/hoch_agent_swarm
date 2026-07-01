#!/usr/bin/env bash
# ==============================================================================
# scripts/rc32_pert_command_center_verify.sh
# ==============================================================================
# Verifies that the local PERT Command Center on port 8765 is active, 
# responds correctly to API calls, and serves the dashboard HTML.
# ==============================================================================
set -e

PORT=8765
URL="http://127.0.0.1:$PORT"

echo "=================================================="
echo "VERIFYING PERT COMMAND CENTER ON PORT $PORT"
echo "=================================================="

# Check if port is listening
if ! lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[ERROR] PERT Command Center is not running on port $PORT."
    exit 1
fi

echo "[PASS] Port $PORT is listening."

# Check root page status
RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL/")
if [ "$RESPONSE_CODE" -ne 200 ]; then
    echo "[ERROR] Root URL returned HTTP status $RESPONSE_CODE instead of 200."
    exit 1
fi
echo "[PASS] Dashboard HTML page returned HTTP 200."

# Check API endpoint status and structure
API_RESPONSE=$(curl -s "$URL/api/pert/data")
if [ -z "$API_RESPONSE" ]; then
    echo "[ERROR] API returned an empty response."
    exit 1
fi

# Assert JSON properties
echo "$API_RESPONSE" | jq -e '.north_star.baseline' >/dev/null
echo "$API_RESPONSE" | jq -e '.readiness.score' >/dev/null
echo "$API_RESPONSE" | jq -e '.pert_cpm.tasks' >/dev/null
echo "$API_RESPONSE" | jq -e '.agents' >/dev/null
echo "$API_RESPONSE" | jq -e '.next_actions' >/dev/null
echo "$API_RESPONSE" | jq -e '.evidence_ledger' >/dev/null

echo "[PASS] API JSON validation succeeded."
echo "[SUCCESS] PERT Command Center verification passed completely."
exit 0
