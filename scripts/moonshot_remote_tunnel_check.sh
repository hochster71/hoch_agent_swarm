#!/usr/bin/env bash
# =============================================================================
# moonshot_remote_tunnel_check.sh
# Check SSH reverse tunnel status for Moonshot UI over Tailscale
# =============================================================================
set -euo pipefail

TAILSCALE_IP="100.87.18.15"
PORT="8765"

echo "Checking SSH reverse tunnel process..."
PID=$(ps aux | grep -E "ssh.*-R.*${PORT}" | grep -v grep | awk '{print $2}' || echo "")

if [ -n "$PID" ]; then
  echo "Tunnel process is RUNNING (PID: ${PID})."
  
  # Verify port reachability over Tailscale IP
  if curl -sS -I --connect-timeout 3 "http://${TAILSCALE_IP}:${PORT}/ui-moonshot" &>/dev/null; then
    echo "Tailscale endpoint http://${TAILSCALE_IP}:${PORT}/ui-moonshot is REACHABLE."
    exit 0
  else
    echo "WARNING: Tunnel process exists but Tailscale endpoint is UNREACHABLE."
    exit 2
  fi
else
  echo "Tunnel process is NOT RUNNING."
  exit 1
fi
