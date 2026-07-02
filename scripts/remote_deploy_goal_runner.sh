#!/usr/bin/env bash
# =============================================================================
# remote_deploy_goal_runner.sh
# Safely syncs the repository to HOCH-200 VPS and verifies status.
# =============================================================================
set -euo pipefail

TARGET_IP="50.116.41.183"
TARGET_DIR="/root/hoch_agent_swarm"

echo "==> Initiating remote deployment package sync to root@${TARGET_IP}..."

# 1. Capture current git revision
COMMIT_SHA=$(git rev-parse HEAD)
echo "Current Commit: ${COMMIT_SHA}"
echo "${COMMIT_SHA}" > REVISION

# 2. Rsync the codebase safely (excluding heavy build directories)
rsync -avz --delete \
  --exclude="node_modules" \
  --exclude=".venv" \
  --exclude="dist" \
  --exclude=".git" \
  --exclude="*.log" \
  --exclude="*.nohup" \
  --exclude="test-results" \
  --exclude="playwright-report" \
  ./ "root@${TARGET_IP}:${TARGET_DIR}/"

# 3. Write revision file on remote
ssh "root@${TARGET_IP}" "echo '${COMMIT_SHA}' > ${TARGET_DIR}/REVISION"

echo "✅ Sync complete. Deployed Git SHA: ${COMMIT_SHA} to remote ${TARGET_DIR}/REVISION."
exit 0
