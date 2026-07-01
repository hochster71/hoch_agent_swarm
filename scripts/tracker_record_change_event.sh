#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NDJSON_FILE="$SCRIPT_DIR/../has_live_project_tracker/data/dora_events.ndjson"

# Check if there is a JSON string passed as the first argument
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 '<json_event_string>'"
    echo "Example: $0 '{\"change_id\": \"ch-1\", \"commit_sha\": \"a1b2c3d\", \"commit_time\": \"2026-06-30T10:00:00Z\", \"deploy_time\": \"2026-06-30T10:15:00Z\", \"deploy_status\": \"success\"}'"
    exit 1
fi

EVENT_JSON="$1"

# Validate JSON (basic syntax check using node)
node -e "JSON.parse(process.argv[1])" "$EVENT_JSON" 2>/dev/null || {
    echo "ERROR: Invalid JSON format provided!"
    exit 1
}

# Append safely
echo "$EVENT_JSON" >> "$NDJSON_FILE"
echo "Successfully appended event to dora_events.ndjson"
