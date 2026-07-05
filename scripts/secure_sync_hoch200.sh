#!/usr/bin/env bash
# secure_sync_hoch200.sh
# Sole approved sync path for HOCH-200. Insecure host checking is prohibited.

set -euo pipefail

TARGET_HOST="100.87.18.15"
TARGET_USER="root" # TODO: Migrate to a dedicated deploy user instead of root.

echo "Verifying SSH host keys for ${TARGET_HOST}..."
# Use StrictHostKeyChecking=accept-new to pin new host keys securely.
# This prevents MITM attacks while avoiding manual prompt blockages.
SSH_OPTS="-o StrictHostKeyChecking=accept-new"

echo "Syncing repository files to remote host..."
rsync -avz \
  -e "ssh ${SSH_OPTS}" \
  --exclude ".git" \
  --exclude "node_modules" \
  --exclude ".venv" \
  --exclude "*.key" \
  --exclude ".env" \
  --exclude "ag_daemon.log" \
  --exclude "ag_daemon.err" \
  --exclude "*.db-shm" \
  --exclude "*.db-wal" \
  /Users/michaelhoch/hoch_agent_swarm/ \
  "${TARGET_USER}@${TARGET_HOST}:/root/hoch_agent_swarm/"

# --- Fail-closed manifest guard ---------------------------------------------
# The runtime prompt-registry gate goes FAIL_CLOSED (locks task routing) if the
# validated Agent Capability manifest is missing or not PASS on a host. A sync
# that leaves the relay without a valid manifest silently bricks the swarm, so
# verify it landed and reads PASS before declaring success. Fail loudly otherwise.
echo "Verifying prompt-registry manifest on remote (fail-closed gate depends on it)..."
REMOTE_MANIFEST_STATUS=$(ssh ${SSH_OPTS} "${TARGET_USER}@${TARGET_HOST}" \
  "cd /root/hoch_agent_swarm 2>/dev/null && python3 -c \"import json; print(json.load(open('data/prompt_registry/agents.manifest.json')).get('validation_status','MISSING'))\" 2>/dev/null || echo MISSING")
if [ "${REMOTE_MANIFEST_STATUS}" = "PASS" ] || [ "${REMOTE_MANIFEST_STATUS}" = "GO" ]; then
  echo "🟢 Remote registry manifest present and verified (${REMOTE_MANIFEST_STATUS})."
else
  echo "❌ SYNC INCOMPLETE: remote registry manifest is '${REMOTE_MANIFEST_STATUS}'."
  echo "   The swarm will FAIL_CLOSED on that host. Regenerate + re-sync the manifest before relying on the relay."
  exit 1
fi

echo "🟢 Secure sync completed."
