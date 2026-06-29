#!/usr/bin/env bash
# 24/7 Operations: restart_24_7.sh
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Restarting 24/7 Reliability Control Plane..."
if docker compose -f docker-compose.24x7.yml restart; then
    echo "[PASS] 24/7 services restarted successfully."
    exit 0
else
    echo "[FAIL] Failed to restart Docker Compose services."
    exit 1
fi
