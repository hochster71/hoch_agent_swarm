#!/usr/bin/env bash
set -e

echo "=================================================="
echo "DOCKER ROLE SEPARATION CHECK"
echo "=================================================="

# 1. Fetch image IDs
API_IMG_ID=$(docker image inspect hoch-agent-swarm/has-api:latest --format '{{.Id}}' 2>/dev/null || echo "")
WORKER_IMG_ID=$(docker image inspect hoch-agent-swarm/has-worker:latest --format '{{.Id}}' 2>/dev/null || echo "")

if [ -z "$API_IMG_ID" ] || [ -z "$WORKER_IMG_ID" ]; then
  echo "[FAIL] Missing has-api or has-worker image."
  exit 1
fi

echo "API Image ID:    $API_IMG_ID"
echo "Worker Image ID: $WORKER_IMG_ID"

if [ "$API_IMG_ID" = "$WORKER_IMG_ID" ]; then
  echo "[FAIL] has-api and has-worker images are identical (no role separation)."
  exit 1
fi
echo "[PASS] has-api and has-worker have distinct image IDs."

# 2. Verify labels
API_ROLE=$(docker image inspect hoch-agent-swarm/has-api:latest --format '{{index .Config.Labels "org.hoch.role"}}')
WORKER_ROLE=$(docker image inspect hoch-agent-swarm/has-worker:latest --format '{{index .Config.Labels "org.hoch.role"}}')

if [ "$API_ROLE" != "api" ]; then
  echo "[FAIL] API role label mismatch: expected 'api', got '$API_ROLE'"
  exit 1
fi

if [ "$WORKER_ROLE" != "worker" ]; then
  echo "[FAIL] Worker role label mismatch: expected 'worker', got '$WORKER_ROLE'"
  exit 1
fi
echo "[PASS] Label checks passed (API: $API_ROLE, Worker: $WORKER_ROLE)"

# 3. Check role marker files
if ! docker compose exec -T has-api test -f /app/.has-role-api; then
  echo "[FAIL] has-api container is missing role marker file /app/.has-role-api"
  exit 1
fi

if ! docker compose exec -T has-worker test -f /app/.has-role-worker; then
  echo "[FAIL] has-worker container is missing role marker file /app/.has-role-worker"
  exit 1
fi
echo "[PASS] Role marker file checks passed."

# 4. Check user
API_USER=$(docker inspect has-api --format '{{.Config.User}}')
WORKER_USER=$(docker inspect has-worker --format '{{.Config.User}}')

if [ "$API_USER" != "appuser" ] || [ "$WORKER_USER" != "appuser" ]; then
  echo "[FAIL] Containers must run as appuser (API user: $API_USER, Worker user: $WORKER_USER)"
  exit 1
fi
echo "[PASS] Non-root user checks passed."

echo "[SUCCESS] Docker role image separation successfully verified."
