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

# Single-flight: if a prior tick is still running (model generation can exceed the interval), skip.
LOCK="/tmp/hoch_brain_cadence.lock"
if ! mkdir "$LOCK" 2>/dev/null; then echo "[$STAMP] previous tick still running — skip"; exit 0; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

echo "[$STAMP] brain cadence tick (meta-directed)"

# 1. META — decide the highest-leverage lever from the real gap analysis.
$PY -m backend.brain_convergence.research_meta 2>/dev/null | sed 's/^/  /'
CHOSEN="$($PY -c "import json;print(json.load(open('data/prompt_brain/research_meta_decision.json'))['chosen_lever'])" 2>/dev/null || echo UNKNOWN)"

# 2. EXECUTE the chosen lever ($0 local-model path; each no-ops cleanly if the model is down).
case "$CHOSEN" in
  EXPAND)
    echo "  lever=EXPAND — growing thin pools, then improving"
    $PY -m backend.brain_convergence.expand_run 8 6 2>/dev/null | sed 's/^/    /' || true
    $PY -m backend.brain_convergence.improve_run 6 2>/dev/null | sed 's/^/    /' || true ;;
  IMPROVE|SELECT)
    echo "  lever=$CHOSEN — best-of-N improvement sweep"
    $PY -m backend.brain_convergence.improve_run 6 2>/dev/null | sed 's/^/    /' || true ;;
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
