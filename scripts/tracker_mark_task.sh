#!/bin/bash
set -e

if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <task_id> <status> [blocker_reason]"
    echo "Example: $0 T004 Running"
    echo "Example: $0 T004 Blocked \"Pending Stripe API approval\""
    exit 1
fi

TASK_ID="$1"
STATUS="$2"
BLOCKER="$3"

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
echo "MARKING TASK STATUS"
echo "=================================================="
echo "Task ID: $TASK_ID"
echo "Status:  $STATUS"
if [ -n "$BLOCKER" ]; then
    echo "Blocker: $BLOCKER"
fi

# Prepare payload
if [ -n "$BLOCKER" ]; then
    PAYLOAD="{\"id\": \"$TASK_ID\", \"status\": \"$STATUS\", \"blocker\": \"$BLOCKER\"}"
else
    PAYLOAD="{\"id\": \"$TASK_ID\", \"status\": \"$STATUS\"}"
fi

RESPONSE=$(curl -s -u "$UI_USER:$UI_PASS" \
  -H "Content-Type: application/json" \
  -X POST \
  -d "$PAYLOAD" \
  "http://localhost:$TRACKER_PORT/api/mark")

echo "Response: $RESPONSE"
