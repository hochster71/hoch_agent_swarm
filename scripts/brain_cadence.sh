#!/usr/bin/env bash
# brain_cadence.sh — one self-improvement tick for the BRAIN.
# Logs whether a live local model is available (the $0 Generate path), then runs one M0
# convergence generation. Meant to be scheduled (launchd/systemd) so the burn-in does real
# convergence work each cycle instead of idling. Safe: read-only except the champion/convergence
# state it's designed to write; falls back to mechanical selection when no local model is up.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
export PATH="$HOME/.local/bin:$PATH"
PY="$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)"
STAMP="$(date -u +%FT%TZ)"

echo "[$STAMP] brain cadence tick"
echo -n "  live-brain: "
$PY -c "from backend.brain_convergence.local_model_bridge import status; import json; print(json.dumps(status()))" 2>/dev/null || echo '{"live_brain_available": false}'
# 1. GENERATE: if a local model is up, try to improve the weakest champions (dual-gated, $0)
$PY -m backend.brain_convergence.improve_run 3 2>/dev/null || echo "  improve_run: skipped"
# 2. SELECT/PROMOTE + converge (mechanical, always runs)
$PY -m backend.brain_convergence.run_m0 2>/dev/null | tail -1
# 3. publish the live feed for the moonshot console
$PY scripts/write_brain_live.py 2>/dev/null || true
