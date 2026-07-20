#!/usr/bin/env python3
"""HELM autonomous build-to-GOAL runner.

Drives the council loop node-by-node until GOAL, hands-off, within HELM's hard rails:
  per node → Orchestrator frames → Builder (guarded execute) builds → Grok (Auditor) verifies
  → the node flips to DONE ONLY on a clean VERIFIED verdict (NO FAKE GREEN).

Safe by default: no args = DRY plan (reports what it would do, changes nothing).
`--go` = founder standing authorization to run the guarded build loop for real. Even with
--go it STOPS and reports rather than fake-green on: a founder-gated need, a hard blocker,
a missing prerequisite (grok/claude CLI), or repeated Grok rejection.

Hard rails (enforced by the guarded gateway + guarded_build): frozen target auto-rollback,
repo-scoped edits, no deploy/publish/money (acceptEdits = file edits only), snapshot before
mutate, per-task cost cap + monthly cap, ledger. Architectural changes still need an EDR.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PERT = ROOT / "coordination" / "goal" / "helm_pert.json"
STATUS = ROOT / "coordination" / "goal" / "build_to_goal_status.json"

# Per-node execution plan. 'verify' nodes are audited directly; 'build' nodes are built by the
# Claude Builder lane (guarded execute) then audited. Order = fastest controllable first.
NODE_PLAN = [
    {"id": "N6_DISPATCH", "type": "verify",
     "ask": "Confirm N6_DISPATCH (provider dispatch enablement, AC9) is satisfied. Evidence: "
            "the council now dispatches through CouncilDispatchGateway to local (Ollama), Grok "
            "(CLI_GROK), and Claude (CLI_CLAUDE) — cost-capped, ledgered, role-bound. Verdict "
            "VERIFIED if the guarded multi-provider dispatch is in place, else state the gap."},
    {"id": "N3_VERIFY", "type": "verify_frozen",
     "ask": None},  # uses helm_fire_verification.run_verification (rich frozen evidence)
    {"id": "N4_NORMALIZE", "type": "build",
     "task": "Implement the EDR-0003 normalization layer for HELM (AC5). Create NEW non-frozen "
             "module(s) under backend/helm_runtime/ (do NOT edit the frozen target files) that "
             "normalize dispatch/runtime records into the canonical shape EDR-0003 specifies, "
             "with unit tests under tests/. If EDR-0003 is not yet written, draft it under "
             "docs/helm/edr/ first, then implement to it. Keep changes minimal and tested."},
    {"id": "N8_CONMON", "type": "build",
     "task": "Complete continuous ConMon + NIST 800-53 Rev5 evidence (AC8). Ensure the ConMon "
             "evidence collector runs continuously (not one-shot) and the Rev5 control mappings "
             "are current, writing fresh evidence under docs/evidence/. Add/adjust tests. New "
             "non-frozen files only."},
    {"id": "N5_KNOWLEDGE", "type": "build",
     "task": "Implement the Knowledge Engine / governed retrieval per EDR-0004 (AC6). Create NEW "
             "non-frozen module(s) providing policy-bound retrieval wired through governance, "
             "with tests. If EDR-0004 needs authoring, draft it under docs/helm/edr/ first."},
]
_MAX_REMEDIATION = 3   # Builder self-heals with the Auditor's feedback before any escalation
_MAX_DEBUG = 2         # then the debug-swarm diagnoses + fixes before anything reaches the founder


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_pert():
    return json.loads(PERT.read_text())


def _node_status(pert, nid):
    for n in pert.get("nodes", []):
        if n.get("id") == nid:
            return _effective_status(n)
    return None


# 2026-07-19 audit directive: a limited or unknown verification result must NEVER satisfy a
# terminal DONE condition. A node that records a verdict counts as DONE only when that verdict
# is a clean VERIFIED. (N3_VERIFY was marked DONE on VERIFIED_WITH_LIMITATIONS — that class of
# fake green is structurally impossible now: the evaluator, not the label, enforces it.)
_NON_CLEAN_VERDICTS = ("VERIFIED_WITH_LIMITATIONS", "REJECTED", "FAILED", "UNKNOWN", "BLOCKED")

# --- N3-VERDICT-BINDING-GAP remediation (2026-07-20, founder-directed) -----------------------
# A clean "VERIFIED" verdict is NOT sufficient for N3_VERIFY. On 2026-07-20 the runner
# declared GOAL_REACHED 100% off a REAL Grok verdict that was (a) bound to the frozen-target
# content hash instead of the evaluated candidate SHA, (b) scoped to bridge+gateway instead
# of the council-required composed runtime, (c) generated BEFORE the burn-down remediations,
# and (d) self-disclaiming independent re-execution. Cleanliness is necessary, never
# sufficient: the verdict must mechanically prove its BINDING, SCOPE, and VINTAGE, or
# N3_VERIFY = HOLD and the goal cannot be reached. Fail closed on every uncertainty.
_N3_ROOT = Path(__file__).resolve().parents[1]
_N3_SCOPE_MARKER = "SCOPE: COMPOSED_RUNTIME"  # T4 dispatch contract: verdict must attest scope
_N3_DISCLAIMERS = ("not independent re-execution", "not independent re-hashing",
                   "not a live production audit")


def _n3_candidate_ids():
    """(head_sha, tree_sha) of the evaluated candidate. Overridable by tests."""
    import subprocess
    def _g(*a):
        r = subprocess.run(["git", *a], cwd=_N3_ROOT, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    return _g("rev-parse", "HEAD"), _g("rev-parse", "HEAD^{tree}")


def _n3_binding_ok(n: dict) -> bool:
    """True ONLY when the verdict artifact mechanically proves all required bindings:
    terminal clean OVERALL, candidate HEAD sha embedded, candidate tree sha embedded,
    composed-runtime scope attested, and no method disclaimer. Anything missing, stale,
    narrower, content-only, or pre-remediation => False (HOLD)."""
    try:
        ev = n.get("evidence") or ""
        path = _N3_ROOT / ev
        if not path.is_file():
            return False
        text = path.read_text(errors="replace")
        if "OVERALL: VERIFIED" not in text:
            return False
        head, tree = _n3_candidate_ids()
        if not head or not tree or head not in text or tree not in text:
            return False  # content-hash-only or unbound verdicts fail here (BINDING + VINTAGE)
        if _N3_SCOPE_MARKER not in text:
            return False  # narrower / unattested scope (SCOPE)
        low = text.lower()
        if any(d in low for d in _N3_DISCLAIMERS):
            return False  # provenance/limitations disclaim the required verification
        return True
    except Exception:
        return False  # fail closed - a crashing check must never grant DONE


def _effective_status(n: dict) -> str:
    st = n.get("status", "PENDING")
    verdict = (n.get("verdict") or "").upper()
    if st == "DONE" and verdict and verdict != "VERIFIED":
        return "PARTIAL"
    if st == "DONE" and any(tok in (n.get("evidence") or "").upper() for tok in _NON_CLEAN_VERDICTS):
        return "PARTIAL"
    if n.get("id") == "N3_VERIFY" and st == "DONE" and not _n3_binding_ok(n):
        return "HOLD"
    return st


_REAL_PERT = Path(__file__).resolve().parents[1] / "coordination" / "goal" / "helm_pert.json"


def _set_node_status(nid, status, verdict=None, evidence=None):
    p = _load_pert()
    for n in p.get("nodes", []):
        if n.get("id") == nid:
            n["status"] = status
            if verdict is not None:
                n["verdict"] = verdict
            if evidence is not None:
                n["evidence"] = evidence
            # Clear old error or reason codes upon landing a successful status update
            for key in ("reason_code", "reason_description", "status_note"):
                if key in n:
                    del n[key]
    PERT.write_text(json.dumps(p, indent=2) + "\n")
    # Publish to the live event bus ONLY when operating on the REAL PERT file. Tests that point
    # PERT at a temp copy must never contaminate the audit stream (NO FAKE GREEN on telemetry too).
    if PERT.resolve() != _REAL_PERT.resolve():
        return
    try:
        # HELM-GOV | extends: N6 emitter (goal_runner) | edr: EDR-0006-R4 | why: GOAL_NODE_UPDATE
        #          | advances material state (a PERT node status) — it must carry a Proof Record.
        from backend.helm_runtime.governed_emit import emit_governed
        emit_governed(type="GOAL_NODE_UPDATE", producer="goal_runner", mission_id="GOAL_HELM",
                      authority="goal_runner:PERT_engine", explanation=f"PERT node {nid} -> {status}",
                      inputs={"node": nid, "status": status},
                      proof_command="scripts/helm_goal_runner.py (deterministic PERT recompute)",
                      environment="goal_runner", payload={"node": nid, "status": status})
    except Exception:
        pass


def _pct(pert):
    leg = pert.get("status_legend", {})
    nodes = pert.get("nodes", [])
    if not nodes:
        return 0.0
    return round(100.0 * sum(leg.get(_effective_status(n), 0.0) for n in nodes) / len(nodes), 1)


def _overall(text):
    t = (text or "").upper()
    import re
    m = re.search(r"OVERALL:\s*([A-Z_]+)", t)
    if m:
        val = m.group(1).strip()
        if val in ("VERIFIED", "VERIFIED_WITH_LIMITATIONS", "FAILED", "REJECTED"):
            return val
    for tok in ("VERIFIED_WITH_LIMITATIONS", "VERIFIED", "REJECTED", "FAILED"):
        if tok in t:
            return tok
    return "UNKNOWN"


def _write_status(state, detail):
    p = _load_pert()
    STATUS.write_text(json.dumps({
        "schema": "HELM_BUILD_TO_GOAL_STATUS_v1", "updated_at": _now(),
        "state": state, "detail": detail, "percent_to_goal": _pct(p),
        "nodes": {n["id"]: _effective_status(n) for n in p.get("nodes", [])},
    }, indent=2) + "\n")


def _stop(state, detail):
    _write_status(state, detail)
    print(f"\n■ RUNNER STOPPED [{state}] — {detail}")
    try:
        print(f"  status → {STATUS.relative_to(ROOT)}")
    except Exception:
        print(f"  status → {STATUS}")
    return 0 if state == "GOAL_REACHED" else 2


def _prereqs(go):
    missing = []
    if shutil.which("grok") is None:
        missing.append("grok CLI (Auditor) — needed to verify every node")
    # claude only needed if there are build nodes still open
    return missing


_STRICT = ("\n\nYou MUST end your response with exactly one line, nothing after it:\n"
           "OVERALL: VERIFIED    (only if the presented evidence fully satisfies the criterion)\n"
           "OVERALL: REJECTED    (if you cannot confirm from the evidence presented)")


def _audit(ask):
    """Fire the Grok auditor lane; force a strict terminal verdict; retry once on UNKNOWN."""
    from backend.dispatch.guarded_council import guarded_dispatch
    from backend.dispatch.council_router import _frame
    persona = "You are the HELM Auditor (Grok). Verify strictly against the PRESENTED EVIDENCE; do not rubber-stamp."
    for attempt in (1, 2):
        r = guarded_dispatch("auditor", _frame(persona, ask + _STRICT), pert_node="GOAL", timeout=600)
        if not r["ok"]:
            return "BLOCKED", r.get("message", "")
        ov = _overall(r.get("text", ""))
        if ov in ("VERIFIED", "REJECTED", "FAILED", "VERIFIED_WITH_LIMITATIONS"):
            return ov, r.get("text", "")
        ask = ask + "\n\n(Your previous reply had no OVERALL line. Answer again and END with the OVERALL: line.)"
    return "UNKNOWN", r.get("text", "")


def _n6_live_evidence() -> str:
    """Gather LIVE proof that guarded multi-provider dispatch is real (not just claimed):
    the council status + an actual local round-trip. Grok itself answering this request
    through the guarded gateway is itself proof the frontier (grok) lane is live."""
    from backend.dispatch.council_router import council_status
    from backend.dispatch.guarded_council import guarded_dispatch
    st = council_status()
    loc = guarded_dispatch("local", "Reply with exactly: alive")
    return json.dumps({
        "council_status_members": [{"lane": m["role"], "provider": m["provider"],
                                    "model": m.get("model"), "status": m["status"]}
                                   for m in st.get("members", [])],
        "live_local_round_trip_ok": bool(loc.get("ok")),
        "live_local_reply": (loc.get("text") or loc.get("message") or "")[:80],
        "note": "You (Grok) are answering THIS request through the same guarded CouncilDispatchGateway "
                "(CLI_GROK) — that is itself live proof the frontier lane dispatches. The local "
                "round-trip above proves the local lane. Both are cost-capped + ledgered.",
    }, indent=2)


def _verify_frozen():
    from helm_fire_verification import run_verification
    r = run_verification()
    if not r.get("ok"):
        return "BLOCKED", r.get("message", "")
    return _overall(r.get("text", "")), r.get("verdict_path", "")


def _build(task):
    from backend.dispatch.guarded_build import build
    return build(task, mode="execute", pert_node="GOAL", timeout=1800)


def _debug_swarm(nid, build_text, audit_text):
    """Swarm debug: a capable lane diagnoses the ROOT CAUSE of an audit failure and returns a
    concrete, minimal fix plan for the Builder to apply. This is where a code failure goes —
    NOT the founder. Uses the builder lane's provider (Claude if enabled, else a local coder)."""
    from backend.dispatch.guarded_council import guarded_dispatch
    from backend.dispatch.council_router import _frame
    ask = (f"You are the HELM Debugger. A build for {nid} did NOT pass independent audit. "
           f"Diagnose the ROOT CAUSE and give a concrete, minimal, file-level fix plan the "
           f"Builder can apply directly. Be specific; do not restate the task.\n\n"
           f"BUILD OUTPUT:\n{(build_text or '')[:3000]}\n\n"
           f"AUDITOR REJECTION:\n{(audit_text or '')[:2000]}")
    r = guarded_dispatch("builder", _frame("", ask), pert_node="GOAL", timeout=900)
    return r.get("text", "") if r.get("ok") else ""


def run(go: bool) -> int:
    print(f"▸ HELM build-to-GOAL runner — {'GO (live)' if go else 'DRY (plan only)'} — {_now()}")
    missing = _prereqs(go)
    if missing:
        return _stop("BLOCKED_PREREQ", "missing: " + "; ".join(missing))

    needs_founder: list[str] = []
    for node in NODE_PLAN:
        nid = node["id"]
        pert = _load_pert()
        st = _node_status(pert, nid)
        if st == "DONE":
            print(f"  ✓ {nid} already DONE — skip")
            continue
        print(f"\n▸ Node {nid} (status {st}) — {node['type']} — {_pct(pert)}% to GOAL")
        _write_status("RUNNING", f"working {nid}")

        if not go:
            print(f"  [DRY] would {node['type']} {nid} then Grok-verify → DONE on clean verdict")
            continue

        # BUILD nodes: Claude builder (guarded execute), with up to N remediation passes.
        if node["type"] == "build":
            if shutil.which("claude") is None:
                needs_founder.append(f"{nid}: needs Claude Code CLI (Builder) — install it + "
                                     "run helm_enable_claude_lane.sh builder")
                print(f"  ⏸ {nid} — no claude CLI, recorded, continuing")
                continue
            task = node["task"]
            closed = False
            last_build = last_audit = last_fix = ""
            # Ladder 1 — Builder self-heals using the Auditor's feedback.
            for attempt in range(1, _MAX_REMEDIATION + 1):
                print(f"  · build attempt {attempt} …")
                b = _build(task)
                if b.get("status") == "ROLLED_BACK":
                    needs_founder.append(f"{nid}: build touched frozen target — rolled back ({b.get('message')})")
                    break
                if not b.get("ok"):
                    needs_founder.append(f"{nid}: builder blocked — {b.get('message')}")
                    break
                last_build = b.get("text") or ""
                overall, ev = _audit(f"Independently verify this build satisfies {nid}. "
                                     f"Builder output:\n{last_build[:6000]}")
                last_audit = ev
                print(f"    Grok verdict: {overall}")
                if overall == "VERIFIED":
                    _set_node_status(nid, "DONE", verdict="VERIFIED"); closed = True
                    print(f"  ✓ {nid} → DONE (Grok VERIFIED)")
                    break
                if overall == "BLOCKED":
                    needs_founder.append(f"{nid}: auditor unavailable — {ev[:150]}")
                    break
                task = node["task"] + f"\n\nAuditor found this not-yet-verified: {ev[:1500]}\nRemediate."
            # Ladder 2 — DEBUG SWARM. A code failure goes here, not to the founder: a debugger
            # diagnoses the root cause, the Builder applies the fix, the Auditor re-checks.
            if not closed and last_build and "auditor unavailable" not in "".join(needs_founder[-1:]):
                for dbg in range(1, _MAX_DEBUG + 1):
                    print(f"  · debug-swarm pass {dbg} …")
                    fix = _debug_swarm(nid, last_build, last_audit)
                    if not fix:
                        break
                    last_fix = fix
                    b = _build(node["task"] + f"\n\nDEBUGGER root-cause fix plan — apply this:\n{fix[:2500]}")
                    if b.get("status") == "ROLLED_BACK" or not b.get("ok"):
                        needs_founder.append(f"{nid}: debug build blocked — {b.get('message')}")
                        break
                    last_build = b.get("text") or ""
                    overall, ev = _audit(f"Independently verify this fixed build satisfies {nid}. "
                                         f"Builder output:\n{last_build[:6000]}")
                    last_audit = ev
                    print(f"    Grok verdict (post-debug): {overall}")
                    if overall == "VERIFIED":
                        _set_node_status(nid, "DONE", verdict="VERIFIED"); closed = True
                        print(f"  ✓ {nid} → DONE (debug-swarm fixed, Grok VERIFIED)")
                        break
            if not closed and not any(nid in x for x in needs_founder):
                # Swarm exhausted. The founder does NOT fix code — this is a yes/no DECISION.
                # Present the swarm's recommendation + the auditor's objection; the founder only
                # approves a direction (or says "keep trying / adjust scope"), never writes code.
                needs_founder.append(
                    f"{nid}: DECISION FOR FOUNDER (not code to fix). The swarm built and debugged "
                    f"but the Auditor isn't satisfied.\n      Auditor objection: {last_audit[:200]}\n"
                    f"      Swarm recommendation: {(last_fix or 'escalate to a stronger model / adjust scope')[:220]}\n"
                    f"      → You only decide: approve this direction, adjust scope, or keep swarming.")
            continue

        # VERIFY nodes
        if node["type"] == "verify_frozen":
            overall, ev = _verify_frozen()
        else:
            ask = node["ask"]
            if nid == "N6_DISPATCH":
                ask += "\n\n=== LIVE EVIDENCE (gathered just now) ===\n" + _n6_live_evidence()
            overall, ev = _audit(ask)
        print(f"  Grok verdict: {overall}  ({ev[:80]})")
        if overall == "VERIFIED":
            _set_node_status(nid, "DONE", verdict="VERIFIED", evidence=ev)
            print(f"  ✓ {nid} → DONE")
        elif overall == "BLOCKED":
            return _stop("BLOCKED_AUDIT", f"{nid}: auditor unavailable — {ev}")
        else:
            needs_founder.append(f"{nid}: Grok {overall} — {ev[:200]}")
            print(f"  ⏸ {nid} not VERIFIED ({overall}) — recorded, continuing")

    # Rollup — GOAL is reached only when every node's EFFECTIVE status is DONE
    # (a DONE label with a non-clean verdict counts as PARTIAL, never DONE).
    pert = _load_pert()
    remaining = [n["id"] for n in pert.get("nodes", [])
                 if n.get("id") != "GOAL_HELM" and _effective_status(n) != "DONE"]
    if not remaining:
        _set_node_status("GOAL_HELM", "DONE")
        return _stop("GOAL_REACHED", f"All nodes DONE — GOAL_HELM reached ({_pct(_load_pert())}%).")
    detail = f"Advanced to {_pct(pert)}%. Still open: {remaining}."
    if needs_founder:
        detail += "  Needs founder / blocked:\n    - " + "\n    - ".join(needs_founder)
    return _stop("PARTIAL", detail)


def run_until_goal(max_cycles: int = 15, sleep_s: int = 12) -> int:
    """AUTONOMOUS drive: loop the full node pass until GOAL, re-attempting every non-DONE node
    each cycle (picks up enriched evidence, debug-swarm fixes, etc.). Stops ONLY on GOAL, on a
    genuine stall where the remaining work needs a founder decision, or a hard cap. No re-runs,
    no copy-paste — one start carries HELM to GOAL or to a real yes/no."""
    print(f"▸ AUTONOMOUS build-to-GOAL — looping to GOAL ({_now()})")
    last_pct, stalls = -1.0, 0
    for cycle in range(1, max_cycles + 1):
        print(f"\n========================  CYCLE {cycle}/{max_cycles}  ========================")
        run(go=True)
        pert = _load_pert()
        pct = _pct(pert)
        remaining = [n["id"] for n in pert.get("nodes", [])
                     if n.get("id") != "GOAL_HELM" and _effective_status(n) != "DONE"]
        if not remaining:
            _set_node_status("GOAL_HELM", "DONE")
            return _stop("GOAL_REACHED", f"All nodes DONE — GOAL_HELM reached ({_pct(_load_pert())}%).")
        stalls = stalls + 1 if pct <= last_pct else 0
        last_pct = pct
        if stalls >= 2:   # two cycles with zero forward progress → genuinely needs the founder
            detail = ""
            try:
                detail = json.loads(STATUS.read_text()).get("detail", "")
            except Exception:
                pass
            return _stop("NEEDS_FOUNDER", f"Autonomous swarm stalled at {pct}% after {cycle} cycles — "
                         f"remaining work needs a founder decision (never a code fix).\n{detail}")
        time.sleep(sleep_s)
    return _stop("PARTIAL", f"Reached {last_pct}% after {max_cycles} cycles.")


if __name__ == "__main__":
    import time
    if "--auto" in sys.argv:
        raise SystemExit(run_until_goal())
    raise SystemExit(run(go="--go" in sys.argv))
