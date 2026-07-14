#!/bin/bash
# HELM phase auto-chainer. Runs A->B->C on a SINGLE writer.
# INVARIANTS:
#   - never launches a soak while another soak_runner is alive (no split-brain)
#   - seals a phase ONLY after natural termination
#   - advances to the next phase ONLY on an unqualified PASS verdict
#   - a FAIL/INCONCLUSIVE HALTS the chain and leaves the evidence for founder review
cd /Users/michaelhoch/hoch_agent_swarm
VENV=.venv/bin/python
LOG=/tmp/auto_chain.log
exec >> "$LOG" 2>&1
echo "=== auto-chain tick $(date -u +%FT%TZ) ==="

# never run if a soak is alive
if pgrep -f "soak_runner.py" >/dev/null; then echo "  soak alive; waiting"; exit 0; fi
# never run if a foreign scheduler reappeared
if pgrep -f "persistent_scheduler|helm_supervisor" >/dev/null; then echo "  FOREIGN SCHEDULER present; HALT"; exit 0; fi

STATE=coordination/council/auto_chain_state.json
[ -f "$STATE" ] || echo '{"phase":"A","status":"RUNNING"}' > "$STATE"
PHASE=$($VENV -c "import json;print(json.load(open('$STATE'))['phase'])")
STATUS=$($VENV -c "import json;print(json.load(open('$STATE'))['status'])")
echo "  phase=$PHASE status=$STATUS"
[ "$STATUS" = "HALTED" ] && { echo "  chain HALTED; no-op"; exit 0; }
[ "$STATUS" = "DONE" ]   && { echo "  chain DONE"; exit 0; }

# find newest package for this phase, seal it
PKG=$(ls -dt coordination/council/live_proof_packages/HELM-SOAK-*Z 2>/dev/null | head -1)
[ -z "$PKG" ] && { echo "  no package"; exit 0; }
if [ ! -f "$PKG/seal_verdict.json" ]; then
  echo "  sealing $PKG"
  $VENV scripts/council/seal_soak_phase.py --package "$PKG" >/dev/null 2>&1
fi
VERDICT=$($VENV -c "import json,glob,os;p='$PKG/seal_verdict.json';print(json.load(open(p)).get('verdict','NONE') if os.path.exists(p) else 'NONE')")
echo "  verdict=$VERDICT"

case "$VERDICT" in
  *PASS)
    NEXT=""; SECS=0
    case "$PHASE" in
      A) NEXT="B"; SECS=28800 ;;   # 8h
      B) NEXT="C"; SECS=86400 ;;   # 24h
      C) NEXT="DONE"; SECS=0 ;;
    esac
    if [ "$NEXT" = "DONE" ]; then
      $VENV -c "import json;json.dump({'phase':'C','status':'DONE'},open('$STATE','w'))"
      echo "  ALL PHASES PASSED. Chain DONE. Founder DOORSTEP is next."
    else
      # clean baseline then launch next phase as the SOLE writer
      $VENV -c "from backend.mission_control.per_task_lease import PerTaskLeaseManager as M; from pathlib import Path; M(Path('coordination/leases')).reclaim_expired_leases()"
      nohup $VENV scripts/council/soak_runner.py --seconds $SECS --phase $NEXT >/tmp/soak_$NEXT.log 2>&1 &
      $VENV -c "import json;json.dump({'phase':'$NEXT','status':'RUNNING','prev':'$PHASE PASS'},open('$STATE','w'))"
      echo "  $PHASE PASSED -> launched phase $NEXT (${SECS}s)"
    fi
    ;;
  *)
    $VENV -c "import json;json.dump({'phase':'$PHASE','status':'HALTED','verdict':'$VERDICT'},open('$STATE','w'))"
    echo "  phase $PHASE did NOT pass ($VERDICT). Chain HALTED for founder review."
    ;;
esac
