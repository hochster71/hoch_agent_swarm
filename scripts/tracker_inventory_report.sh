#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/../has_live_project_tracker/data"

echo "=================================================="
echo "HAS/HASF GLOBAL PROJECT REGISTRY REPORT"
echo "=================================================="

# 1. GitHub Inventory Summary
if [ -f "$DATA_DIR/github_inventory.json" ]; then
    REPOS=$(jq '. | length' "$DATA_DIR/github_inventory.json")
    LANGUAGES=$(jq -r '[.[].language] | unique | .[]' "$DATA_DIR/github_inventory.json" | paste -sd, -)
    echo "GitHub Repositories Discovered: $REPOS"
    echo "Primary Languages:             $LANGUAGES"
else
    echo "GitHub Repositories:            [MISSING]"
fi

echo "--------------------------------------------------"

# 2. Local Workspaces Summary
if [ -f "$DATA_DIR/local_inventory.json" ]; then
    WORKSPACES=$(jq '. | length' "$DATA_DIR/local_inventory.json")
    TOTAL_FILES=$(jq '[.[].file_count] | add' "$DATA_DIR/local_inventory.json")
    TOTAL_SIZE=$(jq '[.[].total_size_mb] | add' "$DATA_DIR/local_inventory.json")
    echo "Local Workspace Folders:        $WORKSPACES"
    echo "Total Files Scanned:            $TOTAL_FILES"
    echo "Total Local Space Consumed:     $TOTAL_SIZE MB"
else
    echo "Local Workspace Catalog:        [MISSING]"
fi

echo "--------------------------------------------------"

# 3. Cloud Documents Summary
if [ -f "$DATA_DIR/cloud_inventory.json" ]; then
    CLOUD_FILES=$(jq '. | length' "$DATA_DIR/cloud_inventory.json")
    ICLOUD_COUNT=$(jq '[.[] | select(.provider == "iCloud Drive")] | length' "$DATA_DIR/cloud_inventory.json")
    GDRIVE_COUNT=$(jq '[.[] | select(.provider == "Google Drive")] | length' "$DATA_DIR/cloud_inventory.json")
    echo "Cloud Files Cataloged:          $CLOUD_FILES"
    echo " • iCloud Drive Documents:      $ICLOUD_COUNT"
    echo " • Google Drive Documents:      $GDRIVE_COUNT"
else
    echo "Cloud Documents Index:          [MISSING]"
fi

echo "=================================================="
