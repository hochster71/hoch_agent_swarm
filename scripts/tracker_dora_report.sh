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
echo "DORA METRICS REPORT"
echo "=================================================="

URL="http://localhost:$TRACKER_PORT/api/dora"
RESPONSE=$(curl -s -u "$UI_USER:$UI_PASS" "$URL")

# Check if unauthorized or failed
if [ -z "$RESPONSE" ] || echo "$RESPONSE" | grep -q "Unauthorized"; then
    echo "ERROR: Fetch failed or Unauthorized. Check credentials."
    exit 1
fi

echo "$RESPONSE" | node -e '
  const fs = require("fs");
  const data = JSON.parse(fs.readFileSync(0, "utf-8"));
  console.log("Change Lead Time:       " + data.metrics.change_lead_time_hours + "h");
  console.log("Deployment Frequency:   " + data.metrics.deployment_frequency_7d + " (last 7 days)");
  console.log("Time to Restore Service: " + data.metrics.failed_deployment_recovery_time_hours + "h");
  console.log("Change Fail Rate:       " + data.metrics.change_fail_rate_percent + "%");
  console.log("Deployment Rework Rate: " + data.metrics.deployment_rework_rate_percent + "%");
  console.log("--------------------------------------------------");
  console.log("Total Events Logged:    " + data.events_count);
  console.log("Valid Events Count:     " + data.valid_events_count);
  console.log("Missing Telemetry:      " + (data.missing_fields.join(", ") || "None"));
  console.log("Unknown Metrics:        " + (data.unknown_metrics.join(", ") || "None"));
  console.log("Recommendations:        " + data.recommendations.join(" | "));
'
