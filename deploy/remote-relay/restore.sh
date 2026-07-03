#!/usr/bin/env bash
# HOCH Prompt Brain restore tool
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
MANIFEST="$BACKUP_DIR/backup_manifest.json"

if [ ! -f "$MANIFEST" ]; then
  echo "[error] Backup manifest not found."
  exit 1
fi

echo "[info] Verifying manifest..."
archive_name=$(grep -o '"archive_file": "[^"]*' "$MANIFEST" | cut -d'"' -f4)
expected_checksum=$(grep -o '"checksum": "[^"]*' "$MANIFEST" | cut -d'"' -f4)

archive_path="$BACKUP_DIR/$archive_name"
actual_checksum=$(sha256sum "$archive_path" | awk '{print $1}')

if [ "$expected_checksum" != "$actual_checksum" ]; then
  echo "[error] Checksum mismatch. Archive is corrupted."
  exit 1
fi

# Restore action
echo "[info] Extracting archive to codebase root..."
tar -xzf "$archive_path" -C .

echo "[success] Restore completed successfully."
exit 0
