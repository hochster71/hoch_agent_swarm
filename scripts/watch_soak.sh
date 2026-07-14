#!/usr/bin/env bash
# Live soak view. Run it in a terminal and watch. Refreshes every 5s.
#   bash scripts/watch_soak.sh
#
# Everything here is OBSERVED from the daemon's own ledgers. Nothing is asserted.
cd "$(dirname "$0")/.." || exit 1

while true; do
  PKG=$(ls -td coordination/council/live_proof_packages/HELM-SOAK-8H-* 2>/dev/null | head -1)
  PID=$(pgrep -f "soak_runner.py" | head -1)

  clear
  printf '\033[1m  HELM · PHASE B SOAK · LIVE\033[0m\n'
  printf '  ─────────────────────────────────────────────────────────────\n'

  if [ -z "$PID" ]; then
    # A status display that cannot tell SUCCESS from DEATH is one you cannot trust.
    if [ -f "$PKG/validation.json" ]; then
      V=$(python3 -c "import json;print(json.load(open('$PKG/validation.json'))['verdict'])" 2>/dev/null)
      printf '  \033[32mSTATUS   COMPLETE\033[0m  %s\n' "$V"
    else
      printf '  \033[31mSTATUS   DIED (no validation.json — did not finish)\033[0m\n'
    fi
  else
    ET=$(ps -p "$PID" -o etime= | tr -d ' ')
    printf '  STATUS   \033[32mRUNNING\033[0m   pid %s   elapsed %s / 8h\n' "$PID" "$ET"
  fi
  printf '  PACKAGE  %s\n\n' "$(basename "${PKG:-none}")"

  [ -d "$PKG" ] && python3 - "$PKG" <<'PY'
import json, sys, time
from pathlib import Path
p = Path(sys.argv[1])

def jl(n, sub=None):
    f = (p / sub / n) if sub else (p / n)
    if not f.exists():
        return []
    out = []
    for l in f.read_text().splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                pass
    return out

cyc = jl("scheduler_cycles.jsonl")
rec = jl("recovery_events.jsonl")
res = jl("resource_usage.jsonl")
led = jl("task_lease_ledger.jsonl", "daemon")

op, cl, meta, last = {}, {}, {}, ""
auth = 0
for e in led:
    lid, st, ts = e.get("lease_id"), e.get("status"), e.get("ts")
    if not lid or not ts:
        continue
    last = max(last, ts); meta[lid] = e.get("task_id", "")
    if st == "ACQUIRED":
        op.setdefault(lid, ts)
        if e.get("authority_decision_id"):
            auth += 1
    elif st in ("RELEASED", "COMPLETED", "FAILED"):
        cl.setdefault(lid, ts)

now = time.time()
def age(t):
    try:
        return now - time.mktime(time.strptime(t.split(".")[0] + "Z", "%Y-%m-%dT%H:%M:%SZ"))
    except Exception:
        return 0
leaked = [l for l in op if l not in cl and age(op[l]) > 300]
inflight = [l for l in op if l not in cl and age(op[l]) <= 300]

# observed peak from authoritative lease intervals
ev = []
for l, a in op.items():
    ev.append((a, +1)); ev.append((cl.get(l, last), -1))
ev.sort(key=lambda x: (x[0], x[1]))
c = peak = 0
for _, d in ev:
    c += d; peak = max(peak, c)

disp = [x.get("dispatched", 0) for x in cyc]
stalls = sum(1 for d in disp if d == 0)
seed_err = sum(1 for x in cyc if x.get("seed_error"))
fired = sorted({r.get("injection") for r in rec})
G, R, Y, X = "\033[32m", "\033[31m", "\033[33m", "\033[0m"

def line(label, val, ok):
    col = G if ok else R
    print(f"  {label:<26} {col}{val}{X}")

line("cycles", len(cyc), len(cyc) > 0)
line("dispatched (last 10)", " ".join(map(str, disp[-10:])) or "—", stalls == 0)
line("stalled cycles", stalls, stalls == 0)
line("seed errors (db-lock)", seed_err, seed_err == 0)
print()
line("leases acquired", len(op), True)
line("leases released", len(cl), True)
line("in-flight", len(inflight), True)
line("LEAKED  (killed run 1)", len(leaked), len(leaked) == 0)
line("observed peak concurrency", peak, peak >= 2)
line("authority-bound leases", f"{auth}/{len(op)}", auth == len(op))
print()
line("injections fired", f"{len(fired)}/8  {fired}", True)
if res:
    r = res[-1]
    print(f"  {'cpu / mem':<26} {r.get('cpu_percent')}%  {r.get('memory_mb')} MB")
    print(f"  {'ledger growth':<26} {r.get('ledger_growth_bytes', 0)/1024:.0f} KB")
print()
print(f"  \033[2m24/7 STATUS: NOT YET PROVEN — Phase B must seal PASS first\033[0m")
PY

  printf '\n  \033[2mrefreshing every 5s · ctrl-c to exit\033[0m\n'
  sleep 5
done
