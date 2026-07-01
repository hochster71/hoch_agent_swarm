#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/hoch_agent_swarm"
AGENT_DIR="$ROOT/agents/storage_steward"
LOG_DIR="$ROOT/runtime/storage_steward"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$LOG_DIR/run-$STAMP.log"

free_gib() {
  df -g "$HOME" | awk 'NR==2 {print $4}'
}

FREE="$(free_gib)"
{
  echo "AHS_STORAGE_STEWARD run: $STAMP"
  echo "Free GiB: $FREE"
  if [ "$FREE" -ge 50 ]; then
    echo "Status: OK. No archive action required."
    exit 0
  fi
  echo "Status: BELOW_THRESHOLD. Running staged cleanup."
  "$HOME/ahs_storage_cleanup_stage.sh"
  echo "Post-cleanup Free GiB: $(free_gib)"
} | tee "$LOG"
