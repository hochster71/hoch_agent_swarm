#!/usr/bin/env bash
# =============================================================================
# remote_operational_proof_gate.sh
# Validates the final operational constraints for the remote HAS setup.
# =============================================================================
set -uo pipefail

echo "==> Running Remote Operational Proof Gate..."

TARGET_IP="50.116.41.183"
TAILSCALE_IP="100.87.18.15"

# 1. Verify Tailscale tunnel reachability
echo "Probing Tailscale connection to VPS..."
if ! ping -c 1 -t 3 "$TAILSCALE_IP" &>/dev/null; then
  echo "❌ FAIL: Tailscale tunnel to ${TAILSCALE_IP} is unreachable."
  exit 1
fi
echo "✅ Pass: Tailscale IP is reachable."

# 2. Verify public port block
echo "Verifying public ports are blocked..."
PUBLIC_3012_STATUS=$(curl -sS --connect-timeout 3 "http://${TARGET_IP}:3012" 2>&1 || echo "CONNECTION_TIMEOUT")
if [[ "$PUBLIC_3012_STATUS" != *"CONNECTION_TIMEOUT"* ]] && [[ "$PUBLIC_3012_STATUS" != *"Failed to connect"* ]]; then
  echo "❌ FAIL: Security Violation: Public port 3012 is reachable on ${TARGET_IP}!"
  exit 1
fi

PUBLIC_8765_STATUS=$(curl -sS --connect-timeout 3 "http://${TARGET_IP}:8765/ui-moonshot" 2>&1 || echo "CONNECTION_TIMEOUT")
if [[ "$PUBLIC_8765_STATUS" != *"CONNECTION_TIMEOUT"* ]] && [[ "$PUBLIC_8765_STATUS" != *"Failed to connect"* ]]; then
  echo "❌ FAIL: Security Violation: Public port 8765 is reachable on ${TARGET_IP}!"
  exit 1
fi
echo "✅ Pass: Public port access is securely blocked."

# 3. Verify Tailscale service
echo "Checking Moonshot control plane status..."
if ! curl -sS -I --connect-timeout 5 "http://${TAILSCALE_IP}:8765/ui-moonshot" | grep -q "200\|405"; then
  echo "❌ FAIL: Tailscale Moonshot UI endpoint is unreachable."
  exit 1
fi
echo "✅ Pass: Tailscale Moonshot UI endpoint is running."

echo "==> Remote Operational Proof Gate Passed successfully."
exit 0
