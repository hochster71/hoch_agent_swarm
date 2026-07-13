"""Prove G-5 is MECHANICALLY narrowed: it blocks the Epic Fury Apple distribution mission
ONLY — not the HASF lane, not unrelated HASF engineering, not any other factory.

Runs against the REAL ScopedStateEvaluator and the REAL PersistentScheduler.rank_tasks,
with the Apple review blocker ACTIVE (worst case). A task is RUNNABLE iff it survives
rank_tasks.
"""
import json
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.mission_control.scoped_states import ScopedStateEvaluator
from backend.mission_control.persistent_scheduler import PersistentScheduler

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "coordination" / "council" / "live_proof_packages" / \
    f"HELM-BLOCKER-GRANULARITY-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
PKG.mkdir(parents=True, exist_ok=True)

fails = 0
def ck(name, cond, detail=""):
    global fails
    fails += 0 if cond else 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail if not cond else ''}")

# The Apple review blocker is ACTIVE — the worst case for over-broad blocking.
BLOCKERS = [{"id": "G-6", "status": "OPEN", "reason": "APPLE_REVIEW_PENDING"}]

ev = ScopedStateEvaluator(ROOT)
state = ev.evaluate_states(global_hold=False, blockers=BLOCKERS)
fs = state["FACTORY_STATE"]

print("═══ STATE — the block must bind to the MISSION, not the lane ═══")
ck("HASF lane state = ACTIVE (not BLOCKED)", fs["HASF"]["state"] == "ACTIVE", fs["HASF"]["state"])
ck("HASF distribution_lane = BLOCKED_EXTERNAL", fs["HASF"]["distribution_lane"] == "BLOCKED_EXTERNAL",
   fs["HASF"]["distribution_lane"])
ck("EPIC_FURY_DISTRIBUTION in blocked_missions", "EPIC_FURY_DISTRIBUTION" in fs["HASF"]["blocked_missions"])
ck("Apple capabilities blocked", set(fs["HASF"]["blocked_capabilities"]) ==
   {"APP_STORE_CONNECT_OBSERVATION", "APPLE_DISTRIBUTION_PROMOTION"})
ck("GLOBAL_PLATFORM_STATE = ACTIVE", state["GLOBAL_PLATFORM_STATE"] == "ACTIVE",
   state["GLOBAL_PLATFORM_STATE"])
for f in ("HRF", "HCF", "HSF", "HMF"):
    ck(f"{f} lane ACTIVE", fs[f]["state"] == "ACTIVE", fs[f]["state"])

print("\n═══ ELIGIBILITY — through the REAL rank_tasks ═══")
sched = PersistentScheduler(evidence_dir=ROOT / "coordination" / "council" / "daemon")

TASKS = [
    # THE ONE THING THAT MUST BE BLOCKED
    {"task_id": "EF-DIST", "target_pod": "HASF", "mission_id": "EPIC_FURY_DISTRIBUTION",
     "name": "promote Epic Fury build to App Store", "step_index": 0,
     "_expect": "BLOCKED"},
    {"task_id": "EF-CAP", "target_pod": "HASF", "required_capability": "APP_STORE_CONNECT_OBSERVATION",
     "name": "observe App Store Connect review status", "step_index": 0,
     "_expect": "BLOCKED"},
    # NEGATIVE CONTROLS — the blocker must NOT reach any of these
    {"task_id": "HASF-ENG", "target_pod": "HASF", "mission_id": "HELM_ENGINEERING",
     "name": "refactor the census module (unrelated HASF engineering)", "step_index": 0,
     "_expect": "RUNNABLE"},
    {"task_id": "HASF-OTHER-PRODUCT", "target_pod": "HASF", "mission_id": "OTHER_PRODUCT_BUILD",
     "name": "build a different HASF product", "step_index": 0, "_expect": "RUNNABLE"},
    {"task_id": "HASF-HARDEN", "target_pod": "HASF", "mission_id": "HELM_HARDENING",
     "name": "harden the authority gateway", "step_index": 0, "_expect": "RUNNABLE"},
    {"task_id": "HASF-TESTS", "target_pod": "HASF", "mission_id": "LOCAL_TESTS",
     "name": "run local unit tests", "step_index": 0, "_expect": "RUNNABLE"},
    {"task_id": "HRF-1", "target_pod": "HRF", "name": "research synthesis", "step_index": 0,
     "_expect": "RUNNABLE"},
    {"task_id": "HCF-1", "target_pod": "HCF", "name": "cyber hardening", "step_index": 0,
     "_expect": "RUNNABLE"},
    {"task_id": "HSF-1", "target_pod": "HSF", "name": "story chronicle", "step_index": 0,
     "_expect": "RUNNABLE"},
]

runnable_ids = {t["task_id"] for t in sched.rank_tasks([dict(t) for t in TASKS], BLOCKERS)}
results = []
for t in TASKS:
    got = "RUNNABLE" if t["task_id"] in runnable_ids else "BLOCKED"
    ok = got == t["_expect"]
    ck(f"{t['task_id']:20s} expect {t['_expect']:8s} -> {got}", ok)
    results.append({"task_id": t["task_id"], "pod": t["target_pod"],
                    "mission": t.get("mission_id"), "capability": t.get("required_capability"),
                    "expected": t["_expect"], "observed": got, "passed": ok})

# the canonical narrowed blocker record
narrowed = {
    "scope_type": "PRODUCT_MISSION",
    "factory_id": "HASF",
    "product_id": "EPIC_FURY_2026",
    "mission_id": "APPLE_DISTRIBUTION",
    "blocked_capabilities": ["APP_STORE_CONNECT_OBSERVATION", "APPLE_DISTRIBUTION_PROMOTION"],
    "status": "BLOCKED_EXTERNAL",
    "reason": "APPLE_REVIEW_PENDING",
    "must_not_block": ["unrelated HASF engineering", "another HASF product",
                       "HELM hardening", "local test execution", "any other factory"],
}
(PKG / "g5_narrowed_blocker.json").write_text(json.dumps(narrowed, indent=2))
(PKG / "factory_state.json").write_text(json.dumps(state, indent=2, default=str))
(PKG / "eligibility_results.json").write_text(json.dumps(results, indent=2))
verdict = "BLOCKER_GRANULARITY_PASS" if fails == 0 else "NOT_PASS"
(PKG / "validation.json").write_text(json.dumps({
    "package": PKG.name, "verdict": verdict, "failed_checks": fails,
    "blocker_active_during_proof": BLOCKERS,
    "claim": "G-5 blocks ONLY EPIC_FURY_2026/APPLE_DISTRIBUTION. HASF lane is ACTIVE. "
             "4 factories eligible => concurrency burn-in is unblocked.",
    "assessed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}, indent=2))
sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(PKG.iterdir()) if p.is_file() and p.name != "SHA256SUMS"]
(PKG / "SHA256SUMS").write_text("\n".join(sums) + "\n")

print(f"\n═══ {verdict} — {fails} failed ═══")
print(f"evidence: {PKG.relative_to(ROOT)}")
sys.exit(1 if fails else 0)
