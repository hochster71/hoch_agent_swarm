#!/usr/bin/env bash
# 24/7 Operations: failover_check.sh
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Running VPS high-availability heartbeat diagnostic..."

# In local-first / low-cost VPS setup, the VPS checks if the local primary is online
PRIMARY_HOST="http://localhost:8086" # Can be configured as external domain/IP
MAX_RETRIES=3
FAILED_PINGS=0

for i in $(seq 1 $MAX_RETRIES); do
    PING_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "$PRIMARY_HOST/api/v1/operator/health" --max-time 10 || echo "500")
    if [ "$PING_HEALTH" -eq 200 ] || [ "$PING_HEALTH" -eq 204 ]; then
        break
    else
        FAILED_PINGS=$((FAILED_PINGS + 1))
        sleep 2
    fi
done

if [ "$FAILED_PINGS" -eq "$MAX_RETRIES" ]; then
    echo "[WARNING] Heartbeat failed. Primary host is UNREACHABLE."
    # Trigger promotion check
    bash "$PROJECT_ROOT/scripts/failover_promote_secondary.sh"
    exit 0
else
    echo "[PASS] Heartbeat stable: Primary control plane is active."
    exit 0
fi
