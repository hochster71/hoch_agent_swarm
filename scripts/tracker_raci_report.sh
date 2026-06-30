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
echo "RACI GOVERNANCE REPORT"
echo "=================================================="

URL="http://localhost:$TRACKER_PORT/api/raci"
RESPONSE=$(curl -s -u "$UI_USER:$UI_PASS" "$URL")

# Check if unauthorized or failed
if [ -z "$RESPONSE" ] || echo "$RESPONSE" | grep -q "Unauthorized"; then
    echo "ERROR: Fetch failed or Unauthorized. Check credentials."
    exit 1
fi

echo "$RESPONSE" | node -e '
  const fs = require("fs");
  const data = JSON.parse(fs.readFileSync(0, "utf-8"));
  const summary = data.coverage_summary;
  console.log("Total Workstream & Task Rows:  " + summary.total_rows);
  console.log("Valid Rows:                   " + summary.valid_rows_count);
  console.log("Invalid Rows:                 " + summary.invalid_rows_count);
  console.log("RACI Coverage:                " + summary.coverage_percent + "%");
  console.log("--------------------------------------------------");
  console.log("Violations by Severity:");
  console.log("  • P0 (Critical Blocks):     " + summary.p0_count);
  console.log("  • P1 (Security/QA Gaps):    " + summary.p1_count);
  console.log("  • P2 (Missed Optimization): " + summary.p2_count);
  console.log("--------------------------------------------------");
  console.log("Active Governance Violations:");
  if (data.violations.length === 0) {
    console.log("  None. All systems compliant.");
  } else {
    data.violations.forEach((v, idx) => {
      console.log(`  ${idx+1}. [${v.severity}] Task ${v.task_id}: ${v.message}`);
    });
  }
  console.log("--------------------------------------------------");
  console.log("Top Recommendations:");
  data.recommendations.forEach(r => {
    console.log("  • " + r);
  });
  console.log("--------------------------------------------------");
  console.log("QA Gate Impact:               " + data.qa_gate_impact.impact_level);
  console.log("Reason:                       " + data.qa_gate_impact.reason);
'
