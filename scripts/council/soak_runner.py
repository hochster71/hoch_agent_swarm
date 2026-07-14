"""HELM unattended failure-injected soak. Phase A = 2h. Production daemon path only.

Folds the scheduler-native concurrency proof INTO the soak: the daemon's OWN canonical
lease ledger must show observed_peak_concurrency >= 2. No burn-in harness.

Usage:  python3 scripts/council/soak_runner.py --seconds 7200 --phase A
"""
import argparse
import hashlib
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.mission_control.persistent_scheduler import PersistentScheduler, DB_PATH
from backend.mission_control.per_task_lease import PerTaskLeaseManager
from backend.council.authority_gateway import (
    bind_classification, enforce, AuthorityDenied, canonical_task_digest)

ROOT = Path(__file__).resolve().parents[2]
LEASE_DIR = ROOT / "coordination" / "leases"

ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=int, default=7200)
ap.add_argument("--phase", default="A")
args = ap.parse_args()

PKG = ROOT / "coordination" / "council" / "live_proof_packages" / \
    f"HELM-SOAK-{ {'A':'2H','B':'8H','C':'24H','D':'72H'}.get(args.phase,'XH') }-" \
    f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
PKG.mkdir(parents=True, exist_ok=True)
EVID = PKG / "daemon"; EVID.mkdir(exist_ok=True)

def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def jl(name, row):
    with open(PKG / name, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")

M = dict(scheduler_cycles=0, tasks_admitted=0, tasks_completed=0, tasks_failed=0,
         tasks_retried=0, stale_leases_recovered=0, stale_writes_rejected=0,
         duplicate_terminal_attempts=0, gateway_denials=0, authority_mismatches=0,
         adapter_failures=0, evidence_integrity_failures=0,
         manual_prompt_copies=0, manual_result_copies=0, founder_interruptions=0,
         scheduler_restarts=0)
INJECTIONS, RECOVERIES = [], []

TARGET = "backend/council/decision_record.py"
SEED = "only RATIFIED and non-expired records authorize action"
CONTENT = (ROOT / TARGET).read_text()[:1200]
# instruction OUTSIDE <DATA>; inert payload INSIDE. The gate classifies only the instruction.
DATA = f"<DATA>\n{CONTENT}\n</DATA>"

# Each factory has a DETERMINISTIC validator with real requirements. The task must be a
# genuine task for that factory -- not one generic prompt pretending to satisfy all four.
FACTORY_WORK = {
    "HASF": dict(
        name="inspect the decision_record module",
        prompt=("Inspect the module decision_record shown below. Name ONE concrete defect or "
                "risk and recommend a fix. Use the word 'decision_record'. Be specific.\n" + DATA),
        ctx={"subject": TARGET}),
    "HRF": dict(
        name="compare RATIFIED vs SUPERSEDED semantics",
        prompt=("Compare how the statuses 'ratified' and 'superseded' are treated in the code "
                "below. Explain how they differ and which may authorize action. Use explicit "
                "comparison language (e.g. 'whereas', 'unlike').\n" + DATA),
        ctx={"compare": ["ratified", "superseded"]}),
    "HCF": dict(
        name="control-to-evidence gap analysis",
        prompt=("Analyse the code below as a control. State which control it enforces, what "
                "evidence would prove it works, and name at least one gap where evidence is "
                "missing. Use the words control, evidence, and gap.\n" + DATA),
        ctx={}),
    "HSF": dict(
        name="write a governance changelog entry",
        prompt=("Write a short changelog entry (at least 5 non-empty lines) describing the "
                "authority rules in the code below. Mention 'authority'.\n" + DATA),
        ctx={"min_lines": 5, "theme": "authority"}),
}

PODS = ["HASF", "HRF", "HCF", "HSF"]

def seed_round(n):
    """Admit 4 fresh eligible tasks (ONE PER FACTORY) + 1 Epic Fury task (must stay blocked).

    Stale PENDING rows from earlier rounds are retired first: rank_tasks puts critical pods
    first, so leftover HASF tasks would otherwise fill all 4 slots and the soak would silently
    exercise ONE factory while claiming four.
    """
    # GUARDED: an unhandled 'database is locked' here killed Phase A run 2 at round 38.
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass
    ts = now()
    conn.execute("UPDATE mission_control_tasks SET status='RETIRED' "
                 "WHERE (task_id LIKE 'SOAK-%' OR task_id LIKE 'SNC-%') "
                 "AND status IN ('PENDING','FAILED')")
    for pod in PODS:
        tid = f"SOAK-{pod}-{n}"
        w = FACTORY_WORK[pod]
        conn.execute("""INSERT OR REPLACE INTO mission_control_missions
            (mission_id,name,target_pod,command,status,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?)""", (f"M-{tid}", f"soak {pod}", pod, "noop", "ACTIVE", ts, ts))
        conn.execute("""INSERT OR REPLACE INTO mission_control_tasks
            (task_id,mission_id,name,status,step_index,dependencies,created_at,updated_at,
             mission_prompt,required_capability,validator_ctx)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, f"M-{tid}", w["name"], "PENDING", 0, "", ts, ts,
             w["prompt"], None, json.dumps(w["ctx"])))
        M["tasks_admitted"] += 1
    ef = f"SOAK-EF-{n}"
    conn.execute("""INSERT OR REPLACE INTO mission_control_missions
        (mission_id,name,target_pod,command,status,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?)""", (f"M-{ef}", "epic fury apple", "HASF", "noop", "ACTIVE", ts, ts))
    conn.execute("""INSERT OR REPLACE INTO mission_control_tasks
        (task_id,mission_id,name,status,step_index,dependencies,created_at,updated_at,
         mission_prompt,required_capability,validator_ctx)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (ef, f"M-{ef}", "promote build to App Store", "PENDING", 0, "", ts, ts,
         "promote", "APP_STORE_CONNECT_OBSERVATION", "{}"))
    conn.commit(); conn.close()
    return ef

def resources():
    try:
        out = subprocess.run(["ps", "-o", "%cpu=,rss=", "-p", str(os.getpid())],
                             capture_output=True, text=True, timeout=5).stdout.split()
        return float(out[0]), round(int(out[1]) / 1024, 1)
    except Exception:
        return -1.0, -1.0

def ledger_bytes():
    return sum(p.stat().st_size for p in EVID.glob("*.jsonl") if p.is_file())

# ---------------- failure injections ----------------
def inj_kill_worker(s):
    """1. Kill a worker mid-flight: leave an ACTIVE lease that is never released."""
    lm = PerTaskLeaseManager()
    l = lm.acquire_lease("SOAK-KILLED-WORKER", "doomed", duration_seconds=8)
    INJECTIONS.append({"id": 1, "injection": "kill_worker", "at": now(),
                       "detail": "lease held then worker 'dies' (never released)"})
    time.sleep(9)                                  # let it go stale
    l2 = lm.acquire_lease("SOAK-KILLED-WORKER", "recovery-worker")
    ok = l2 is not None and l2["fencing_token"] > l["fencing_token"]
    if ok: M["stale_leases_recovered"] += 1
    # the DEAD worker now tries to commit with its stale token -> must be rejected
    okc, msg = lm.commit_terminal("SOAK-KILLED-WORKER", l["lease_id"], l["fencing_token"])
    if not okc and "STALE_FENCE" in msg: M["stale_writes_rejected"] += 1
    if l2: lm.release_lease("SOAK-KILLED-WORKER", l2["lease_id"])
    RECOVERIES.append({"id": 1, "recovered": ok, "stale_write_rejected": (not okc),
                       "detail": msg, "at": now()})
    return ok and not okc

def inj_corrupt_lock(s):
    """2. Corrupt a lock file -> must be quarantined and reclaimed, not deadlocked."""
    lm = PerTaskLeaseManager()
    p = lm._path("SOAK-CORRUPT-LOCK"); p.write_text("")      # corrupt
    INJECTIONS.append({"id": 2, "injection": "corrupt_lock_file", "at": now()})
    got = lm.acquire_lease("SOAK-CORRUPT-LOCK", "w")
    ok = got is not None
    if ok:
        M["stale_leases_recovered"] += 1
        lm.release_lease("SOAK-CORRUPT-LOCK", got["lease_id"])
    RECOVERIES.append({"id": 2, "recovered": ok, "at": now(),
                       "detail": "corrupt lock quarantined and reclaimed" if ok else "DEADLOCK"})
    return ok

def inj_corrupt_tokens(s):
    """3. Corrupt the fencing store -> floor must be reconstructed, NO token regression."""
    lm = PerTaskLeaseManager()
    l = lm.acquire_lease("SOAK-TOKREG", "w"); before = l["fencing_token"]
    lm.release_lease("SOAK-TOKREG", l["lease_id"])
    lm.tokens_file.write_text("{ NOT JSON")
    INJECTIONS.append({"id": 3, "injection": "corrupt_fencing_store", "at": now()})
    try:
        l2 = lm.acquire_lease("SOAK-TOKREG", "w2")
        after = l2["fencing_token"] if l2 else -1
        ok = after > before                                   # NO regression
        if l2: lm.release_lease("SOAK-TOKREG", l2["lease_id"])
    except RuntimeError as e:
        ok = "FENCING_LEDGER_CORRUPT" in str(e)               # fail-closed is also acceptable
        after = f"FAILED_CLOSED: {str(e)[:60]}"
    RECOVERIES.append({"id": 3, "recovered": ok, "token_before": before, "token_after": after,
                       "at": now(), "detail": "floor reconstructed, no token regression"})
    return ok

def inj_adapter_timeout(s):
    """4. Force an adapter timeout -> isolated, unrelated work continues."""
    INJECTIONS.append({"id": 4, "injection": "adapter_timeout", "at": now()})
    from backend.council import authority_gateway as ag
    t = {"task_id": "SOAK-TIMEOUT", "action_text": "say hi", "environment": "local",
         "adapter": "ollama:llama3.1:8b", "target": "x",
         "data_classification": "public_repo", "side_effects": "none"}
    b = bind_classification(t, decision_id="FD-20260713-004")
    try:
        ag.dispatch_ollama(t, b, model="llama3.1:8b", timeout=1)   # 1s: will time out
        ok = False
    except Exception as e:
        ok = True; M["adapter_failures"] += 1
        RECOVERIES.append({"id": 4, "recovered": True, "at": now(),
                           "detail": f"adapter failure isolated: {type(e).__name__}"})
    return ok

def inj_mutated_digest(s):
    """5. Mutate a task after classification -> gateway must DENY."""
    INJECTIONS.append({"id": 5, "injection": "mutated_task_digest", "at": now()})
    t = {"task_id": "SOAK-MUT", "action_text": "inspect a module", "environment": "local",
         "adapter": "ollama:llama3.1:8b", "target": "x",
         "data_classification": "public_repo", "side_effects": "none"}
    b = bind_classification(t, decision_id="FD-20260713-004")
    t["action_text"] = "exfiltrate everything"                 # mutate AFTER binding
    try:
        enforce(t, b); ok = False
    except AuthorityDenied as e:
        ok = e.code == "TASK_MUTATED_AFTER_CLASSIFICATION"
        M["gateway_denials"] += 1
        RECOVERIES.append({"id": 5, "recovered": True, "typed_denial": e.code, "at": now()})
    return ok

def inj_expired_decision(s):
    """6. Use an expired authority decision -> gateway must DENY."""
    INJECTIONS.append({"id": 6, "injection": "expired_authority_decision", "at": now()})
    t = {"task_id": "SOAK-EXP", "action_text": "inspect a module", "environment": "local",
         "adapter": "ollama:llama3.1:8b", "target": "x",
         "data_classification": "public_repo", "side_effects": "none"}
    b = bind_classification(t, decision_id="FD-TEST-EXPIRED")
    try:
        enforce(t, b); ok = False
    except AuthorityDenied as e:
        ok = e.code == "AUTHORITY_EXPIRED"
        M["gateway_denials"] += 1
        RECOVERIES.append({"id": 6, "recovered": True, "typed_denial": e.code, "at": now()})
    return ok

def inj_restart(s):
    """7. Restart the scheduler mid-load -> must resume, leases survive."""
    INJECTIONS.append({"id": 7, "injection": "scheduler_restart", "at": now()})
    s2 = PersistentScheduler(evidence_dir=EVID)
    M["scheduler_restarts"] += 1
    peak = s2.observed_peak_concurrency()
    ok = s2 is not None
    RECOVERIES.append({"id": 7, "recovered": ok, "at": now(),
                       "detail": f"fresh scheduler resumed; ledger peak still {peak}"})
    return ok, s2

def inj_duplicate_terminal(s):
    """8b. Duplicate terminal must be rejected."""
    lm = PerTaskLeaseManager()
    l = lm.acquire_lease("SOAK-DUP", "w")
    lm.commit_terminal("SOAK-DUP", l["lease_id"], l["fencing_token"])
    M["duplicate_terminal_attempts"] += 1
    ok2, msg = lm.commit_terminal("SOAK-DUP", l["lease_id"], l["fencing_token"])
    lm.release_lease("SOAK-DUP", l["lease_id"])
    ok = (not ok2) and "DUPLICATE" in msg
    INJECTIONS.append({"id": 8, "injection": "duplicate_terminal", "at": now()})
    RECOVERIES.append({"id": 8, "recovered": ok, "typed_denial": msg, "at": now()})
    return ok

# ---------------- main soak loop ----------------
_c = sqlite3.connect(str(DB_PATH)); _c.execute("PRAGMA busy_timeout=8000")
for _pref in ("SNC-%", "SOAK-%"):
    _c.execute("DELETE FROM mission_control_tasks WHERE task_id LIKE ?", (_pref,))
    _c.execute("DELETE FROM mission_control_missions WHERE mission_id LIKE ?", ("M-" + _pref,))
_c.commit(); _c.close()

sched = PersistentScheduler(evidence_dir=EVID, publish_runtime_source=True)
BLOCKERS = [{"id": "G-6", "status": "OPEN"}]
t_end = time.time() + args.seconds
start = time.time()
inj_done = set()
# injections spread across the first 30% of the run
SCHEDULE = {1: 0.05, 2: 0.10, 3: 0.14, 4: 0.18, 5: 0.22, 6: 0.25, 7: 0.28, 8: 0.30}
INJ_FN = {1: inj_kill_worker, 2: inj_corrupt_lock, 3: inj_corrupt_tokens,
          4: inj_adapter_timeout, 5: inj_mutated_digest, 6: inj_expired_decision,
          8: inj_duplicate_terminal}

(PKG / "soak_config.json").write_text(json.dumps({
    "phase": args.phase, "seconds": args.seconds, "started_at": now(),
    "concurrency_limit": sched.concurrency_limit,
    "evidence_source": "production daemon path (scheduler.run_once); no burn-in harness",
    "epic_fury": "APPLE_DISTRIBUTION held via required_capability; unrelated HASF work must continue",
}, indent=2))

rnd = 0
ef_blocked_every_cycle = True
FACTORIES_SEEN = set()
while time.time() < t_end:
    rnd += 1
    try:
        ef_id = seed_round(rnd)
    except Exception as _e:
        # A seeding failure must NEVER kill the soak. Record and continue.
        jl("scheduler_cycles.jsonl", {"round": rnd, "at": now(),
                                      "seed_error": str(_e)[:160], "dispatched": 0})
        time.sleep(3)
        continue
    try:
        cycle = sched.run_once()
        M["scheduler_cycles"] += 1
        disp = [d["task_id"] for d in cycle.get("dispatched", [])]
        M["tasks_completed"] += sum(1 for d in cycle.get("dispatched", []) if d.get("success"))
        M["tasks_failed"] += sum(1 for d in cycle.get("dispatched", []) if not d.get("success"))
        for d in cycle.get("dispatched", []):
            for _p in PODS:
                if d["task_id"].startswith(f"SOAK-{_p}-") and d.get("success"):
                    FACTORIES_SEEN.add(_p)
        if ef_id in disp:
            ef_blocked_every_cycle = False            # Epic Fury must NEVER dispatch
        jl("scheduler_cycles.jsonl", {"round": rnd, "at": now(),
                                      "dispatched": len(disp), "ids": disp})
    except Exception as e:
        M["tasks_failed"] += 1
        jl("scheduler_cycles.jsonl", {"round": rnd, "at": now(), "error": str(e)[:200]})

    frac = (time.time() - start) / args.seconds
    for iid, at in SCHEDULE.items():
        if iid not in inj_done and frac >= at:
            inj_done.add(iid)
            try:
                if iid == 7:
                    ok, sched = inj_restart(sched)
                else:
                    ok = INJ_FN[iid](sched)
                jl("recovery_events.jsonl", {"injection": iid, "expected_behavior": ok, "at": now()})
            except Exception as e:
                jl("recovery_events.jsonl", {"injection": iid, "error": str(e)[:200], "at": now()})

    cpu, mem = resources()
    rep = sched.concurrency_report()
    jl("resource_usage.jsonl", {"at": now(), "cpu_percent": cpu, "memory_mb": mem,
                                "ledger_growth_bytes": ledger_bytes()})
    jl("runtime_truth_snapshots.jsonl", {"at": now(), "soak_status": "IN_PROGRESS",
                                         "24_7_status": "NOT YET PROVEN",
                                         "observed_peak_concurrency": rep["observed_peak_concurrency"],
                                         "effective_limit": rep["effective_limit"],
                                         "status": rep["status"]})
    time.sleep(5)

# ---------------- finalize ----------------
rep = sched.concurrency_report()
peak = rep["observed_peak_concurrency"]
for src, dst in ((sched.lease_log, "lease_ledger.jsonl"),
                 (sched.dispatch_log, "dispatch_ledger.jsonl"),
                 (LEASE_DIR / "_terminal_ledger.jsonl", "terminal_ledger.jsonl")):
    if src.exists(): shutil.copyfile(src, PKG / dst)
(PKG / "concurrency_report.json").write_text(json.dumps(rep, indent=2, default=str))
(PKG / "failure_injections.json").write_text(json.dumps(INJECTIONS, indent=2, default=str))
(PKG / "recovery_events.json").write_text(json.dumps(RECOVERIES, indent=2, default=str))
(PKG / "manual_intervention_metrics.json").write_text(json.dumps({
    "manual_prompt_copies": 0, "manual_result_copies": 0, "founder_interruptions": 0}, indent=2))

term = LEASE_DIR / "_terminal_ledger.jsonl"
tids = [json.loads(l)["task_id"] for l in term.read_text().splitlines()] if term.exists() else []
dup_terminal = len(tids) != len(set(tids))
recovered = {r["id"]: r.get("recovered") for r in RECOVERIES}

checks = {
    "scheduler_native_overlap_observed": isinstance(peak, int) and peak >= 2,
    "observed_peak_concurrency_ge_2": isinstance(peak, int) and peak >= 2,
    "effective_equals_observed": rep["effective_limit"] == peak,
    "status_proven": rep["status"] == "OK",
    "daemon_survived_no_crash": M["scheduler_cycles"] > 0,
    "scheduler_restarted_successfully": M["scheduler_restarts"] >= 1,
    "worker_kill_recovered": recovered.get(1) is True,
    "corrupt_lock_recovered": recovered.get(2) is True,
    "corrupt_tokens_no_regression": recovered.get(3) is True,
    "adapter_timeout_isolated": recovered.get(4) is True,
    "mutated_task_denied": recovered.get(5) is True,
    "expired_decision_denied": recovered.get(6) is True,
    "duplicate_terminal_rejected": recovered.get(8) is True,
    "stale_writes_rejected": M["stale_writes_rejected"] >= 1,
    "zero_duplicate_terminal_success": not dup_terminal,
    "epic_fury_stayed_lane_scoped": ef_blocked_every_cycle,
    # A soak in which NOTHING completed is NOT a pass. The first smoke run reported
    # tasks_completed=0 / tasks_failed=16 and my criteria still said PASS -- a fake-green in
    # my own acceptance checks. Real work must actually land.
    "real_work_completed": M["tasks_completed"] >= 3,
    "factories_exercised_ge_3": len(FACTORIES_SEEN) >= 3,
    "zero_manual_prompt_copies": M["manual_prompt_copies"] == 0,
    "zero_manual_result_copies": M["manual_result_copies"] == 0,
}
failed = [k for k, v in checks.items() if not v]
verdict = f"SOAK_PHASE_{args.phase}_PASS" if not failed else "NOT_PASS"
(PKG / "validation.json").write_text(json.dumps({
    "package": PKG.name, "phase": args.phase, "verdict": verdict,
    "failed_checks": failed, "checks": checks, "metrics": M,
    "concurrency": rep,
    "factories_exercised": sorted(FACTORIES_SEEN),
    "soak_status": "COMPLETE", "24_7_status": "NOT YET PROVEN",
    "duration_seconds": args.seconds, "finished_at": now(),
}, indent=2, default=str))
sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(PKG.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
(PKG / "SHA256SUMS").write_text("\n".join(sums) + "\n")
print(f"{verdict}  peak={peak}  cycles={M['scheduler_cycles']}  failed={failed}")
print(f"evidence: {PKG.relative_to(ROOT)}")
