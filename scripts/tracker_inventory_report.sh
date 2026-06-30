#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/../has_live_project_tracker/data"
SUMMARY_FILE="$DATA_DIR/inventory_summary.json"

if [ ! -f "$SUMMARY_FILE" ]; then
    echo "Error: inventory_summary.json not found." >&2
    exit 1
fi

echo "=================================================="
echo "HAS/HASF TRACKER INVENTORY INGESTION REPORT"
echo "=================================================="

# Read values using jq
AGENT_COUNT=$(jq '.agent_count' "$SUMMARY_FILE")
BUILD_COUNT=$(jq '.build_count' "$SUMMARY_FILE")
GITHUB_COUNT=$(jq '.github_count' "$SUMMARY_FILE")
GITHUB_STATUS=$(jq -r '.github_status' "$SUMMARY_FILE")
LOCAL_COUNT=$(jq '.local_count' "$SUMMARY_FILE")
LOCAL_STATUS=$(jq -r '.local_status' "$SUMMARY_FILE")
CLOUD_COUNT=$(jq '.cloud_count' "$SUMMARY_FILE")
CLOUD_STATUS=$(jq -r '.cloud_status' "$SUMMARY_FILE")
SUMMARY_VERDICT=$(jq -r '.overall_status' "$SUMMARY_FILE")

echo "Agent Inventory Count:        $AGENT_COUNT"
echo "Build Inventory Count:        $BUILD_COUNT"
echo "GitHub Inventory Status:      $GITHUB_STATUS ($GITHUB_COUNT repos)"
echo "Local Project Inventory Count: $LOCAL_COUNT"
echo "Cloud Inventory Status:       $CLOUD_STATUS ($CLOUD_COUNT documents)"
echo "Summary Verdict:              $SUMMARY_VERDICT"

echo "--------------------------------------------------"
echo "Remaining Partials:"
# Get all blockers or list iCloud Drive partials
jq -r '.blockers[]' "$SUMMARY_FILE" || echo "None"
# Check if iCloud was skipped/missing
if ! ls ~/Library/Mobile\ Documents/com~apple~CloudDocs &>/dev/null; then
    echo " • iCloud Drive (Skipped: mount path absent or unreadable)"
fi

echo "--------------------------------------------------"
echo "Top Next Actions:"
echo " 1. [T010] Deduplicate and classify local vs. remote workspaces."
echo " 2. [T011] Integrate inventory data tables into the Live Tracker UI."
echo " 3. Verify signature validations for incoming git commits."
echo "=================================================="
