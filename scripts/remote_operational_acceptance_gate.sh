#!/usr/bin/env bash
# =============================================================================
# remote_operational_acceptance_gate.sh
# Verifies full remote operational acceptance conditions on HOCH-200.
# =============================================================================
set -euo pipefail

echo "==> Running Remote Operational Acceptance Gate..."

TARGET_IP="50.116.41.183"
TARGET_DIR="/root/hoch_agent_swarm"

# 1. Fetch current local git HEAD commit
COMMIT_SHA=$(git rev-parse HEAD)
echo "Expected Local Commit: ${COMMIT_SHA}"

# 2. Check remote REVISION
REMOTE_SHA=$(ssh "root@${TARGET_IP}" "cat ${TARGET_DIR}/REVISION" 2>/dev/null || echo "MISSING")
echo "Remote Deployed Commit: ${REMOTE_SHA}"

if [ "${COMMIT_SHA}" != "${REMOTE_SHA}" ]; then
  echo "❌ FAIL: Remote commit mismatch (Expected: ${COMMIT_SHA}, got: ${REMOTE_SHA})"
  exit 1
fi
echo "✅ Pass: Remote commit matches local build commit."

# 3. Check systemd timer/service status
TIMER_STATUS=$(ssh "root@${TARGET_IP}" "systemctl is-active has-goal-runner.timer" 2>/dev/null || echo "inactive")
echo "Remote systemd timer state: ${TIMER_STATUS}"

if [ "${TIMER_STATUS}" != "active" ]; then
  echo "❌ FAIL: Remote systemd goal runner timer is not active."
  exit 1
fi
echo "✅ Pass: Remote goal runner systemd timer is active."

# 4. Check heartbeat file existence and freshness
HEARTBEAT_DATA=$(ssh "root@${TARGET_IP}" "cat ${TARGET_DIR}/runner_heartbeat.json" 2>/dev/null || echo "MISSING")

if [ "${HEARTBEAT_DATA}" = "MISSING" ]; then
  echo "❌ FAIL: Heartbeat file runner_heartbeat.json is missing on remote host."
  exit 1
fi

HB_TIMESTAMP=$(echo "${HEARTBEAT_DATA}" | jq -r '.last_seen' 2>/dev/null || echo "")

if [ -z "${HB_TIMESTAMP}" ]; then
  echo "❌ FAIL: Invalid heartbeat data format."
  exit 1
fi

# Calculate time difference
DIFF=$(python3 -c "
from datetime import datetime, timezone
hb_ts = datetime.fromisoformat('${HB_TIMESTAMP}'.replace('Z', '+00:00'))
now_ts = datetime.now(timezone.utc)
print(int((now_ts - hb_ts).total_seconds()))
")
echo "Heartbeat timestamp: ${HB_TIMESTAMP} (age: ${DIFF}s)"

if [ ${DIFF} -gt 300 ]; then
  echo "❌ FAIL: Heartbeat age is too high (age: ${DIFF}s > 300s)"
  exit 1
fi
echo "✅ Pass: Remote runner heartbeat is fresh (age: ${DIFF}s <= 300s)."

echo "✅ Remote Operational Acceptance Gate Passed successfully."
exit 0
