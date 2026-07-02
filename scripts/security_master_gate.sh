#!/usr/bin/env bash
# =============================================================================
# security_master_gate.sh
# Validates and enforces cybersecurity scanning pass thresholds.
# =============================================================================
set -euo pipefail

echo "==> Running Security Master Gate..."

RUN_ID=$(cat data/runtime_scenarios/latest_run_id)

python3 scripts/security_scan_aggregate_gate.py "$RUN_ID"

SUMMARY_FILE="data/security_scans/${RUN_ID}/security_summary.json"

if [ ! -f "$SUMMARY_FILE" ]; then
  echo "❌ FAIL: Security summary file '$SUMMARY_FILE' does not exist."
  exit 1
fi

RESULT=$(jq -r '.overall_result' "$SUMMARY_FILE" 2>/dev/null || echo "FAIL")

echo "==> Security Master Gate result: $RESULT"

if [ "$RESULT" != "PASS" ]; then
  echo "❌ FAIL: Security Master Gate thresholds not met. Audit summary:"
  jq . "$SUMMARY_FILE"
  exit 1
fi

echo "✅ Security Master Gate Passed."
exit 0
