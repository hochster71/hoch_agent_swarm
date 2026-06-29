#!/usr/bin/env bash
# 24/7 Operations: stop_24_7.sh
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Stopping 24/7 Reliability Control Plane..."
if docker compose -f docker-compose.24x7.yml stop; then
    echo "[PASS] 24/7 services stopped successfully (volumes retained)."
    exit 0
else
    echo "[FAIL] Failed to stop Docker Compose services."
    exit 1
fi
