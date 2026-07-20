#!/usr/bin/env bash
# HELM build-to-GOAL — start the autonomous runner hands-off.
#
#   bash scripts/helm_build_to_goal.sh          # DRY: show the plan, change nothing
#   bash scripts/helm_build_to_goal.sh --go     # LIVE: your standing authorization to build
#   bash scripts/helm_build_to_goal.sh --go &   # LIVE in background — walk away
#
# Drives the council loop (Orchestrator → Builder guarded-execute → Grok verify) node-by-node
# until GOAL, within HELM's hard rails. Stops and reports on GOAL, a founder gate, or a real
# blocker — never fakes completion. Progress: coordination/goal/build_to_goal_status.json.
set -uo pipefail
REPO="/Users/michaelhoch/hoch_agent_swarm"
PY="$REPO/.venv/bin/python3"; [ -x "$PY" ] || PY="$(command -v python3)"
LOG="/tmp/helm_build_to_goal.log"
cd "$REPO" || exit 1

# Load founder env so the guarded lanes (grok key, dispatch flag) are visible.
set -a
[ -f "$HOME/.helm/helm.env" ] && . "$HOME/.helm/helm.env"
[ -f "$REPO/.env" ] && . "$REPO/.env"
set +a
# COST: the Builder is the `claude` CLI (Claude Code). If ANTHROPIC_API_KEY is set, Claude Code
# bills PER-TOKEN via the API instead of using the flat Max plan. Unset it here so the builder
# runs on your Max subscription (flat, far cheaper for 24/7). The Auditor uses Grok (XAI_API_KEY),
# which is untouched.
unset ANTHROPIC_API_KEY

GO=""
[ "${1:-}" = "--go" ] && GO="--go"
[ "${1:-}" = "--auto" ] && GO="--auto"   # loop autonomously until GOAL — no re-runs, ever

echo "▸ HELM build-to-GOAL  ($([ -n "$GO" ] && echo LIVE || echo DRY))" | tee "$LOG"
echo "  Auditor (Grok) CLI: $(command -v grok || echo 'NOT INSTALLED — required')" | tee -a "$LOG"
echo "  Builder (Claude) CLI: $(command -v claude || echo 'not installed — needed for build nodes N4/N8/N5')" | tee -a "$LOG"
echo "  Watch progress: tail -f $LOG   ·   status: coordination/goal/build_to_goal_status.json" | tee -a "$LOG"
echo | tee -a "$LOG"

if [ -z "$GO" ]; then
  echo "  DRY RUN — showing the plan only. Re-run with --go to build for real." | tee -a "$LOG"
fi

# Run the loop, streaming to the log. In LIVE mode this may run a long time (build nodes).
"$PY" "$REPO/scripts/helm_goal_runner.py" $GO 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}

echo | tee -a "$LOG"
if [ "$rc" = "0" ]; then
  echo "✓ GOAL reached — see coordination/goal/build_to_goal_status.json" | tee -a "$LOG"
else
  echo "■ Runner stopped (needs founder or blocked). Read the last lines above + the status file." | tee -a "$LOG"
fi
exit "$rc"
