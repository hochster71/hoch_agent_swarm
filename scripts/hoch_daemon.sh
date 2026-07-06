#!/usr/bin/env bash
# hoch_daemon.sh — CONTINUOUS autonomy loop (the always-on heartbeat).
#
# Runs the full portfolio tick back-to-back instead of a 10-minute launchd interval, so every
# factory + AI Michael + the cyber swarm advance continuously. The cadence's own single-flight lock
# means a slow (LLM) tick never stacks — the loop simply runs as fast as real work allows.
#
# Honest note: polling every N seconds does NOT create improvement out of nothing — a plateaued
# factory still reads STALLED/CONVERGED. It keeps the system LIVE and does real work wherever
# headroom (thin classes, swarm targets) exists. $0.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
INTERVAL="${HOCH_DAEMON_INTERVAL:-10}"
LOG="data/backups/hoch_daemon.log"
mkdir -p data/backups
echo "[$(date -u +%FT%TZ)] hoch_daemon start (interval ${INTERVAL}s)" >> "$LOG"
while true; do
  bash scripts/hoch_cadence.sh >> "$LOG" 2>&1 || echo "[$(date -u +%FT%TZ)] tick error" >> "$LOG"
  sleep "$INTERVAL"
done
