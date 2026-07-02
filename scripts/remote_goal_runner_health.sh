#!/usr/bin/env bash
# =============================================================================
# remote_goal_runner_health.sh
# Checks remote service health and container status.
# =============================================================================
set -euo pipefail

TARGET_IP="50.116.41.183"

echo "==> Verifying remote service and container health on HOCH-200..."

# 1. Probe remote docker container status
CONTAINER_STATUS=$(ssh "root@${TARGET_IP}" "docker inspect --format='{{.State.Health.Status}}' hoch-relay-api 2>/dev/null || echo 'NOT_RUNNING'")
echo "Container hoch-relay-api state: ${CONTAINER_STATUS}"

if [ "${CONTAINER_STATUS}" != "healthy" ]; then
  echo "❌ FAIL: Container status is not healthy (got: ${CONTAINER_STATUS})."
  exit 1
fi

# 2. Query remote health endpoint from within VPS
HEALTH_RESP=$(ssh "root@${TARGET_IP}" "curl -sS http://100.87.18.15:3012/health || echo 'FAILED'")
echo "Remote Health Response: ${HEALTH_RESP}"

if [[ "${HEALTH_RESP}" == *"FAILED"* ]] || [[ "${HEALTH_RESP}" != *"status"* ]]; then
  echo "❌ FAIL: Remote /health endpoint returned invalid or failed status."
  exit 1
fi

echo "✅ Remote goal runner and container are healthy."
exit 0
