#!/usr/bin/env bash
# =============================================================================
# hasf_revenue_readiness_gate.sh
# Gating script to assert that HASF monetization/revenue targets are satisfied.
# =============================================================================
set -euo pipefail

echo "==> Running HASF Revenue Readiness Gate..."

RESP=$(curl -sS "http://127.0.0.1:8765/api/v1/hasf/revenue-readiness" || echo "FAILED")

if [[ "$RESP" == "FAILED" ]] || [[ "$RESP" != *"hasf_revenue_ready"* ]]; then
  echo "❌ FAIL: Revenue readiness API endpoint is offline or failed."
  exit 1
fi

READY=$(echo "$RESP" | jq -r '.hasf_revenue_ready' 2>/dev/null || echo "false")

echo "HASF Revenue Readiness: ${READY}"

if [ "${READY}" != "true" ]; then
  echo "❌ FAIL: HASF revenue targets not met."
  exit 1
fi

echo "✅ HASF Revenue Readiness Gate Passed."
exit 0
