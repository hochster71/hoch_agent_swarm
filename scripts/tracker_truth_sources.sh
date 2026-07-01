#!/bin/bash
set -euo pipefail

export TRACKER_PORT=${TRACKER_PORT:-3001}
export UI_USER=${UI_USER:-admin}
export UI_PASS=${UI_PASS:-change-this-password}

URL="http://localhost:$TRACKER_PORT/api/truth-sources"

if command -v jq >/dev/null 2>&1; then
  curl -s -u "$UI_USER:$UI_PASS" "$URL" | jq .
else
  curl -s -u "$UI_USER:$UI_PASS" "$URL"
fi
