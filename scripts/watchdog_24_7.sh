#!/usr/bin/env bash
# 24/7 Operations: watchdog_24_7.sh
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Running out-of-band Watchdog diagnostic ping..."

# Try up to 3 times to prevent transient network issues from triggering restart
FAILED_COUNT=0
for i in {1..3}; do
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/api/v1/operator/health --max-time 5 || echo "500")
    if [ "$STATUS_CODE" -eq 200 ] || [ "$STATUS_CODE" -eq 204 ] || [ "$STATUS_CODE" -eq 401 ] || [ "$STATUS_CODE" -eq 403 ]; then
        # App is responsive (even auth failures mean the process is running)
        break
    else
        FAILED_COUNT=$((FAILED_COUNT + 1))
        sleep 2
    fi
done

if [ "$FAILED_COUNT" -eq 3 ]; then
    echo "[WARNING] Swarm application is unresponsive. Attempting automatic Docker restart..."
    if docker compose -f docker-compose.24x7.yml restart hoch-app; then
        echo "[PASS] Autorecover triggered: hoch-app restarted successfully."
        exit 0
    else
        echo "[FAIL] Autorecover failed: Docker daemon or Compose container restart command errored."
        exit 1
    fi
else
    echo "[PASS] Watchdog checked: Swarm API is healthy."
    exit 0
fi
