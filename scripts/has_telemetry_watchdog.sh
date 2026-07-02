#!/usr/bin/env bash
set -euo pipefail

cd /Users/michaelhoch/hoch_agent_swarm

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

while true; do
  TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    echo "[$TS] HAS telemetry watchdog refresh start"
    python3 scripts/refresh_live_telemetry.py
    python3 scripts/verify_live_telemetry_freshness.py
    echo "[$TS] HAS telemetry watchdog refresh complete"
    echo
  } >> "$LOG_DIR/has_telemetry_watchdog.log" 2>&1

  sleep 300
done
