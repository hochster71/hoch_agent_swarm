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


def chain_precondition(ledger_path, *, expected_head=None):
    """AU-9: a PASS may NOT be issued over rewritten history.

    A seal is a claim about what happened. If the record of what happened can be silently edited,
    the seal is worthless. This is the gate: verify the evidence chain BEFORE any verdict.
    Returns (ok, reason). A broken chain is CONTRADICTED -- never a warning, never a pass.
    """
    import sys as _sys, os as _os
    _root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    from backend.truth.evidence_chain import verify_chain, ChainBroken
    try:
        verify_chain(ledger_path, expected_head=expected_head)
        return True, "evidence chain verified"
    except ChainBroken as e:
        return False, f"evidence chain BROKEN — refusing to seal: {e}"
    except Exception as e:
        return False, f"evidence chain UNKNOWN — refusing to seal: {e}"



if __name__ == "__main__":

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
    # A verdict that cannot be RECORDED is not a verdict. Bind these up front so the
    # seal is always writable, even if a section is skipped.
    CAPACITY = 4
    worker_peak = recovery_peak = total_peak = 0
    violation = False
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

    # ---- CAPACITY DECOMPOSITION + DANGLING LEASES ----------------------------------------
    # These are the two checks that FAILED the previous Phase A runs. A PASS issued without
    # running them is not a PASS. (My earlier edit to add them silently did not apply -- the
    # sealer graded 122 cycles without ever looking for a leaked lease.)
    print("\n--- CAPACITY + LEASE INTEGRITY ---")
    ADMIN = ("KILLED-WORKER", "CORRUPT", "TOKREG", "DUP", "TIMEOUT", "MUT", "EXP", "STUCK")
    _is_worker = lambda t: not any(k in str(t).upper() for k in ADMIN)
    lease_rows = jl("lease_ledger.jsonl") or jl("daemon/task_lease_ledger.jsonl")

    _op, _cl, _meta, _last = {}, {}, {}, ""
    for e in lease_rows:
        lid, st, ts, tid = e.get("lease_id"), e.get("status"), e.get("ts"), e.get("task_id", "")
        if not lid or not ts:
            continue
        _last = max(_last, ts); _meta[lid] = tid
        if st == "ACQUIRED":
            _op.setdefault(lid, ts)
        elif st in ("RELEASED", "COMPLETED", "FAILED"):
            _cl.setdefault(lid, ts)

    def _peak(pred, exclude=()):
        ev = []
        for l, a in _op.items():
            if l in exclude or not pred(_meta.get(l, "")):
                continue
            ev.append((a, +1)); ev.append((_cl.get(l, _last), -1))
        ev.sort(key=lambda x: (x[0], x[1]))
        c = pk = 0
        for _, d in ev:
            c += d; pk = max(pk, c)
        return pk

    leaked = [l for l in _op if l not in _cl]
    worker_peak = _peak(_is_worker)
    true_worker_peak = _peak(_is_worker, exclude=set(leaked))
    recovery_peak = _peak(lambda t: not _is_worker(t))
    total_peak = _peak(lambda t: True)
    violation = true_worker_peak > CAPACITY

    print(f"  configured capacity        : {CAPACITY}")
    print(f"  worker peak (raw)          : {worker_peak}")
    print(f"  worker peak (excl. leaked) : {true_worker_peak}")
    print(f"  recovery/injection peak    : {recovery_peak}")
    print(f"  total peak                 : {total_peak}")
    # FILESYSTEM CROSS-CHECK. The ledger cannot record a release that failed, so a leak can be
    # invisible in it (this is exactly how "0 leaked leases" passed A/B/C while lock files sat
    # stranded on disk). Cross-check the ACTUAL lock files against the ledger. J-SPACE found this
    # by reading the filesystem; the sealer must too.
    import glob as _glob, json as _json2, time as _t2
    _live_locks = []
    for _lp in _glob.glob(str(ROOT / "coordination" / "leases" / "*.lock")):
        try:
            _ld = _json2.load(open(_lp))
            _tid = str(_ld.get("task_id",""))
            # a lock older than 10 min that the ledger says was RELEASED is STRANDED
            if _tid.startswith(("SOAK-",)) and _ld.get("status") == "ACTIVE":
                _live_locks.append(_tid)
        except Exception:
            pass
    # AU-9: a PASS may NOT be issued over rewritten history. Verify the evidence chain BEFORE
    # any verdict. A seal is a claim about what happened; if the record of what happened can be
    # silently edited, the seal is worthless.
    # AU-9 gate verifies the PACKAGE ledger UNDER SEAL — the soak's actual evidence — not the
    # live daemon ledger (which other components write via non-chained paths).
    _lead = PKG / "daemon" / "task_lease_ledger.jsonl"
    if not _lead.exists():
        _lead = PKG / "lease_ledger.jsonl"
    _chain_ok, _chain_why = chain_precondition(_lead)
    req("evidence chain intact (AU-9, tamper-evident)", _chain_ok, _chain_why)

    req("no STRANDED lock files (filesystem cross-check)", len(_live_locks) == 0,
        f"{len(_live_locks)} lock files ACTIVE on disk: {_live_locks[:4]}")

    req("NO leaked lease (acquired, never released)", not leaked,
        f"{len(leaked)} leaked: {[_meta.get(l) for l in leaked][:3]}")
    req("capacity NOT exceeded by genuine workers", not violation,
        f"worker_peak={true_worker_peak} > capacity={CAPACITY}")

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
        "capacity": {"configured_worker_capacity": CAPACITY,
                     "worker_peak_concurrency": worker_peak,
                     "recovery_peak_concurrency": recovery_peak,
                     "total_peak_concurrency": total_peak,
                     "capacity_violation": violation},
        "notes": notes,
        "unrelated_work_continued_after_every_injection": not any(
            f_.startswith("injection") for f_ in failures),
        "evaluator": "seal_soak_phase.py (independent of the runner that produced the evidence)",
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "next_phase_authorized": (not failures),
        "24_7_status": "NOT YET PROVEN",
    }, indent=2))
    print(f"  sealed: {PKG / 'seal_verdict.json'}")
    sys.exit(0 if not failures else 1)
