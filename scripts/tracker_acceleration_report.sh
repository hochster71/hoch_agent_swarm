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
echo "PRODUCTION ACCELERATION REPORT"
echo "=================================================="

URL="http://localhost:$TRACKER_PORT/api/acceleration"
RESPONSE=$(curl -s -u "$UI_USER:$UI_PASS" "$URL")

# Check if unauthorized or failed
if [ -z "$RESPONSE" ] || echo "$RESPONSE" | grep -q "Unauthorized"; then
    echo "ERROR: Fetch failed or Unauthorized. Check credentials."
    exit 1
fi

echo "$RESPONSE" | node -e '
  const fs = require("fs");
  const data = JSON.parse(fs.readFileSync(0, "utf-8"));
  console.log("Acceleration Verdict:   " + data.verdict);
  console.log("Remaining Hours:        " + data.remaining_hours + "h");
  console.log("Est. Hours Saved:       " + data.estimated_hours_saved + "h");
  console.log("--------------------------------------------------");
  console.log("Top Downstream Unlocks:");
  data.top_unlocks.forEach(u => {
    console.log("  • " + u.id + ": " + u.name + " (unlocks " + u.downstream_count + " downstream tasks)");
  });
  console.log("--------------------------------------------------");
  console.log("Safe Parallel Swarm Batch:");
  data.safe_parallel_batch.forEach(t => {
    console.log("  • " + t.id + ": " + t.name + " (" + t.expected_hours + "h) -> Assigned: " + t.assigned_agent);
  });
  console.log("--------------------------------------------------");
  console.log("Stale Running Tasks:");
  if (data.stale_running_tasks.length === 0) {
    console.log("  None.");
  } else {
    data.stale_running_tasks.forEach(t => {
      console.log("  • " + t.id + ": " + t.name + " (Running for >" + t.stale_after_seconds + "s)");
    });
  }
  console.log("--------------------------------------------------");
  console.log("Next 3 Highest-Leverage Actions:");
  data.next_3_actions.forEach(a => {
    console.log("  • " + a);
  });
'
