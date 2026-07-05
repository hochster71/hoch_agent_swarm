#!/usr/bin/env bash
# HOCH Prompt Brain backup tool
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

timestamp=$(date +%Y%m%d_%H%M%S)
archive_name="hoch_backup_$timestamp.tar.gz"
archive_path="$BACKUP_DIR/$archive_name"

echo "[info] Packaging data registers..."

tar --ignore-failed-read -czf "$archive_path" \
  backend/swarm_ledger.db \
  has_live_project_tracker/data \
  data/prompt_brain \
  data/doctrine \
  data/app_store \
  docs/doctrine \
  docs/app_store \
  docs/prompt_brain/pilot

# Generate checksum
sha256sum "$archive_path" > "$archive_path.sha256"

# Write manifest
cat <<EOF > "$BACKUP_DIR/backup_manifest.json"
{
  "backup_id": "$timestamp",
  "archive_file": "$archive_name",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "checksum": "$(cat "$archive_path.sha256" | awk '{print $1}')"
}
EOF

echo "[success] Backup complete: $archive_name"
exit 0
