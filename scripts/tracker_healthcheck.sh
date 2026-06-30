#!/bin/bash
set -euo pipefail

# Load secrets if present
SECRETS_FILE="$HOME/.hoch-secrets/has-tracker.env"
if [ -f "$SECRETS_FILE" ]; then
    set -a
    source "$SECRETS_FILE"
    set +a
fi

export TRACKER_PORT=${TRACKER_PORT:-3001}
export UI_USER=${TRACKER_USER:-${UI_USER:-admin}}
export UI_PASS=${TRACKER_PASSWORD:-${UI_PASS:-change-this-password}}

echo "=================================================="
echo "RUNNING FULL TRACKER HEALTH CHECK"
echo "=================================================="

ENDPOINTS=(
  "/api/health"
  "/api/truth"
  "/api/truth-sources"
  "/api/status"
  "/api/tasks"
  "/api/landscape"
  "/api/gaps"
  "/api/disk"
  "/api/dora"
  "/api/acceleration"
  "/api/raci"
  "/api/raci-heatmap"
)

FAILED=0

for EP in "${ENDPOINTS[@]}"; do
  URL="http://localhost:$TRACKER_PORT$EP"
  echo -n "Checking $EP... "
  STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "$UI_USER:$UI_PASS" "$URL" || echo "000")
  if [ "$STATUS_CODE" -eq 200 ]; then
    echo "[PASS] (200)"
  else
    echo "[FAIL] ($STATUS_CODE)"
    FAILED=$((FAILED + 1))
  fi
done

if [ "$FAILED" -eq 0 ]; then
  echo "=================================================="
  echo "[PASS] All tracker endpoints healthy."
  echo "=================================================="
  exit 0
else
  echo "=================================================="
  echo "[FAIL] $FAILED tracker endpoints failed."
  echo "=================================================="
  exit 1
fi
