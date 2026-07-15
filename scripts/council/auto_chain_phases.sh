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

# FAKE-GREEN FIX (2026-07-14): the old logic did `ls -dt HELM-SOAK-*Z | head -1` (ANY newest package),
# read its seal, and matched `*PASS`. When the B/C soak launches silently failed and produced no new
# package, `head -1` kept returning Phase A (2H), so the chainer re-read SOAK_PHASE_A_PASS three times
# and fabricated B -> C -> DONE. Only the 2h Phase A ever actually ran. That is a fake green.
# The fix is strict phase binding: each phase reads ONLY its own duration-prefixed package, requires a
# verdict that NAMES that phase, and requires the package to belong to THIS chain (started at/after the
# recorded phase launch). A missing/old package HALTS for founder review instead of advancing.

case "$PHASE" in
  A) PREF="2H";  NEXT="B";    SECS=28800 ;;   # A(2h) -> B(8h)
  B) PREF="8H";  NEXT="C";    SECS=86400 ;;   # B(8h) -> C(24h)
  C) PREF="24H"; NEXT="DONE"; SECS=0 ;;
  *) echo "  unknown phase '$PHASE'; HALT"; exit 0 ;;
esac

# this phase's package = newest of its OWN duration prefix (never another phase's)
PKG=$(ls -dt coordination/council/live_proof_packages/HELM-SOAK-${PREF}-*Z 2>/dev/null | head -1)
[ -z "$PKG" ] && { echo "  no ${PREF} package for phase $PHASE yet; waiting"; exit 0; }

# it must belong to THIS chain: its start must be at/after the recorded phase launch time
PHASE_SINCE=$($VENV -c "import json;print(json.load(open('$STATE')).get('phase_started_at',''))" 2>/dev/null)
PKG_START=$($VENV -c "import json,os;p='$PKG/soak_config.json';print(json.load(open(p)).get('started_at','') if os.path.exists(p) else '')" 2>/dev/null)
if [ -n "$PHASE_SINCE" ] && [ -n "$PKG_START" ] && [[ "$PKG_START" < "$PHASE_SINCE" ]]; then
  echo "  newest ${PREF} package ($PKG_START) predates this phase launch ($PHASE_SINCE): the launched soak produced NO package -> HALT"
  $VENV -c "import json;s=json.load(open('$STATE'));s.update(status='HALTED',reason='phase $PHASE launch produced no fresh ${PREF} package (soak failed to start)');json.dump(s,open('$STATE','w'))"
  exit 0
fi

if [ ! -f "$PKG/seal_verdict.json" ]; then
  echo "  sealing $PKG (phase $PHASE)"
  $VENV scripts/council/seal_soak_phase.py --package "$PKG" --phase "$PHASE" >/dev/null 2>&1
fi
VERDICT=$($VENV -c "import json,os;p='$PKG/seal_verdict.json';print(json.load(open(p)).get('verdict','NONE') if os.path.exists(p) else 'NONE')")
echo "  phase=$PHASE pkg=$(basename "$PKG") verdict=$VERDICT"

# STRICT: the verdict must NAME this phase. SOAK_PHASE_A_PASS can NEVER advance phase B or C.
EXPECT="SOAK_PHASE_${PHASE}_PASS"
if [ "$VERDICT" = "$EXPECT" ]; then
  if [ "$NEXT" = "DONE" ]; then
    $VENV -c "import json;s=json.load(open('$STATE'));s.update(phase='C',status='DONE');json.dump(s,open('$STATE','w'))"
    echo "  ALL PHASES PASSED (A,B,C each proven by its OWN seal). Chain DONE. Founder DOORSTEP is next."
  else
    $VENV -c "from backend.mission_control.per_task_lease import PerTaskLeaseManager as M; from pathlib import Path; M(Path('coordination/leases')).reclaim_expired_leases()"
    NOW=$($VENV -c "import datetime;print(datetime.datetime.now(datetime.timezone.utc).isoformat())")
    # DETACHMENT FIX (2026-07-14): plain `nohup ... &` from a short-lived launchd tick gets REAPED when
    # the tick exits, so Phase B and C died instantly (empty logs). macOS has no `setsid` binary; use
    # Python's start_new_session=True (the posix setsid syscall) to fully detach a surviving soak.
    $VENV -c "import subprocess,os; f=open('/tmp/soak_$NEXT.log','w'); subprocess.Popen(['$VENV','scripts/council/soak_runner.py','--seconds','$SECS','--phase','$NEXT'],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,cwd=os.getcwd())"
    sleep 6   # let the runner create its package before the next tick evaluates it
    if ! pgrep -f "soak_runner.py --seconds $SECS --phase $NEXT" >/dev/null; then
      echo "  phase $NEXT FAILED TO STAY ALIVE after launch -> HALT (no fake advance)"
      $VENV -c "import json;s=json.load(open('$STATE'));s.update(status='HALTED',reason='phase $NEXT soak died on launch');json.dump(s,open('$STATE','w'))"
      exit 0
    fi
    $VENV -c "import json;json.dump({'phase':'$NEXT','status':'RUNNING','prev':'$PHASE $VERDICT','phase_started_at':'$NOW'},open('$STATE','w'))"
    echo "  $PHASE PASSED ($VERDICT) -> launched phase $NEXT (${SECS}s) at $NOW"
  fi
else
  $VENV -c "import json;s=json.load(open('$STATE'));s.update(status='HALTED',verdict='$VERDICT',expected='$EXPECT');json.dump(s,open('$STATE','w'))"
  echo "  phase $PHASE verdict='$VERDICT' != expected '$EXPECT'. Chain HALTED for founder review (no fake advance)."
fi
