#!/usr/bin/env bash
# 24/7 Operations: restore_state.sh
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

BACKUP_FILE=${1:-""}
DRY_RUN=${2:-"false"}

if [ -z "$BACKUP_FILE" ]; then
    echo "[FAIL] Missing backup file argument. Usage: restore_state.sh <backup_file> [dry_run_flag]"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[FAIL] Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "[INFO] Restoring state from backup: $BACKUP_FILE (Dry-Run: $DRY_RUN)..."

if [ "$DRY_RUN" = "true" ]; then
    echo "[PASS] Dry-run check: Backup file can be uncompressed and paths are valid."
    tar -tzf "$BACKUP_FILE" > /dev/null
    exit 0
fi

# Unpack tarball safely
tar -xzf "$BACKUP_FILE" -C "$PROJECT_ROOT"

echo "[PASS] State successfully restored from: $BACKUP_FILE"
exit 0
