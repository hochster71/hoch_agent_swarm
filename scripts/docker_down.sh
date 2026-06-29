#!/usr/bin/env bash
set -euo pipefail

# Verify and pin Docker context based on responsiveness
if docker --context default ps >/dev/null 2>&1; then
  docker context use default >/dev/null
elif docker --context desktop-linux ps >/dev/null 2>&1; then
  docker context use desktop-linux >/dev/null
else
  docker context use default >/dev/null || true
fi

echo "Docker context: $(docker context show)"
echo "Docker server version:"
docker info | grep -E "Server Version" || docker info --format '{{.ServerVersion}}' || echo "Unknown"

echo "==> Stopping all HAS containers..."
docker compose down --remove-orphans -v
echo "==> Done."
