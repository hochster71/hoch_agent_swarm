#!/usr/bin/env bash
# HOCH GOAL Runtime Loop — governed e2e loop toward the app-store critical-path table.
#
#   Governor: Michael (operator). This loop NEVER does founder/high-risk work itself.
#   Each cycle:
#     1) translate the orchestrator's prose next-actions -> structured, gated queue
#     2) run the SAFE class via the safe-executor (whitelist + operator-hold + approval routing)
#     3) refresh the live control-plane feed so the pinned widget stays warm
#     4) write a heartbeat + a compact runtime-status JSON the widget/dashboards can read
#
#   Fail-closed: safe-executor only runs whitelisted, idempotent actions; anything risky or
#   founder-owned is routed to human_approval_queue.json for the governor. Honors operator hold.
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)"
PY=python3
LOG="data/backups/goal_runtime_loop.log"
STATUS="frontend/data/goal_runtime_loop_status.json"
INTERVAL="${GOAL_LOOP_INTERVAL:-60}"
mkdir -p data/backups frontend/data
cyc=0
echo "[$(date -u +%FT%TZ)] GOAL runtime loop START (governor=Michael, interval=${INTERVAL}s, pid=$$)" >> "$LOG"
while true; do
  cyc=$((cyc+1)); ts=$(date -u +%FT%TZ)
  # 1) orchestrator prose -> structured queue (unknown/flagged -> approval, never fabricated)
  $PY scripts/hoch_action_translator.py --write >/dev/null 2>&1
  # 2) SAFE class only. SAFE_EXECUTOR_ENABLED=1 = governor-authorized live run.
  out=$(SAFE_EXECUTOR_ENABLED=1 $PY scripts/hoch_safe_executor.py 2>/dev/null)
  ok=$(printf '%s' "$out" | grep -c '"outcome": "SUCCESS"')
  appr=$(printf '%s' "$out" | grep -c 'ROUTED_TO_APPROVAL')
  blk=$(printf '%s' "$out" | grep -c '"outcome": "BLOCKED"')
  # 3) keep the live control-plane feed / widget warm
  curl -s http://127.0.0.1:8000/api/v1/control-plane/status >/dev/null 2>&1 \
    || curl -s http://127.0.0.1:8765/api/v1/control-plane/status >/dev/null 2>&1
  # 4) heartbeat + runtime status for the widget
  printf '{"schema":"goal-runtime-loop-v1","updated_at":"%s","cycle":%s,"governor":"Michael","safe_ok":%s,"routed_to_approval":%s,"blocked_by_hold":%s}\n' \
    "$ts" "$cyc" "${ok:-0}" "${appr:-0}" "${blk:-0}" > "$STATUS"
  echo "[$ts] cycle=$cyc safe_ok=${ok:-0} routed_to_approval=${appr:-0} blocked=${blk:-0}" >> "$LOG"
  sleep "$INTERVAL"
done
