#!/usr/bin/env bash
# brain_cadence.sh — one self-improvement tick, META-DIRECTED.
#
# The research meta-loop reads the real gaps and picks the single highest-leverage lever; this
# script executes it, then always runs mechanical selection + convergence and publishes the live
# feed. Single-flight lock so a slow local-model tick never stacks on the next interval. Safe:
# every stage degrades cleanly when no local model is up (mechanical loop still advances).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
export PATH="$HOME/.local/bin:$PATH"
PY="$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)"
STAMP="$(date -u +%FT%TZ)"

# Single-flight lock — PID-aware and SELF-HEALING. A bare mkdir lock never releases if the owner
# is killed (SIGKILL, launchd stop, crash), which would silently freeze the cadence forever — a
# fail-open trap. So we record the owner PID and reclaim the lock if that PID is no longer alive.
LOCK="/tmp/hoch_brain_cadence.lock"
PIDFILE="$LOCK/pid"
_acquire() { mkdir "$LOCK" 2>/dev/null && { echo $$ > "$PIDFILE"; trap 'rm -f "$PIDFILE"; rmdir "$LOCK" 2>/dev/null' EXIT; return 0; }; return 1; }
if ! _acquire; then
    OWNER="$(cat "$PIDFILE" 2>/dev/null || echo "")"
    if [ -n "$OWNER" ] && kill -0 "$OWNER" 2>/dev/null; then
        echo "[$STAMP] previous tick still running (pid $OWNER) — skip"; exit 0
    fi
    echo "[$STAMP] stale lock (owner ${OWNER:-unknown} not alive) — reclaiming"
    rm -f "$PIDFILE"; rmdir "$LOCK" 2>/dev/null
    _acquire || { echo "[$STAMP] lock race — skip"; exit 0; }
fi

echo "[$STAMP] brain cadence tick (meta-directed)"

# 0. DISPATCH — autonomously discover and seed new task classes.
$PY -m backend.brain_convergence.swarm_dispatcher 2>/dev/null | sed 's/^/  /'

# 1. META — decide the highest-leverage lever from the real gap analysis.
$PY -m backend.brain_convergence.research_meta 2>/dev/null | sed 's/^/  /'
CHOSEN="$($PY -c "import json;print(json.load(open('data/prompt_brain/research_meta_decision.json'))['chosen_lever'])" 2>/dev/null || echo UNKNOWN)"

# 2. EXECUTE the chosen lever ($0 local-model path; each no-ops cleanly if the model is down).
case "$CHOSEN" in
  EXPAND)
    echo "  lever=EXPAND — growing thin pools, then improving"
    $PY -m backend.brain_convergence.expand_run 8 6 2>/dev/null | sed 's/^/    /' || true
    $PY -m backend.brain_convergence.recursive_optimizer 6 2>/dev/null | sed 's/^/    /' || true ;;
  IMPROVE|SELECT)
    echo "  lever=$CHOSEN — recursive multi-turn improvement sweep"
    $PY -m backend.brain_convergence.recursive_optimizer 6 2>/dev/null | sed 's/^/    /' || true ;;
  RECONCILE)
    echo "  lever=RECONCILE — taxonomy merges recommended (operator-confirmed; see decision file)" ;;
  CONVERGED)
    echo "  lever=CONVERGED — at the honest ceiling of current levers (see decision file)" ;;
  IMPROVER_OFFLINE)
    echo "  lever=IMPROVER_OFFLINE — mechanical-only this tick (start Ollama for the live brain)" ;;
  *)
    echo "  lever=$CHOSEN — mechanical loop only" ;;
esac

# 3. SELECT / PROMOTE + convergence (mechanical, always runs; passes real improver status).
$PY -m backend.brain_convergence.run_m0 2>/dev/null | tail -1 | sed 's/^/  /'

# 4. Refresh the codified audit + publish the live feed for the moonshot console.
$PY -m backend.brain_convergence.gap_analysis 2>/dev/null | tail -1 | sed 's/^/  /' || true
$PY scripts/write_brain_live.py 2>/dev/null | sed 's/^/  /' || true
