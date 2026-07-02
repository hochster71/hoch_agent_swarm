#!/usr/bin/env bash
# =============================================================================
# hoch200_gate.sh
# Gate check to ensure HOCH-200 relay setup is verified and secure.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS_FILE="${REPO_ROOT}/hoch_pods/compute/setup_status.json"

echo "==> Running HOCH-200 Relay Gate Check..."

# 1. Verify setup_status.json exists
if [ ! -f "${STATUS_FILE}" ]; then
  echo "FAIL: setup_status.json does not exist. Run verification first."
  exit 1
fi

# 2. Check gate status
GATE_STATUS=$(python3 -c "
import json
try:
    with open('${STATUS_FILE}', 'r') as f:
        data = json.load(f)
    print(data.get('gate', ''))
except Exception as e:
    print('ERROR:', e)
")

if [ "${GATE_STATUS}" != "CONDITIONAL_GO" ] && [ "${GATE_STATUS}" != "FINAL_GO" ]; then
  echo "FAIL: HOCH-200 gate status is '${GATE_STATUS}', expected 'CONDITIONAL_GO' or 'FINAL_GO'."
  exit 1
fi
echo "✅ Gate status is verified: ${GATE_STATUS}"

# 3. Test public port closure (anti-exposure verification)
VPS_HOST=$(python3 -c "
import json
with open('${STATUS_FILE}', 'r') as f:
    print(json.load(f).get('public_ipv4', ''))
")

echo "ℹ Probing public port 3012 closure on ${VPS_HOST}..."
if python3 -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(3.0)
try:
    s.connect(('${VPS_HOST}', 3012))
    s.close()
    exit(1) # Connected -> open = fail
except Exception:
    exit(0) # Error/timeout -> closed = pass
"; then
  echo "✅ Public Port 3012 is successfully verified as closed/blocked."
else
  echo "FAIL: Public Port 3012 is reachable! Exposure constraint violated."
  exit 1
fi

echo "========================================="
echo "HOCH-200 Gate Result: PASS"
echo "========================================="
exit 0
