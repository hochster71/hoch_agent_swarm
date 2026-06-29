#!/usr/bin/env bash
set -euo pipefail

echo "==> Running Meta-Orchestrator Prevention Gates..."

# Trigger fresh collection pass first
COLLECT_DATA=$(curl -s -X POST http://127.0.0.1:8000/api/v1/runtime-truth/collect)

# Fetch telemetry signals via state endpoint
STATE_DATA=$(curl -s http://127.0.0.1:8000/api/v1/runtime-truth/state)
MAP_DATA=$(curl -s http://127.0.0.1:8000/api/v1/runtime-truth/source-map)

# Helper function to get signal value
get_signal_value() {
  local signal_id=$1
  echo "$STATE_DATA" | jq -r ".signals[] | select(.signal_id == \"$signal_id\") | .value"
}

# Fetch crucial metrics
COVERAGE_SCORE=$(get_signal_value "domain_coverage_score" | tr -d '%')
OWNERLESS_COUNT=$(get_signal_value "ownerless_domain_count")
CRITICAL_GAPS=$(get_signal_value "critical_gap_count")
LOAD_SCORE=$(get_signal_value "michael_orchestration_load")
READINESS_SCORE=$(echo "$COLLECT_DATA" | jq -r ".readiness.score")

echo "  [domain_coverage_gate]: Score is ${COVERAGE_SCORE}%"
echo "  [ownerless_domain_gate]: Count is ${OWNERLESS_COUNT}"
echo "  [operator_load_gate]: Operator load score is ${LOAD_SCORE}"
echo "  [readiness_gate]: Current readiness score is ${READINESS_SCORE}"

# 1. Check if critical_gap_count > 0 and report says no blockers / readiness is 100
if [ "$CRITICAL_GAPS" -gt 0 ]; then
  if [ "$READINESS_SCORE" = "100" ] || [ "$READINESS_SCORE" = "100.0" ]; then
    echo "ERROR: Gate violation: critical_gap_count > 0 but readiness score is 100!"
    exit 1
  fi
fi

# 2. Check if ownerless_domain_count > 10 and orchestration load is LOW
if [ "$OWNERLESS_COUNT" -gt 10 ] && [ "$LOAD_SCORE" != "HIGH" ]; then
  echo "ERROR: Gate violation: ownerless_domain_count > 10 but orchestration load is $LOAD_SCORE (expected HIGH)!"
  exit 1
fi

# 3. Check if #view-meta-orchestrator is missing in frontend/index.html
if ! grep -q "view-meta-orchestrator" frontend/index.html; then
  echo "ERROR: Gate violation: view-meta-orchestrator UI container is missing from frontend/index.html!"
  exit 1
fi

# 4. Check if Runtime Truth lacks meta-orchestrator signals
if ! echo "$STATE_DATA" | jq -e '.signals[] | select(.signal_id == "meta_orchestrator_status")' > /dev/null; then
  echo "ERROR: Gate violation: Runtime Truth lacks meta-orchestrator signals!"
  exit 1
fi

# 5. Check if source map lacks meta-orchestrator entries
if ! echo "$MAP_DATA" | jq -e '.source_map[] | select(.key == "meta_orchestrator_status")' > /dev/null; then
  echo "ERROR: Gate violation: Source map lacks meta-orchestrator entries!"
  exit 1
fi

# 6. Legacy validation checks
MISSING_LIFECYCLES=$(get_signal_value "missing_lifecycle_count")
MISSING_BUSINESS=$(get_signal_value "missing_business_function_count")
BRIEF_STATUS=$(get_signal_value "daily_brief_status")

if [ "$BRIEF_STATUS" != "PASS" ]; then
  echo "ERROR: daily brief status is not PASS"
  exit 1
fi

echo "SUCCESS: All Meta-Orchestrator Prevention Gates passed."
exit 0
