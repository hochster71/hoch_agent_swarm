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

# Clean up any potential conflicting host processes first (defense in depth)
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "backend.main" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Check if already healthy first to avoid redundant socket proxy load
API_HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' has-api 2>/dev/null || echo "\"unknown\"")
UI_HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' has-ui 2>/dev/null || echo "\"unknown\"")

if [ "$API_HEALTH" == "\"healthy\"" ] && [ "$UI_HEALTH" == "\"healthy\"" ]; then
  echo "==> Services are already healthy and running. Skipping compose up."
else
  # Run docker compose up with build
  docker compose up --build -d has-api has-ui has-worker
fi

echo "==> Waiting for services to become healthy..."
for i in {1..30}; do
  API_HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' has-api 2>/dev/null || echo "\"unknown\"")
  UI_HEALTH=$(docker inspect --format='{{json .State.Health.Status}}' has-ui 2>/dev/null || echo "\"unknown\"")
  
  if [ "$API_HEALTH" == "\"healthy\"" ] && [ "$UI_HEALTH" == "\"healthy\"" ]; then
    echo "==> All HAS services are HEALTHY!"
    docker compose ps
    exit 0
  fi
  echo "Waiting... API: $API_HEALTH, UI: $UI_HEALTH ($i/30)"
  sleep 2
done

echo "ERROR: Services failed to become healthy in time."
docker compose logs
exit 1
