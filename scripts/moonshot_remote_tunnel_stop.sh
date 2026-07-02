#!/usr/bin/env bash
# =============================================================================
# moonshot_remote_tunnel_stop.sh
# Stop SSH reverse tunnel for Moonshot UI over Tailscale
# =============================================================================
set -euo pipefail

PORT="8765"

echo "Checking for active SSH reverse tunnels..."
PID=$(ps aux | grep -E "ssh.*-R.*${PORT}" | grep -v grep | awk '{print $2}' || echo "")

if [ -n "$PID" ]; then
  echo "Stopping tunnel (PID: ${PID})..."
  kill -9 "${PID}"
  echo "Tunnel stopped."
  exit 0
else
  echo "No active tunnel found."
  exit 0
fi
