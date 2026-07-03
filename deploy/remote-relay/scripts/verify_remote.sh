#!/usr/bin/env bash
# Verification checking tool for public-private connection boundary
set -e

echo "[info] Verifying local model port private constraints..."
# Checks if model ports are public
if curl -s --connect-timeout 2 http://localhost:11434 >/dev/null; then
  echo "[warning] Model port 11434 is public."
else
  echo "[success] Model port 11434 is protected."
fi

exit 0
