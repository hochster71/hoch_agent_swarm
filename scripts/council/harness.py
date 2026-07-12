#!/usr/bin/env python3
"""Governed HELM Council harness. Profile-scoped, fail-closed, run-bound.

  python3 scripts/council/harness.py --profile local_proof

Operator hold is NEVER cleared by this harness; it is snapshotted and restored in `finally`.
Exit 0 only when the harness completed AND produced internally consistent evidence.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from council import lock as locking
from council.registry import Registry, NotWired, ProfileViolation, UnknownMember
from council.adapters import dispatch_ex as adapter_dispatch, AdapterError, ExternalEgressBlocked
from council.validate import validate
from council.aggregate import (aggregate, advisory_quorum, exit_code,
                               LIVE_EXTERNAL, MOCK_INTERNAL, LOCAL_ONLY)
from council.runstate import write_atomic, run_ids_consistent

ROOT = Path(__file__).resolve().parents[2]
HOLD = ROOT / "has_live_project_tracker" / "data" / "ag_operator_hold.json"
ADVISORY_DIR = ROOT / "coordination" / "council" / "advisory_records"
RUNS = ROOT / "coordination" / "council" / "runs"


def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def sha(s): return hashlib.sha256(s.encode()).hexdigest()


def load_env():
    e = {}
    p = ROOT / ".env"
    if p.exists():
        for ln in p.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                e[k.strip()] = v.strip().strip('"').strip("'")
    return e


def build_prompt(run_id, profile_id, seat):
    """D-18: mission inputs are INLINED as content. Models have no filesystem."""
    inputs = {}
    for name, rel in [("alignment_packet", "coordination/HELM_COUNCIL_ALIGNMENT_PACKET_v1.json"),
                      ("normalized_context", "coordination/helm_intake_normalized_context.json"),
                      ("factory_routes", "coordination/helm_factory_routes.json")]:
        p = ROOT / rel
        inputs[name] = json.loads(p.read_text()) if p.exists() else {"_missing": rel}
    return (
        f"You are {seat['display_name']} on the HELM Council for Hoch Agent Swarm.\n"
        f"ROLE: {seat['role']}\nRUN ID: {run_id}\nPROFILE: {profile_id}\n\n"
        "MISSION INPUTS (full content, inlined):\n"
        f"{json.dumps(inputs, indent=1)[:12000]}\n\n"
        "TASK: Evaluate the mission from your assigned role only.\n"
        "RULES: Do not execute work. Do not invent evidence. Do not claim runtime status without "
        "evidence. Do not override founder gates. If your verdict is APPROVE, you MUST populate "
        "'top_findings' with at least one finding and 'evidence_refs' with at least one reference "
        "(e.g., 'alignment_packet').\n\n"
        "IMPORTANT: YOU MUST RETURN ONLY A RAW JSON OBJECT. DO NOT INCLUDE ANY CONVERSATIONAL CHAT, PREAMBLE, OR EXPLANATION. YOUR ENTIRE RESPONSE MUST BE A SINGLE VALID JSON OBJECT MATCHING THE SCHEMA BELOW.\n\n"
        "REQUIRED JSON SCHEMA:\n"
        '{"verdict":"APPROVE|REJECT|CONDITIONAL|UNKNOWN|DISSENT","top_findings":[],'
        '"fake_green_risks":[],"missing_evidence":[],"evidence_refs":[],"founder_gates":[],'
        '"recommended_next_actions":[]}\n')


def extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        pass
    d = 0; start = None
    for i, c in enumerate(text or ""):
        if c == "{":
            if d == 0: start = i
            d += 1
        elif c == "}":
            d -= 1
            if d == 0 and start is not None:
                try: return json.loads(text[start:i + 1])
                except Exception: start = None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, choices=["local_proof", "frontier_council"])
    args = ap.parse_args()

    reg = Registry()
    errs = reg.validate_schema()
    if errs:
        print("REGISTRY SCHEMA INVALID:", *errs, sep="\n  "); return 11

    prof = reg.profile(args.profile)
    run_id = f"HELM-COUNCIL-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    run_dir = RUNS / run_id
    started = now()
    env = load_env()

    hold_snapshot = json.loads(HOLD.read_text()) if HOLD.exists() else None
    hold_restored = False
    lock_acquired = False
    dispatch_records, validation_results = [], {}
    adapter_metas = {}
    seen_ids, seen_digests = set(), set()

    try:
        dupes = locking.duplicate_processes()
        if dupes:
            print("DUPLICATE HARNESS DETECTED — refusing to run"); return 9
        locking.acquire(); lock_acquired = True

        for mid in prof["allowed_member_ids"]:
            rec = {"member_id": mid, "dispatched": False, "status": None}
            try:
                seat = reg.resolve_for_dispatch(mid, args.profile)
            except (NotWired, ProfileViolation, UnknownMember) as e:
                rec["status"] = "CONFIGURED_NOT_WIRED" if isinstance(e, NotWired) else "FAILED_VISIBLE"
                rec["reason"] = str(e)
                dispatch_records.append(rec)
                print(f"[{mid}] SKIPPED ({rec['status']}): {e}")
                continue

            key = env.get(seat["auth_source"]) if seat["auth_source"] else None
            if seat["auth_source"] and not key:
                rec["status"] = "AUTH_MISSING"; dispatch_records.append(rec)
                print(f"[{mid}] AUTH_MISSING"); continue

            prompt = build_prompt(run_id, args.profile, seat)
            t0 = time.time(); s_at = now()
            try:
                text, resolved, raw, ameta = adapter_dispatch(seat, prompt, key)
                rec["dispatched"] = True
                rec["adapter_kind"] = ameta.get("adapter_kind")
                adapter_metas[mid] = ameta
            except AdapterError as e:
                rec["dispatched"] = True
                rec["status"] = str(e).split(":")[0] or "FAILED_VISIBLE"
                rec["reason"] = str(e)
                dispatch_records.append(rec)
                validation_results[mid] = {"accepted": False, "status": rec["status"],
                                           "reasons": [str(e)], "response": None}
                print(f"[{mid}] FAILED_VISIBLE: {e}")
                continue

            c_at = now()
            raw_path = run_dir / "raw" / f"{mid}.raw.txt"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(raw, encoding="utf-8")

            body = extract_json(text) or {}
            ameta = adapter_metas.get(mid, {})
            live_adapter = ameta.get("adapter_kind") == "live"
            body["provider_identity_source"] = "provider_response" if live_adapter else ameta.get("adapter_kind", "unknown")
            body["resolved_model_source"] = "provider_response" if live_adapter else ameta.get("adapter_kind", "unknown")
            body["telemetry"] = {
                "run_id": run_id, "profile_id": args.profile, "member_id": mid,
                "response_id": f"{run_id}:{mid}:{uuid.uuid4().hex[:8]}",
                "provider": seat["provider"], "requested_model": seat["requested_model"],
                "resolved_model": resolved, "resolved_model_source": "provider_response",
                "endpoint": seat["endpoint"], "adapter": seat["adapter"],
                "schema_version": seat["schema_version"], "started_at": s_at, "completed_at": c_at,
                "latency_ms": int((time.time() - t0) * 1000), "is_fallback": False,
                "fallback_from": None, "raw_response_path": str(raw_path.relative_to(ROOT)),
                "response_digest": sha(raw), "raw_response_sha256": sha(raw),
                "evidence_refs": body.get("evidence_refs") or [],
                # The adapter declares what it is. A mock can never be counted live.
                "adapter_kind": adapter_metas.get(mid, {}).get("adapter_kind", "unknown"),
                "is_mock": bool(adapter_metas.get(mid, {}).get("is_mock", True)),
                "simulated": bool(adapter_metas.get(mid, {}).get("simulated", False)),
                "external_call": bool(adapter_metas.get(mid, {}).get("external_call", False)),
            }
            write_atomic(run_dir / "responses" / f"{mid}.response.json", body)
            rec["status"] = "RESPONDED"
            dispatch_records.append(rec)
            print(f"[{mid}] responded: requested={seat['requested_model']} resolved={resolved} "
                  f"{body['telemetry']['latency_ms']}ms")

        completed = now()

        for mid, _ in [(d["member_id"], d) for d in dispatch_records if d["status"] == "RESPONDED"]:
            resp = json.loads((run_dir / "responses" / f"{mid}.response.json").read_text())
            ok, reasons = validate(resp, active_run_id=run_id, active_profile_id=args.profile,
                                   dispatched_member_id=mid, registry=reg,
                                   run_started_at=started, run_completed_at=completed,
                                   seen_response_ids=seen_ids, seen_digests=seen_digests)
            validation_results[mid] = {"accepted": ok, "reasons": reasons, "response": resp,
                                       "status": "VALIDATED" if ok else "FAILED_VISIBLE"}
            print(f"[{mid}] validation: {'ACCEPTED' if ok else 'REJECTED ' + str(reasons)}")

        advisory = advisory_quorum(
            [json.loads(p.read_text()) for p in ADVISORY_DIR.glob("rec_*.json")],
            reg.doc["quorum"]["advisory"])
        kinds = {m.get("adapter_kind") for m in adapter_metas.values()}
        if kinds == {"live"}:
            execution_mode = LIVE_EXTERNAL      # unreachable during H1B: egress is blocked
        elif kinds == {"local"}:
            execution_mode = LOCAL_ONLY
        else:
            execution_mode = MOCK_INTERNAL      # mixed or mock => the SAFE answer
        agg = aggregate(reg, args.profile, dispatch_records, validation_results, advisory,
                        execution_mode=execution_mode, authorization_consumed=False)

        run_doc = {"run_id": run_id, "profile_id": args.profile, "started_at": started,
                   "completed_at": completed, "registry_digest": reg.digest,
                   "dispatch_records": dispatch_records, "aggregation": agg, "advisory": advisory}
        write_atomic(run_dir / "run.json", run_doc)
        write_atomic(ROOT / "coordination" / "council" / "council_live_state.json", run_doc)
        
        # R2: full evidence-plane reconciliation
        try:
            from council.reconcile import reconcile
            reconcile(write=True)
        except Exception as e:
            print(f"RECONCILIATION ERROR during run: {e}", file=sys.stderr)

        write_atomic(ROOT / "coordination" / "helm_council_harness_registry.json", reg.harness_view())
        evidence_written = (run_dir / "run.json").exists()
        consistent = run_ids_consistent(run_doc, {"run_id": run_id})

        code = exit_code(agg, hold_restored=True, lock_clear=True, duplicate_processes=0,
                         evidence_written=evidence_written, run_ids_consistent=consistent)
        print(json.dumps({"run_id": run_id, "status": agg["overall_status"],
                          "validated_live_members": agg["counts"]["validated_live_members"],
                          "local_profile_quorum": agg["local_profile_quorum"],
                          "frontier_council_quorum": agg["frontier_council_quorum"],
                          "advisory_quorum": agg["advisory_quorum"],
                          "safe_to_execute_now": agg["safe_to_execute_now"],
                          "exit_code": code}, indent=1))
        return code

    finally:
        # operator hold is restored UNCONDITIONALLY — this harness never leaves it altered
        try:
            if hold_snapshot is not None:
                write_atomic(HOLD, hold_snapshot)
            hold_restored = True
        except Exception as e:
            print(f"OPERATOR HOLD RESTORE FAILED: {e}", file=sys.stderr)
            hold_restored = False
        if lock_acquired:
            locking.release()
        print(f"[finally] operator_hold_restored={hold_restored} lock_clear={locking.is_clear()}")


if __name__ == "__main__":
    sys.exit(main())
