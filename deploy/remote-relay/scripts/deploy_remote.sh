#!/usr/bin/env bash
# Deploy control plane on remote host
set -e

echo "[info] Bootstrapping remote relay docker compose stack..."
docker-compose down || true
docker-compose up -d --build

echo "[success] Deployment initiated."
exit 0
