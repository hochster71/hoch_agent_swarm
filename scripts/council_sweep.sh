#!/usr/bin/env bash
# Continuous adversarial council. Runs on a timer, audits HELM's own critical surfaces.
# Findings self-adjudicate: CONFIRMED -> autonomous remediation. REJECTED -> discarded.
# Only genuine judgment reaches Michael. He never sees a clipboard.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
PY="./.venv/bin/python3"; [ -x "$PY" ] || PY="$(command -v python3)"
LOG=/tmp/helm-council-sweep.log

TARGETS=(
  backend/council/authority_gateway.py
  backend/council/decision_record.py
  backend/council/founder_model.py
  backend/truth/task_status.py
  backend/truth/integrity.py
  backend/truth/runtime_source.py
  backend/mission_control/per_task_lease.py
)
for t in "${TARGETS[@]}"; do
  [ -f "$t" ] || continue
  printf '%s  audit %s\n' "$(date -u +%H:%M:%SZ)" "$t" >> "$LOG"
  "$PY" backend/council/auto_council.py "$t" >> "$LOG" 2>&1 || \
    printf '%s  audit FAILED %s\n' "$(date -u +%H:%M:%SZ)" "$t" >> "$LOG"
  sleep 5
done
printf '%s  sweep complete\n' "$(date -u +%H:%M:%SZ)" >> "$LOG"
