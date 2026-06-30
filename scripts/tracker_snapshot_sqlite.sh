#!/bin/bash
set -euo pipefail

# HAS/HASF Live Project Tracker SQLite Snapshot Utility
# Creates a safe read-only copy of a live database without locking it.

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <source_db_path> <target_snapshot_path>"
  exit 1
fi

SOURCE_DB="$1"
TARGET_DB="$2"

if [ ! -f "$SOURCE_DB" ]; then
  echo "Error: Source database does not exist at $SOURCE_DB"
  exit 2
fi

# Ensure target directory exists
TARGET_DIR=$(dirname "$TARGET_DB")
mkdir -p "$TARGET_DIR"

echo "Creating safe snapshot of $SOURCE_DB to $TARGET_DB..."

if command -v sqlite3 >/dev/null 2>&1; then
  echo "sqlite3 CLI detected. Using online .backup API..."
  # Use .backup which runs safely and concurrently without long locks
  sqlite3 "$SOURCE_DB" ".backup '$TARGET_DB'"
else
  echo "Warning: sqlite3 CLI not found. Falling back to copy (cp)..."
  # Fallback to standard copy (ensure read-only safe copy)
  cp "$SOURCE_DB" "$TARGET_DB"
fi

# Make snapshot read-only
chmod 444 "$TARGET_DB"

echo "Snapshot created successfully at $TARGET_DB"
