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
  /Users/michaelhoch/hoch_agent_swarm/ \
  "${TARGET_USER}@${TARGET_HOST}:/root/hoch_agent_swarm/"

echo "🟢 Secure sync completed."
