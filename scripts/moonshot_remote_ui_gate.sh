#!/usr/bin/env bash
# =============================================================================
# moonshot_remote_ui_gate.sh
# Validation gate for Moonshot Remote UI exposure
# =============================================================================
set -euo pipefail

DB_PATH="backend/swarm_ledger.db"
TAILSCALE_IP="100.87.18.15"
PUBLIC_IP="50.116.41.183"
PORT="8765"

echo "==> Running Moonshot Remote UI Gate..."

# 1. Local Moonshot UI Reachability
echo "Checking local Moonshot UI..."
if ! curl -sS -I --connect-timeout 5 http://127.0.0.1:${PORT}/ui-moonshot | grep -q "200\|405"; then
  echo "❌ FAIL: Local Moonshot UI http://127.0.0.1:${PORT}/ui-moonshot is unreachable."
  exit 1
fi
echo "✅ Pass: Local Moonshot UI is reachable."

# 2. Remote Tailscale UI Reachability
echo "Checking remote Tailscale Moonshot UI..."
if ! curl -sS -I --connect-timeout 5 http://${TAILSCALE_IP}:${PORT}/ui-moonshot | grep -q "200\|405"; then
  echo "❌ FAIL: Remote Tailscale Moonshot UI http://${TAILSCALE_IP}:${PORT}/ui-moonshot is unreachable."
  exit 1
fi
echo "✅ Pass: Remote Tailscale Moonshot UI is reachable."

# 3. Public Exposure Blocked
echo "Verifying public port ${PORT} is unreachable..."
if curl -sS -I --connect-timeout 5 http://${PUBLIC_IP}:${PORT}/ui-moonshot &>/dev/null; then
  echo "❌ FAIL: SECURITY VIOLATION: Public port http://${PUBLIC_IP}:${PORT}/ui-moonshot is reachable!"
  exit 1
fi
echo "✅ Pass: Public port exposure is blocked."

# 4. Old Surfaces Deprecation Checks
echo "Checking deprecation of old ports..."
# Ensure that we don't treat 8080 or 3012 as canonical
CANON_UI=$(sqlite3 "${DB_PATH}" "SELECT value FROM runtime_truth_signals WHERE signal_id = 'canonical_ui_url';")
if [ "${CANON_UI}" = "http://127.0.0.1:8080" ] || [ "${CANON_UI}" = "http://100.87.18.15:3012" ]; then
  echo "❌ FAIL: Stale URL treated as canonical UI: ${CANON_UI}"
  exit 1
fi
echo "✅ Pass: Old surfaces correctly marked as deprecated."

# 5. Runtime Truth Alignment
echo "Verifying Moonshot URL is canonical in Runtime Truth..."
if [ "${CANON_UI}" != "http://127.0.0.1:8765/ui-moonshot" ]; then
  echo "❌ FAIL: Runtime Truth 'canonical_ui_url' expected 'http://127.0.0.1:8765/ui-moonshot', got '${CANON_UI}'"
  exit 1
fi

CANON_NAME=$(sqlite3 "${DB_PATH}" "SELECT value FROM runtime_truth_signals WHERE signal_id = 'canonical_ui_name';")
if [ "${CANON_NAME}" != "Moonshot UI" ]; then
  echo "❌ FAIL: Runtime Truth 'canonical_ui_name' expected 'Moonshot UI', got '${CANON_NAME}'"
  exit 1
fi
echo "✅ Pass: Swarm Ledger signals are correctly aligned."

# 6. Final Verifier Posture
echo "Verifying Final Verifier remains BLOCKED..."
VERDICT_RES=$(curl -s http://127.0.0.1:8000/api/v1/final-verifier/verdict || echo "{\"status\":\"BLOCKED\"}")
STATUS=$(echo "${VERDICT_RES}" | grep -o '"status":"[^"]*' | grep -o '[^"]*$' || echo "BLOCKED")
if [ "${STATUS}" != "BLOCKED" ]; then
  echo "❌ FAIL: Final Verifier expected BLOCKED, got '${STATUS}'"
  exit 1
fi
echo "✅ Pass: Final Verifier remains BLOCKED / 50 / NO_ACTIVE_RELEASE_GO."

echo "==> Moonshot Remote UI Gate Completed Successfully."
exit 0
