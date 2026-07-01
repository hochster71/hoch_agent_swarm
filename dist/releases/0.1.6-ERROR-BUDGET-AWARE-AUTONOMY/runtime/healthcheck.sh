#!/bin/bash
# healthcheck.sh — Production Health Check Verification Script
set -eo pipefail

HOST=${1:-localhost}
PORT_BACKEND=8000
PORT_COCKPIT=8085

echo "[healthcheck] Querying backend liveness endpoint..."
LIVENESS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT_BACKEND/api/v1/hochster/health || echo "500")

if [ "$LIVENESS_STATUS" != "200" ]; then
    echo "[healthcheck] ERROR: Backend liveness check failed (HTTP status $LIVENESS_STATUS)"
    exit 1
fi
echo "[healthcheck] Backend status: OK"

echo "[healthcheck] Querying preflight readiness gate..."
READINESS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT_BACKEND/api/v1/readiness/status || echo "500")

if [ "$READINESS_STATUS" != "200" ]; then
    echo "[healthcheck] ERROR: Readiness check failed (HTTP status $READINESS_STATUS)"
    exit 1
fi
echo "[healthcheck] Readiness status: OK"

echo "[healthcheck] Probing cockpit static assets..."
COCKPIT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT_COCKPIT/index.html || echo "500")

if [ "$COCKPIT_STATUS" != "200" ]; then
    echo "[healthcheck] ERROR: Cockpit landing page check failed (HTTP status $COCKPIT_STATUS)"
    exit 1
fi
echo "[healthcheck] Cockpit landing page status: OK"

echo "--------------------------------------------------"
echo "ALL HEALTH AND READINESS CHECKS PASSED SUCCESSFULLY"
echo "--------------------------------------------------"
exit 0
