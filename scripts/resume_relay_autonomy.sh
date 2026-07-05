#!/usr/bin/env bash
# resume_relay_autonomy.sh — one-command recovery for a dead/parked relay daemon.
# Run this ON the relay (hoch-relay-001). Read-mostly; the only mutations are
# clearing the operator hold and restarting the daemon service (both operator-safe).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
echo "== HAS relay autonomy resume =="
echo "[repo] $ROOT @ $(git --no-optional-locks rev-parse --short HEAD 2>/dev/null || echo '?')"

# 1. Is the new TTL-hold code present? (needed so simulated e-stops self-heal)
if [ -f backend/runtime_truth/operator_hold.py ]; then
  echo "[code] TTL-hold code present ✓"
else
  echo "[code] MISSING TTL-hold code — run: git pull --ff-only   (then re-run this script)"
fi

# 2. Show whether the daemon is actually alive (heartbeat freshness, NOT the RUNNING flag)
python3 - <<'PY'
import json, datetime
try:
    s=json.load(open('has_live_project_tracker/data/ag_execution_daemon_state.json'))
    hb=s.get('last_heartbeat'); now=datetime.datetime.now(datetime.timezone.utc)
    age=(now-datetime.datetime.fromisoformat(hb.replace('Z','+00:00'))).total_seconds()
    print(f"[before] flag={s.get('daemon_status')} last_cycle={s.get('last_cycle_status')} "
          f"hb_age={age:.0f}s -> {'DEAD/STALE' if age>60 else 'live'}")
except Exception as e:
    print("[before] could not read daemon state:", e)
PY

# 3. Clear the operator hold HERE (where the daemon reads it)
echo "[hold] clearing operator hold on relay..."
python3 scripts/ag_operator_hold.py --disable \
  --reason "Resume autonomy: dead-daemon restart" --operator "Michael Hoch" || true
python3 scripts/verify_no_stuck_hold.py || true

# 4. Locate and restart the daemon's systemd unit (auto-detect; no guessing)
UNIT="$(systemctl list-unit-files --type=service 2>/dev/null \
        | grep -iE 'ag[-_]execution|dispatcher|helm|hasf' | awk '{print $1}' | head -1)"
if [ -n "${UNIT:-}" ]; then
  echo "[svc] restarting ${UNIT} ..."
  sudo systemctl restart "${UNIT}" && sleep 6
  systemctl --no-pager --lines=0 status "${UNIT}" 2>/dev/null | head -4
else
  echo "[svc] no systemd unit auto-detected. Start manually, e.g.:"
  echo "      nohup python3 scripts/ag_execution_daemon.py >> logs/ag_daemon.out 2>&1 &"
fi

# 5. Verify a FRESH heartbeat + that cycles are moving (truth, not the flag)
echo "[verify] waiting for a fresh cycle..."; sleep 6
python3 - <<'PY'
import json, datetime
s=json.load(open('has_live_project_tracker/data/ag_execution_daemon_state.json'))
hb=s.get('last_heartbeat'); now=datetime.datetime.now(datetime.timezone.utc)
age=(now-datetime.datetime.fromisoformat(hb.replace('Z','+00:00'))).total_seconds()
ok = age < 30
print(f"[after] last_cycle={s.get('last_cycle_status')} cycle_count={s.get('cycle_count')} "
      f"hb_age={age:.0f}s -> {'LIVE & CYCLING ✓' if ok else 'STILL NOT CYCLING — check service logs'}")
PY
echo "[done] If LIVE and hold INACTIVE, the daemon will start pulling PENDING tasks (Rung 1, mechanical)."
