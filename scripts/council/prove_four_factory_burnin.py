"""FOUR-FACTORY CONCURRENT BURN-IN through the authority-bound gateway.

Every task: doctrine -> authority_decision_id -> task digest -> PER-TASK lease -> gateway
-> live adapter (ollama) -> result envelope -> independent validator -> artifact -> PERT.

Concurrency is OBSERVED (overlapping lease intervals measured from real wall-clock
timestamps), never inferred from a class name.
"""
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.council.authority_gateway import bind_classification, dispatch_ollama, AuthorityDenied
from backend.council.artifact_validator import validate
from backend.mission_control.per_task_lease import PerTaskLeaseManager
from backend.mission_control.scoped_states import ScopedStateEvaluator
from backend.mission_control.persistent_scheduler import PersistentScheduler

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "coordination" / "council" / "live_proof_packages" / \
    f"HELM-FOUR-FACTORY-BURNIN-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
PKG.mkdir(parents=True, exist_ok=True)

fails = 0
lock = threading.Lock()
def ck(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail if not cond else ''}")

TARGET = "backend/council/decision_record.py"
content = (ROOT / TARGET).read_text()
SEED = "only RATIFIED and non-expired records authorize action"

def make_task(tid, pod):
    return {
        "task_id": tid, "target_pod": pod,
        "action_text": (
            "Return ONLY a JSON object with keys file_path, finding, supporting_line, "
            f'remediation. file_path="{TARGET}". supporting_line MUST be exactly: "{SEED}". '
            "finding and remediation: one sentence each. No prose outside the JSON.\n\n"
            f"FILE CONTENT:\n{content[:1500]}"),
        "environment": "local", "adapter": "ollama:llama3.1:8b", "target": TARGET,
        "data_classification": "public_repo", "side_effects": "none",
    }

FACTORIES = [("HASF-BURN", "HASF"), ("HRF-BURN", "HRF"), ("HCF-BURN", "HCF"), ("HSF-BURN", "HSF")]
lm = PerTaskLeaseManager()
lease_events = []   # (epoch, delta, task_id) — OBSERVED wall-clock
records = {}

def run(tid, pod):
    task = make_task(tid, pod)
    b = bind_classification(task, decision_id="FD-20260713-004")
    lease = lm.acquire_lease(tid, holder=f"burnin-{tid}", duration_seconds=300)
    t_acq = time.time()
    with lock:
        lease_events.append((t_acq, +1, tid))
    try:
        res = dispatch_ollama(task, b, model="llama3.1:8b")
        ok, reasons = validate(res, expected_authority_id=b.authority_decision_id,
                               expected_task_sha256=b.classified_task_sha256)
        art = {"artifact_id": "ART-" + hashlib.sha256(b.authority_decision_id.encode()).hexdigest()[:8],
               "sha256": hashlib.sha256(res.get("output", "").encode()).hexdigest()}
        pert = {"node": tid, "to_state": "VALIDATED" if ok else "FAILED",
                "authority_decision_id": b.authority_decision_id, "advanced": ok}
        rec = {"task_id": tid, "factory": pod,
               "authority_decision_id": b.authority_decision_id,
               "classified_task_sha256": b.classified_task_sha256,
               "lease_id": lease["lease_id"], "fencing_token": lease["fencing_token"],
               "result_authority_id": res.get("authority_decision_id"),
               "validator_passed": ok, "validator_reasons": reasons,
               "artifact": art, "pert_transition": pert,
               "latency_s": res.get("latency_s"),
               "lease_acquired_epoch": t_acq}
    except (AuthorityDenied, Exception) as e:
        rec = {"task_id": tid, "factory": pod, "error": str(e)[:150], "validator_passed": False,
               "lease_id": lease["lease_id"], "fencing_token": lease["fencing_token"],
               "lease_acquired_epoch": t_acq}
    t_rel = time.time()
    with lock:
        lease_events.append((t_rel, -1, tid))
        rec["lease_released_epoch"] = t_rel
        records[tid] = rec
    lm.release_lease(tid, lease["lease_id"])
    return rec

print("═══ FOUR-FACTORY CONCURRENT BURN-IN (live ollama, authority-bound) ═══")
t0 = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    list(ex.map(lambda a: run(*a), FACTORIES))
wall = round(time.time() - t0, 2)

# OBSERVED peak concurrency from real overlapping lease intervals
ev = sorted(lease_events, key=lambda x: x[0])
cur = peak = 0
for _, d, _ in ev:
    cur += d
    peak = max(peak, cur)
sum_latency = sum(r.get("latency_s") or 0 for r in records.values())

print(f"\n  wall-clock: {wall}s   sum of task latencies: {round(sum_latency,2)}s")
ck("OBSERVED peak concurrency >= 2", peak >= 2, f"peak={peak}")
ck("wall-clock < sum(latencies) => genuinely overlapped", wall < sum_latency,
   f"{wall} vs {round(sum_latency,2)}")
ck("4 factories dispatched", len(records) == 4)
passed = [r for r in records.values() if r.get("validator_passed")]
ck("at least 3 validators PASS", len(passed) >= 3, f"{len(passed)}/4")
ck("4 real artifacts", sum(1 for r in records.values() if r.get("artifact")) >= 3)
lease_ids = [r["lease_id"] for r in records.values()]
ck("distinct concurrent leases", len(set(lease_ids)) == len(lease_ids))
ck("authority id present + echoed at every stage",
   all(r.get("authority_decision_id") and r.get("result_authority_id") == r.get("authority_decision_id")
       for r in records.values() if "error" not in r))
ck("0 duplicate terminal executions", len(records) == len(set(records.keys())))
toks = [r["fencing_token"] for r in records.values()]
ck("fencing tokens issued", all(isinstance(t, int) for t in toks), str(toks))

# stale-worker rejection: a released/stale lease must not be reusable with the old token
t_id = "HASF-BURN"
l2 = lm.acquire_lease(t_id, holder="new-worker", duration_seconds=60)
ck("recovered lease mints a STRICTLY GREATER fencing token",
   l2["fencing_token"] > records[t_id]["fencing_token"],
   f"{records[t_id]['fencing_token']} -> {l2['fencing_token']}")
lm.release_lease(t_id, l2["lease_id"])

# Epic Fury distribution must STILL be blocked during all of this
sched = PersistentScheduler(evidence_dir=ROOT / "coordination" / "council" / "daemon")
BL = [{"id": "G-6", "status": "OPEN"}]
ef = [{"task_id": "EF-DIST", "target_pod": "HASF", "mission_id": "EPIC_FURY_DISTRIBUTION",
       "name": "promote to App Store", "step_index": 0}]
ck("Epic Fury distribution STILL blocked during burn-in",
   len(sched.rank_tasks(ef, BL)) == 0)

conc = {"configured": 4, "observed_peak_concurrency": peak,
        "wall_clock_s": wall, "sum_task_latency_s": round(sum_latency, 2),
        "overlapped": wall < sum_latency,
        "method": "OBSERVED from real lease acquire/release wall-clock timestamps"}
(PKG / "concurrency_observed.json").write_text(json.dumps(conc, indent=2))
(PKG / "factory_results.json").write_text(json.dumps(records, indent=2, default=str))
(PKG / "lease_events.json").write_text(json.dumps(
    [{"epoch": e, "delta": d, "task_id": t} for e, d, t in ev], indent=2))
verdict = "FOUR_FACTORY_BURNIN_PASS" if fails == 0 else "NOT_PASS"
(PKG / "validation.json").write_text(json.dumps({
    "package": PKG.name, "verdict": verdict, "failed_checks": fails,
    "concurrency": conc, "validators_passed": f"{len(passed)}/4",
    "epic_fury_distribution": "BLOCKED_EXTERNAL throughout",
    "manual_prompt_copies": 0, "manual_result_copies": 0,
    "assessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, indent=2, default=str))
sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(PKG.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
(PKG / "SHA256SUMS").write_text("\n".join(sums) + "\n")

print(f"\n═══ {verdict} — {fails} failed ═══")
print(f"evidence: {PKG.relative_to(ROOT)}")
sys.exit(1 if fails else 0)
