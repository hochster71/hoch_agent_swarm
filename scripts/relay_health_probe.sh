#!/usr/bin/env bash
# scripts/relay_health_probe.sh
# Performs a safe health check probe on the Tailscale private relay IP.
# Writes a structured evidence JSON to has_live_project_tracker/data/relay_probe_evidence.json.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_FILE="$PROJECT_ROOT/has_live_project_tracker/data/relay_probe_evidence.json"

echo "=================================================="
echo "RUNNING SAFE RELAY HEALTH PROBE (RC41)"
echo "=================================================="

# Check if target is reachable
TARGET_URL="http://100.87.18.15:3012/health"
echo "Probing $TARGET_URL..."

RESPONSE=$(curl -fsS --connect-timeout 5 "$TARGET_URL")

if [ $? -eq 0 ] && [ ! -z "$RESPONSE" ]; then
    echo "  [PASS] Relay health probe succeeded: $RESPONSE"
    
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Write structured JSON evidence file
    cat <<EOF > "$OUTPUT_FILE"
{
  "worker_id": "hoch-relay-001",
  "status": "ONLINE",
  "last_probe_time": "$TIMESTAMP",
  "data_source": "relay_health_probe",
  "confidence": 0.95,
  "freshness": "0.0",
  "response": $RESPONSE,
  "evidence_file": "has_live_project_tracker/data/relay_probe_evidence.json"
}
EOF
    echo "Evidence written to $OUTPUT_FILE"
else
    echo "  [FAIL] Health probe failed!"
    exit 1
fi
