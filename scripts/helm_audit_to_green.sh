#!/usr/bin/env bash
# HELM audit-to-GREEN — start the autonomous audit swarm hands-off.
#   bash scripts/helm_audit_to_green.sh          # DRY: show the audit plan
#   nohup bash scripts/helm_audit_to_green.sh --auto &   # LIVE: loop to all-GREEN, walk away
#
# Each controllable audit: Builder gathers REAL evidence (re-hash, re-run tests, secret sweep,
# guard/spend probes) → Grok independently verifies → GREEN or a recorded finding. Loops to all-
# GREEN or a genuine founder decision. Read-only; frozen target untouched; never fakes green.
set -uo pipefail
REPO="/Users/michaelhoch/hoch_agent_swarm"
PY="$REPO/.venv/bin/python3"; [ -x "$PY" ] || PY="$(command -v python3)"
LOG="/tmp/helm_audit.log"; cd "$REPO" || exit 1
set -a; [ -f "$HOME/.helm/helm.env" ] && . "$HOME/.helm/helm.env"; [ -f "$REPO/.env" ] && . "$REPO/.env"; set +a
unset ANTHROPIC_API_KEY   # any Claude lane uses the flat Max plan, not API billing
MODE="--go"; [ "${1:-}" = "--auto" ] && MODE="--auto"; [ "${1:-}" = "" ] && MODE=""
echo "▸ HELM audit-to-GREEN ($([ -n "$MODE" ] && echo LIVE || echo DRY))" | tee "$LOG"
echo "  Auditor (Grok): $(command -v grok || echo 'NOT INSTALLED — required')" | tee -a "$LOG"
echo "  Watch: tail -f $LOG  ·  UI: https://127.0.0.1:8770/audit  ·  status: coordination/goal/audit_status.json" | tee -a "$LOG"
"$PY" "$REPO/scripts/helm_audit_runner.py" $MODE 2>&1 | tee -a "$LOG"
