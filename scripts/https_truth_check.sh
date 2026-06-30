#!/usr/bin/env bash
# https_truth_check.sh - Verifies HTTPS reverse proxy routing to API and UI services

set -euo pipefail

# Verify and pin Docker context based on responsiveness
if docker --context default ps >/dev/null 2>&1; then
  docker context use default >/dev/null
elif docker --context desktop-linux ps >/dev/null 2>&1; then
  docker context use desktop-linux >/dev/null
else
  docker context use default >/dev/null || true
fi

echo "==> Running HTTPS UI/API Truth Alignment Check..."

API_HTTPS_URL="https://has.localhost/api/v1/runtime-truth/state"
UI_HTTPS_URL="https://has.localhost/"

# Query API via HTTPS resolving has.localhost locally and bypassing TLS warnings
echo "Fetching Runtime Truth State via HTTPS from $API_HTTPS_URL..."
api_res=$(curl -sS --fail -k --resolve has.localhost:443:127.0.0.1 "$API_HTTPS_URL")
if ! echo "$api_res" | grep -F "disk_space" >/dev/null; then
  echo "❌ FAIL: API did not return expected runtime truth signals via HTTPS!"
  exit 1
fi
echo "  [OK] API responded successfully over HTTPS."

# Query UI via HTTPS resolving has.localhost locally and bypassing TLS warnings
echo "Fetching UI via HTTPS from $UI_HTTPS_URL..."
ui_res=$(curl -sS --fail -k --resolve has.localhost:443:127.0.0.1 "$UI_HTTPS_URL")
if ! echo "$ui_res" | grep -i "Hoch Agent Swarm" >/dev/null; then
  echo "❌ FAIL: UI dashboard did not return expected page content via HTTPS!"
  exit 1
fi
echo "  [OK] UI responded successfully over HTTPS."

echo "[PASS] HTTPS routing truth alignments successfully verified."
exit 0
