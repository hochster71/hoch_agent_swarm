#!/usr/bin/env bash
set -euo pipefail
mkdir -p artifacts/live_screenshots
docker compose up -d --build hoch-app
docker compose --profile screenshots run --rm screenshot-worker
