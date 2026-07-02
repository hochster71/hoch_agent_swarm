#!/usr/bin/env bash
# =============================================================================
# remote_first_gate.sh
# Verifies that HAS/HASF is running in a remote-first, monitored posture.
# =============================================================================
set -euo pipefail

echo "==> Running Remote-First Posture Gate..."

TARGET_IP="50.116.41.183"
TAILSCALE_IP="100.87.18.15"

# 1. Probing Tailscale ping to verify remote tunnel is up
if ! ping -c 1 -t 3 "$TAILSCALE_IP" &>/dev/null; then
  echo "❌ FAIL: Tailscale tunnel to remote host is unreachable."
  exit 1
fi

# 2. Querying remote health endpoint to verify active daemon status
HEALTH_STATUS=$(curl -sS --connect-timeout 5 "http://${TAILSCALE_IP}:3012/health" 2>/dev/null || echo "FAILED")

if [[ "$HEALTH_STATUS" == "FAILED" ]] || [[ "$HEALTH_STATUS" != *"status"* ]]; then
  echo "❌ FAIL: Remote Docker API service is offline or unreachable."
  exit 1
fi

# 3. Verify that public ports are securely blocked (no public exposure)
PUBLIC_PROBE=$(curl -sS --connect-timeout 3 "http://${TARGET_IP}:3012" 2>&1 || echo "TIMEOUT")
if [[ "$PUBLIC_PROBE" != *"TIMEOUT"* ]] && [[ "$PUBLIC_PROBE" != *"Failed to connect"* ]]; then
  echo "❌ FAIL: Security Violation: Public port 3012 is exposed to the internet!"
  exit 1
fi

echo "✅ Remote-First Posture Gate Passed (monitored remote state active)."
exit 0
