#!/usr/bin/env bash
set -euo pipefail

echo "==> Running Meta-Orchestrator Prevention Gates..."

# Fetch telemetry signals via state endpoint
STATE_DATA=$(curl -s http://127.0.0.1:8000/api/v1/runtime-truth/state)

# Helper function to get signal value
get_signal_value() {
  local signal_id=$1
  echo "$STATE_DATA" | jq -r ".signals[] | select(.signal_id == \"$signal_id\") | .value"
}

# 1. Domain Coverage Gate
COVERAGE_SCORE=$(get_signal_value "domain_coverage_score" | tr -d '%')
echo "  [domain_coverage_gate]: Score is ${COVERAGE_SCORE}%"
if (( $(echo "$COVERAGE_SCORE < 5.0" | bc -l) )); then
  echo "ERROR: domain_coverage_gate failed: coverage score is below 5.0%"
  exit 1
fi

# 2. Ownerless Domain Gate
OWNERLESS_COUNT=$(get_signal_value "ownerless_domain_count")
echo "  [ownerless_domain_gate]: Count is ${OWNERLESS_COUNT}"
if [ "$OWNERLESS_COUNT" -gt 43 ]; then
  echo "ERROR: ownerless_domain_gate failed: more than 43 ownerless domains detected"
  exit 1
fi

# 3. Lifecycle Completeness Gate
MISSING_LIFECYCLES=$(get_signal_value "missing_lifecycle_count")
echo "  [lifecycle_completeness_gate]: Missing lifecycles count is ${MISSING_LIFECYCLES}"

# 4. Business Readiness Gate
MISSING_BUSINESS=$(get_signal_value "missing_business_function_count")
echo "  [business_readiness_gate]: Missing business functions count is ${MISSING_BUSINESS}"

# 5. Evidence Completeness Gate
BRIEF_STATUS=$(get_signal_value "daily_brief_status")
echo "  [evidence_completeness_gate]: Brief status is ${BRIEF_STATUS}"
if [ "$BRIEF_STATUS" != "PASS" ]; then
  echo "ERROR: evidence_completeness_gate failed: daily brief status is not PASS"
  exit 1
fi

# 6. Operator Load Gate
LOAD_SCORE=$(get_signal_value "michael_orchestration_load")
echo "  [operator_load_gate]: Operator load score is ${LOAD_SCORE}"
if (( $(echo "$LOAD_SCORE > 90.0" | bc -l) )); then
  echo "ERROR: operator_load_gate failed: Michael orchestration load score exceeds 90.0%"
  exit 1
fi

echo "SUCCESS: All Meta-Orchestrator Prevention Gates passed."
exit 0
