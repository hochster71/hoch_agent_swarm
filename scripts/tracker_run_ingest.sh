#!/bin/bash
set -e

# Load secrets if present
SECRETS_FILE="$HOME/.hoch-secrets/has-tracker.env"
if [ -f "$SECRETS_FILE" ]; then
    set -a
    source "$SECRETS_FILE"
    set +a
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=================================================="
echo "RUNNING ALL BATCH A INVENTORY INGESTIONS"
echo "=================================================="

# 1. Sync Agents
python3 scripts/tracker_sync_agents.py

# 2. Sync Builds
python3 scripts/tracker_sync_builds.py

# 3. Ingest GitHub repos
python3 scripts/tracker_ingest_github.py

# 4. Ingest local directories
python3 scripts/tracker_ingest_local.py

# 5. Ingest cloud drives
python3 scripts/tracker_ingest_cloud.py

echo "=================================================="
echo "BATCH A INGESTION RUN COMPLETED"
echo "=================================================="
