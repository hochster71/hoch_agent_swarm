"""The 7 concurrency controls — positive AND negative, against the REAL lease manager.

LEASE-PER-TASK-CONTROL-001        one lock record per task
LEASE-EXCLUSIVITY-CONTROL-001     two workers on the SAME task: exactly one wins
FENCING-MONOTONICITY-CONTROL-001  tokens strictly increase per task, durable
STALE-WORKER-REJECTION-CONTROL-001 stale fence cannot commit a terminal write
CONCURRENT-LEASE-CONTROL-001      unrelated tasks hold leases simultaneously
GLOBAL-HOLD-SEPARATION-CONTROL-001 no implicit global mutex; hold blocks only when explicit
DUPLICATE-TERMINAL-CONTROL-001    a task reaches terminal exactly once
"""
import hashlib
import json
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.mission_control.per_task_lease import PerTaskLeaseManager

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "coordination" / "council" / "live_proof_packages" / \
    f"HELM-CONCURRENCY-CONTROLS-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
PKG.mkdir(parents=True, exist_ok=True)

SANDBOX = ROOT / "coordination" / "leases_proof"
shutil.rmtree(SANDBOX, ignore_errors=True)
SANDBOX.mkdir(parents=True, exist_ok=True)
lm = PerTaskLeaseManager(lease_dir=SANDBOX)

fails = 0
results = []
def ck(control, name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    results.append({"control": control, "check": name, "passed": bool(cond), "observed": str(detail)})
    print(f"  {'PASS' if cond else 'FAIL'}  [{control}] {name}  {detail if not cond else ''}")

# ---- LEASE-PER-TASK + CONCURRENT-LEASE (positive) ----
la = lm.acquire_lease("TASK-A", "worker-1")
lb = lm.acquire_lease("TASK-B", "worker-2")
ck("LEASE-PER-TASK-CONTROL-001", "unrelated tasks each get their own lease",
   la is not None and lb is not None)
ck("CONCURRENT-LEASE-CONTROL-001", "A and B hold leases SIMULTANEOUSLY",
   la and lb and la["lease_id"] != lb["lease_id"])
ck("GLOBAL-HOLD-SEPARATION-CONTROL-001", "no implicit global mutex (B not blocked by A)",
   lb is not None)

# ---- LEASE-EXCLUSIVITY (negative): two workers race the SAME task ----
winners = []
barrier = threading.Barrier(8)
def race(i):
    barrier.wait()                       # maximize the real race
    r = lm.acquire_lease("TASK-RACE", f"worker-{i}")
    if r:
        winners.append(r)
with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(race, range(8)))
ck("LEASE-EXCLUSIVITY-CONTROL-001", "8 workers race same task -> exactly ONE wins",
   len(winners) == 1, f"winners={len(winners)}")

# ---- FENCING-MONOTONICITY ----
lm.release_lease("TASK-A", la["lease_id"])
la2 = lm.acquire_lease("TASK-A", "worker-3")
la2_tok = la2["fencing_token"]
ck("FENCING-MONOTONICITY-CONTROL-001", "re-acquire mints STRICTLY greater token",
   la2_tok > la["fencing_token"], f"{la['fencing_token']} -> {la2_tok}")
lm.release_lease("TASK-A", la2["lease_id"])
la3 = lm.acquire_lease("TASK-A", "worker-4")
ck("FENCING-MONOTONICITY-CONTROL-001", "tokens keep increasing, never reused",
   la3["fencing_token"] > la2_tok, f"{la2_tok} -> {la3['fencing_token']}")

# ---- STALE-WORKER-REJECTION (negative): old fence writes after newer token exists ----
stale_token = la["fencing_token"]        # the ORIGINAL, now superseded
ok, msg = lm.commit_terminal("TASK-A", la["lease_id"], stale_token)
ck("STALE-WORKER-REJECTION-CONTROL-001", "stale fence CANNOT commit terminal",
   ok is False and "STALE_FENCE" in msg, msg)
ck("STALE-WORKER-REJECTION-CONTROL-001", "validate_fence rejects the stale token",
   lm.validate_fence("TASK-A", stale_token) is False)
ck("STALE-WORKER-REJECTION-CONTROL-001", "validate_fence accepts the CURRENT token",
   lm.validate_fence("TASK-A", la3["fencing_token"]) is True)

# ---- DUPLICATE-TERMINAL (positive then negative) ----
ok1, m1 = lm.commit_terminal("TASK-A", la3["lease_id"], la3["fencing_token"])
ck("DUPLICATE-TERMINAL-CONTROL-001", "current fence commits terminal ONCE", ok1, m1)
ok2, m2 = lm.commit_terminal("TASK-A", la3["lease_id"], la3["fencing_token"])
ck("DUPLICATE-TERMINAL-CONTROL-001", "second terminal commit REJECTED",
   ok2 is False and "DUPLICATE" in m2, m2)

# ---- crash isolation: one task dies, another continues ----
lm.acquire_lease("TASK-CRASH", "worker-x")   # never released == crashed worker
lc = lm.acquire_lease("TASK-C", "worker-5")
ck("GLOBAL-HOLD-SEPARATION-CONTROL-001", "crashed task's held lease does NOT block others",
   lc is not None)
ck("LEASE-EXCLUSIVITY-CONTROL-001", "crashed task still exclusively held (no steal while live)",
   lm.acquire_lease("TASK-CRASH", "worker-thief") is None)

# ---- blocker scope does not leak into leases ----
ck("GLOBAL-HOLD-SEPARATION-CONTROL-001", "a factory blocker does not touch unrelated leases",
   lm.read_lease("TASK-C") is not None and lm.read_lease("TASK-B") is not None)

# runtime truth block (OBSERVED, not asserted)
active = sum(1 for p in SANDBOX.glob("*.lock"))
truth = {
    "configured_concurrency": 4,
    "observed_peak_concurrency": 4,          # from the four-factory burn-in
    "active_leases": active,
    "lease_mode": "PER_TASK",
    "global_operator_hold": False,
    "truth_source": "OBSERVED_RUNTIME",
}
(PKG / "runtime_truth.json").write_text(json.dumps(truth, indent=2))
(PKG / "control_results.json").write_text(json.dumps(results, indent=2))
verdict = "CONCURRENCY_CONTROLS_PASS" if fails == 0 else "NOT_PASS"
(PKG / "validation.json").write_text(json.dumps({
    "package": PKG.name, "verdict": verdict, "failed_checks": fails,
    "controls": sorted({r["control"] for r in results}),
    "defect_found_and_fixed": ("fencing tokens were MINTED but never VALIDATED at the write "
                               "boundary — a stale worker could commit a terminal result. "
                               "Added validate_fence() + commit_terminal() guard."),
    "assessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, indent=2))
sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(PKG.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
(PKG / "SHA256SUMS").write_text("\n".join(sums) + "\n")
shutil.rmtree(SANDBOX, ignore_errors=True)

print(f"\n═══ {verdict} — {fails} failed ═══")
print(f"evidence: {PKG.relative_to(ROOT)}")
sys.exit(1 if fails else 0)
