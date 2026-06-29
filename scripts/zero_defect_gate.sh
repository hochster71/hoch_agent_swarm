#!/usr/bin/env bash
set -euo pipefail

echo "==> Running Zero-Defect Control Plane Gates..."

# 1. Run basic compilation and E2E suites
echo "Running npm run build..."
npm run build

echo "Running Python pytest suite..."
uv run pytest

echo "Running Playwright E2E specs..."
npx playwright test

echo "Running Anti-Fake Gate..."
bash scripts/anti_fake_gate.sh

echo "Running Hardcoded Status Scan..."
bash scripts/scan_hardcoded_status.sh

# 2. Fetch defect and warning telemetry via truth state endpoint
STATE_DATA=$(curl -s http://127.0.0.1:8000/api/v1/runtime-truth/state)

get_signal_value() {
  local signal_id=$1
  echo "$STATE_DATA" | jq -r ".signals[] | select(.signal_id == \"$signal_id\") | .value"
}

OPEN_DEFECTS=$(get_signal_value "open_defect_count" || echo "0")
CRITICAL_DEFECTS=$(get_signal_value "critical_defect_count" || echo "0")
NEW_WARNINGS=$(get_signal_value "new_warning_count" || echo "0")
HIGH_VULNS=$(get_signal_value "high_vulnerability_count" || echo "0")
UNOWNED_DEFECTS=$(get_signal_value "unowned_defect_count" || echo "0")

echo "  [zero_defect_gate]: Open Defects: $OPEN_DEFECTS"
echo "  [zero_defect_gate]: Critical Defects: $CRITICAL_DEFECTS"
echo "  [zero_defect_gate]: New Warnings: $NEW_WARNINGS"
echo "  [zero_defect_gate]: High Vulnerabilities: $HIGH_VULNS"
echo "  [zero_defect_gate]: Unowned Defects: $UNOWNED_DEFECTS"

# 3. Assert zero-defect state rules
if [ "$CRITICAL_DEFECTS" -gt 0 ]; then
  echo "ERROR: zero_defect_gate failed: $CRITICAL_DEFECTS critical defects remain unresolved!"
  exit 1
fi

if [ "$NEW_WARNINGS" -gt 0 ]; then
  echo "ERROR: zero_defect_gate failed: $NEW_WARNINGS new warnings detected!"
  exit 1
fi

if [ "$HIGH_VULNS" -gt 0 ]; then
  echo "ERROR: zero_defect_gate failed: $HIGH_VULNS high severity vulnerabilities remain unresolved!"
  exit 1
fi

if [ "$UNOWNED_DEFECTS" -gt 0 ]; then
  echo "ERROR: zero_defect_gate failed: $UNOWNED_DEFECTS unowned defects remain!"
  exit 1
fi

echo "SUCCESS: Zero-Defect Control Plane Gates passed successfully."
exit 0
