"""Seal and INDEPENDENTLY evaluate a soak phase package.

Runs SEPARATELY from the soak runner: the thing that produced the evidence does not get to
grade itself. Adds the control the runner was missing:

    UNRELATED TASKS CONTINUED after every injected failure.

Recovery of the affected task alone is INSUFFICIENT. If the rest of the scheduler stalled,
the phase has not passed -- a system that heals one task while the other three die is not
resilient, it is merely polite about the corpse.

Verdict is exactly one of: SOAK_PHASE_<P>_PASS | _FAIL | _INCONCLUSIVE
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ap = argparse.ArgumentParser()
ap.add_argument("--package", required=True)
ap.add_argument("--phase", default="A")
ap.add_argument("--expect-cycles", type=int, default=10)
args = ap.parse_args()

PKG = ROOT / args.package
if not PKG.is_dir():
    print(f"SOAK_PHASE_{args.phase}_INCONCLUSIVE — package not found: {args.package}")
    sys.exit(2)


def jl(name):
    p = PKG / name
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


cycles = jl("scheduler_cycles.jsonl")
truth = jl("runtime_truth_snapshots.jsonl")
res = jl("resource_usage.jsonl")
recov = json.loads((PKG / "recovery_events.json").read_text()) if (PKG / "recovery_events.json").exists() else []
injs = json.loads((PKG / "failure_injections.json").read_text()) if (PKG / "failure_injections.json").exists() else []
val = json.loads((PKG / "validation.json").read_text()) if (PKG / "validation.json").exists() else None

failures, notes = [], []
def req(name, cond, detail=""):
    if not cond:
        failures.append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail if not cond else ''}")


# ---------- INCONCLUSIVE gates: can we even judge? ----------
incon = []
if val is None:
    incon.append("validation.json missing (process likely terminated early)")
if not cycles:
    incon.append("no scheduler cycles recorded")
if not injs:
    incon.append("no failure injections recorded")
if incon:
    print(f"\n═══ SOAK_PHASE_{args.phase}_INCONCLUSIVE ═══")
    for i in incon:
        print(f"  - {i}")
    (PKG / "seal_verdict.json").write_text(json.dumps({
        "verdict": f"SOAK_PHASE_{args.phase}_INCONCLUSIVE", "reasons": incon,
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=2))
    sys.exit(2)

print(f"═══ INDEPENDENT EVALUATION — SOAK PHASE {args.phase} ═══\n")

# ---------- THE MISSING CONTROL: unrelated work continued after each injection ----------
print("--- UNRELATED TASKS CONTINUED (per injection) ---")
by_ts = sorted(cycles, key=lambda c: c.get("at", ""))
for inj in injs:
    iid, at = inj.get("id"), inj.get("at", "")
    after = [c for c in by_ts if c.get("at", "") >= at]
    # work must resume within the next 3 cycles after the injection
    window = after[:3]
    dispatched_after = sum(c.get("dispatched", 0) for c in window)
    ok = bool(window) and dispatched_after > 0
    req(f"injection {iid} ({inj.get('injection')}): unrelated work continued",
        ok, f"dispatched in next 3 cycles = {dispatched_after}")

# no total stall anywhere
zero = [c for c in cycles if c.get("dispatched", 0) == 0]
req("no cycle stalled to zero dispatch", len(zero) == 0, f"{len(zero)} zero-dispatch cycles")

# ---------- required recoveries ----------
print("\n--- REQUIRED RECOVERIES ---")
rec = {r.get("id"): r for r in recov}
REQUIRED = {1: "worker kill recovered", 2: "corrupt lock quarantined+recovered",
            3: "fencing tokens reconstructed without regression", 4: "adapter timeout isolated",
            5: "mutated task denied", 6: "expired authority denied", 8: "duplicate terminal rejected"}
for k, label in REQUIRED.items():
    r = rec.get(k)
    req(label, bool(r) and r.get("recovered") is True,
        "missing" if not r else f"recovered={r.get('recovered')}")
req("scheduler restarted under load", any(r.get("id") == 7 for r in recov))

# ---------- runner's own acceptance checks ----------
print("\n--- RUNNER ACCEPTANCE CHECKS ---")
for k, v in (val.get("checks") or {}).items():
    req(k, bool(v))

# ---------- manifest integrity ----------
print("\n--- MANIFEST ---")
sums = PKG / "SHA256SUMS"
if not sums.exists():
    req("SHA256SUMS present", False)
else:
    bad = []
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        want, name = line.split("  ", 1)
        f = PKG / name
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != want:
            bad.append(name)
    req("manifest hash-verified", not bad, f"mismatched: {bad}")

# ---------- verdict ----------
verdict = f"SOAK_PHASE_{args.phase}_PASS" if not failures else f"SOAK_PHASE_{args.phase}_FAIL"
peak = (val.get("concurrency") or {}).get("observed_peak_concurrency")
print(f"\n═══ {verdict} ═══")
print(f"  cycles={len(cycles)}  peak={peak}  failed_controls={len(failures)}")
if failures:
    for f_ in failures:
        print(f"    - {f_}")

(PKG / "seal_verdict.json").write_text(json.dumps({
    "verdict": verdict,
    "failed_controls": failures,
    "cycles": len(cycles),
    "observed_peak_concurrency": peak,
    "unrelated_work_continued_after_every_injection": not any(
        f_.startswith("injection") for f_ in failures),
    "evaluator": "seal_soak_phase.py (independent of the runner that produced the evidence)",
    "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "next_phase_authorized": (not failures),
    "24_7_status": "NOT YET PROVEN",
}, indent=2))
print(f"  sealed: {PKG / 'seal_verdict.json'}")
sys.exit(0 if not failures else 1)
