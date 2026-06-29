#!/usr/bin/env bash
# 24/7 Operations: start_24_7.sh
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Starting 24/7 Reliability Control Plane..."
if docker compose -f docker-compose.24x7.yml up -d; then
    echo "[PASS] 24/7 High-Availability services launched successfully."
    exit 0
else
    echo "[FAIL] Failed to start Docker Compose 24x7 services."
    exit 1
fi
