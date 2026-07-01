#!/bin/bash
# Helper script to post events from inside Kubernetes pods to the host tracker server
set -euo pipefail

TYPE="${1:-heartbeat}"
SOURCE="${2:-agent_swarm}"
TARGET="${3:-global_registry}"
SEVERITY="${4:-info}"
STATUS="${5:-success}"
SUMMARY="${6:-K8s sidecar event}"
EVIDENCE_PATH="${7:-}"

HOST="${TRACKER_HOST:-host.k3d.internal}"
PORT="${TRACKER_PORT:-3001}"
USER="${TRACKER_USER:-admin}"
PASSWORD="${TRACKER_PASSWORD:-change-this-password}"

PAYLOAD=$(cat <<EOF
{
  "type": "$TYPE",
  "source": "$SOURCE",
  "target": "$TARGET",
  "domain": "Runtime",
  "severity": "$SEVERITY",
  "status": "$STATUS",
  "payload_summary": "$SUMMARY",
  "evidence_path": ${EVIDENCE_PATH:+"\"$EVIDENCE_PATH\""}
}
EOF
)

# Replace newlines with spaces for raw JSON string
PAYLOAD=$(echo "$PAYLOAD" | tr -d '\n')

echo "Posting event to http://$HOST:$PORT/api/event..."

curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -u "$USER:$PASSWORD" \
  -d "$PAYLOAD" \
  "http://$HOST:$PORT/api/event" || echo "Warning: Failed to reach host tracker api"
