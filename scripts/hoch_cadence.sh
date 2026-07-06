#!/usr/bin/env bash
# hoch_cadence.sh — ONE HOCH tick across the whole portfolio (AI Michael's heartbeat).
#
# Drives every factory, then lets the founder orchestrator decide the next move:
#   1. software brain — full meta loop (expand/improve/select/converge)  [brain_cadence.sh]
#   2. every other factory — crown/refresh champions from its own scorer  [domain_select]
#   3. AI Michael — cross-factory founder decision (autonomous vs escalate)
#   4. publish the live feed for the command deck
#
# Safe: each stage degrades cleanly if the local model is down (mechanical work still advances).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
export PATH="$HOME/.local/bin:$PATH"
PY="$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)"
STAMP="$(date -u +%FT%TZ)"

echo "[$STAMP] HOCH cadence tick — portfolio"

# 1. Software brain (its own single-flight lock guards overlap).
bash scripts/brain_cadence.sh 2>/dev/null | sed 's/^/  /' || echo "  brain_cadence: skipped"

# 2. Run the full improvement cycle for every non-software factory (expand thin classes with the
#    $0 local model -> re-select -> converge with history). Same loop as the software brain, so
#    HMF/HRF earn a real improvement graph. Degrades to re-select when no model is up.
for dom in music research; do
  $PY -m backend.brain_convergence.domain_cycle "$dom" 2>/dev/null | sed 's/^/  /' || true
done

# 3. Cyber Swarm — continuous adversarial hardening (Red proves Blue; Blue scans HAS itself).
$PY -m backend.swarm.cyber_swarm backend 2>/dev/null | sed 's/^/  /' || echo "  swarm: skipped"

# 3b. Self-heal — detect literal secrets in HOCH's own source, quarantine/escalate, immunize.
$PY -m backend.swarm.self_heal 2>/dev/null | head -1 | sed 's/^/  /' || echo "  self-heal: skipped"

# 4. AI Michael — founder orchestration across the whole portfolio.
$PY -m backend.orchestrator.founder_orchestrator 2>/dev/null | sed 's/^/  /' || echo "  orchestrator: skipped"

# 5. Agent-activity audit + NIST 800-53 Rev 5 arterial map.
$PY -m backend.orchestrator.agent_audit 2>/dev/null | head -1 | sed 's/^/  /' || true
$PY -m backend.swarm.nist_map 2>/dev/null | head -1 | sed 's/^/  /' || true

# 4. Publish the live feed (factories + orchestrator brief) for the command deck.
$PY scripts/write_brain_live.py 2>/dev/null | sed 's/^/  /' || true
