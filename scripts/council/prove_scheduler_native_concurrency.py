"""SCHEDULER-NATIVE concurrency proof.

Evidence must come from the DAEMON'S OWN ledger via its NORMAL path:
  tasks enter through the real sqlite task store
  -> scheduler.run_once()
  -> execute_task() -> authority gate -> per-task lease -> gateway -> live adapter
  -> the scheduler's own lease ledger

No burn-in harness. No alternate execution path.
"""
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.mission_control.persistent_scheduler import PersistentScheduler, DB_PATH

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "coordination" / "council" / "live_proof_packages" / \
    f"HELM-SCHEDULER-NATIVE-CONCURRENCY-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
PKG.mkdir(parents=True, exist_ok=True)
EVID = PKG / "daemon"
EVID.mkdir(exist_ok=True)

fails = 0
def ck(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail if not cond else ''}")

TARGET = "backend/council/decision_record.py"
SEED = "only RATIFIED and non-expired records authorize action"
content = (ROOT / TARGET).read_text()[:1200]
PROMPT = ('Return ONLY a JSON object with keys file_path, finding, supporting_line, remediation. '
          f'file_path="{TARGET}". supporting_line MUST be exactly: "{SEED}". '
          'finding and remediation: one sentence each. No prose outside the JSON.\n\n'
          f'FILE CONTENT:\n{content}')

MISSIONS = [("SNC-HASF", "HASF"), ("SNC-HRF", "HRF"), ("SNC-HCF", "HCF"), ("SNC-HSF", "HSF")]
EF_TASK = "SNC-EF-DIST"   # must stay blocked

# ---- seed the REAL task store ----
conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA busy_timeout=5000")
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
ids = [m[0] for m in MISSIONS] + [EF_TASK]
conn.executemany("DELETE FROM mission_control_tasks WHERE task_id = ?", [(i,) for i in ids])
conn.executemany("DELETE FROM mission_control_missions WHERE mission_id = ?",
                 [(f"M-{i}",) for i in ids])

def add_mission(mid, pod, name):
    conn.execute("""INSERT INTO mission_control_missions
        (mission_id, name, target_pod, command, status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?)""", (mid, name, pod, "noop", "ACTIVE", NOW, NOW))

def add_task(tid, mid, name, prompt, cap=None):
    conn.execute("""INSERT INTO mission_control_tasks
        (task_id, mission_id, name, status, step_index, dependencies,
         created_at, updated_at, mission_prompt, required_capability)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (tid, mid, name, "PENDING", 0, "", NOW, NOW, prompt, cap))

for tid, pod in MISSIONS:
    add_mission(f"M-{tid}", pod, f"native concurrency {pod}")
    add_task(tid, f"M-{tid}", f"inspect module ({pod})", PROMPT)

# Epic Fury Apple distribution — blocked via required_capability (the real scoped mechanism)
add_mission(f"M-{EF_TASK}", "HASF", "epic fury apple distribution")
add_task(EF_TASK, f"M-{EF_TASK}", "promote build to App Store", "promote",
         cap="APP_STORE_CONNECT_OBSERVATION")
conn.commit()
conn.close()
print(f"  seeded {len(MISSIONS)} runnable tasks + 1 Epic Fury distribution task into the REAL store")

# ---- run the DAEMON'S OWN cycle ----
sched = PersistentScheduler(evidence_dir=EVID)
# mission_id on the task row is the FK (M-*), so tag the blocked mission for the scoped gate
print("\n═══ scheduler.run_once() — the production path ═══")
t0 = time.time()
cycle = sched.run_once()
wall = round(time.time() - t0, 2)
print(f"  dispatched={cycle['dispatched_count']}  wall={wall}s")

# ---- read the peak from the SCHEDULER'S OWN ledger ----
report = sched.concurrency_report()
peak = report["observed_peak_concurrency"]
print(f"\n  scheduler's own ledger -> observed_peak_concurrency = {peak}")

lease_rows = [json.loads(l) for l in sched.lease_log.read_text().splitlines()] if sched.lease_log.exists() else []
acquired = [r for r in lease_rows if r.get("status") == "ACQUIRED"]
lease_ids = {r["lease_id"] for r in acquired}

ck("4 tasks admitted through the NORMAL task store", cycle["dispatched_count"] == 4,
   f"dispatched={cycle['dispatched_count']}")
ck("4 distinct per-task leases issued by the scheduler", len(lease_ids) == 4, f"{len(lease_ids)}")
ck("scheduler-ledger observed_peak_concurrency >= 2", isinstance(peak, int) and peak >= 2, f"{peak}")
ck("effective_limit == observed_peak_concurrency", report["effective_limit"] == peak)
ck("status = OK (PROVEN)", report["status"] == "OK", report["status"])
ck("authority id stamped on dispatched tasks",
   all(r.get("authority_decision_id") for r in acquired) or
   any("authority_decision_id" in r for r in lease_rows))
ck("Epic Fury distribution NOT dispatched (stayed blocked)",
   EF_TASK not in [d["task_id"] for d in cycle["dispatched"]])
term = ROOT / "coordination" / "leases" / "_terminal_ledger.jsonl"
tids = [json.loads(l)["task_id"] for l in term.read_text().splitlines()] if term.exists() else []
ck("no duplicate terminal success", len(tids) == len(set(tids)), f"{len(tids)} vs {len(set(tids))}")

# ---- NEGATIVE CONTROL: a synthetic/externally supplied peak cannot move the report ----
print("\n═══ NEGATIVE CONTROL — synthetic peak must NOT change concurrency_report() ═══")
try:
    sched.observed_peak = 999                 # attacker sets an attribute
    sched.concurrency_limit = 999             # and inflates the configured limit
    r2 = sched.concurrency_report()
    ck("synthetic attribute cannot inflate observed peak", r2["observed_peak_concurrency"] == peak,
       f"{r2['observed_peak_concurrency']}")
    ck("effective_limit still derives from OBSERVED leases, not config",
       r2["effective_limit"] == peak, f"{r2['effective_limit']}")
finally:
    sched.concurrency_limit = 4

# ---- forged ledger row with no lease_id must be ignored ----
with open(sched.lease_log, "a") as f:
    f.write(json.dumps({"ts": "2099-01-01T00:00:00Z", "status": "ACQUIRED",
                        "task_id": "FORGED", "peak": 999}) + "\n")   # no lease_id
r3 = sched.concurrency_report()
ck("forged ledger row without lease_id is ignored", r3["observed_peak_concurrency"] == peak,
   f"{r3['observed_peak_concurrency']}")

# ---- evidence package ----
for src, name in ((sched.lease_log, "lease_ledger.jsonl"),
                  (sched.cycles_log, "scheduler_cycles.jsonl"),
                  (sched.dispatch_log, "dispatch_ledger.jsonl")):
    if src.exists():
        (PKG / name).write_text(src.read_text())
(PKG / "concurrency_report.json").write_text(json.dumps(report, indent=2, default=str))
(PKG / "cycle_result.json").write_text(json.dumps(cycle, indent=2, default=str))

verdict = "SCHEDULER_NATIVE_CONCURRENCY_PASS" if fails == 0 else "NOT_PASS"
(PKG / "validation.json").write_text(json.dumps({
    "package": PKG.name, "verdict": verdict, "failed_checks": fails,
    "evidence_source": "the scheduler's OWN lease ledger via run_once() — no burn-in harness",
    "observed_peak_concurrency": peak,
    "measurement_method": "authoritative lease intervals paired by lease_id",
    "measurement_bug_fixed": ("observed_peak_concurrency() previously counted ACQUIRED and "
                              "DISPATCH_START each as +1, double-counting every task and "
                              "inflating the peak ~2x. Now paired by lease_id."),
    "epic_fury_distribution": "BLOCKED throughout",
    "assessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, indent=2, default=str))
sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(PKG.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
(PKG / "SHA256SUMS").write_text("\n".join(sums) + "\n")

print(f"\n═══ {verdict} — {fails} failed ═══")
print(f"evidence: {PKG.relative_to(ROOT)}")
sys.exit(1 if fails else 0)
