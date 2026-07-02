#!/usr/bin/env bash
# =============================================================================
# moonshot_remote_tunnel_start.sh
# Start SSH reverse tunnel for Moonshot UI over Tailscale
# =============================================================================
set -euo pipefail

VPS_USER="root"
VPS_HOST="50.116.41.183"
TAILSCALE_IP="100.87.18.15"
PORT="8765"

echo "Checking if SSH reverse tunnel is already active..."
PID=$(ps aux | grep -E "ssh.*-R.*${PORT}" | grep -v grep | awk '{print $2}' || echo "")

if [ -n "$PID" ]; then
  echo "Tunnel is already running with PID: ${PID}"
  exit 0
fi

echo "Starting SSH reverse tunnel..."
ssh -N -f -R "${TAILSCALE_IP}:${PORT}:127.0.0.1:${PORT}" "${VPS_USER}@${VPS_HOST}"
sleep 2

# Verify it is active locally
PID=$(ps aux | grep -E "ssh.*-R.*${PORT}" | grep -v grep | awk '{print $2}' || echo "")
if [ -n "$PID" ]; then
  echo "Tunnel successfully started. PID: ${PID}"
  exit 0
else
  echo "ERROR: Failed to start SSH reverse tunnel."
  exit 1
fi
