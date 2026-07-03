#!/usr/bin/env bash
# Rotates logs and stale evidence datasets to keep disk space usage low.
echo "[info] Running log and evidence rotation..."
find ./logs -name "*.log" -mtime +14 -exec rm -f {} \;
echo "[success] Log rotation complete."
exit 0
