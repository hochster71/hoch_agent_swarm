"""HOCH GOAL ENGINE — completion computed ONLY from validators that actually executed.

RATIFIED 2026-07-12 by Michael Bryan Hoch.

This replaces the previous goal computation, which was:
  * a weight-sum over tasks whose `status` was a HARDCODED STRING LITERAL in
    backend/pert_server.py (audit F-01.2), and
  * a fallback default of 90.0 emitted with source=autonomous_cadence_telemetry,
    freshness=0.0s, confidence=HIGH whenever the source was missing (audit F-02.1).

THE RULE
--------
A requirement contributes to completion ONLY when its validator has EXECUTED
SUCCESSFULLY against CURRENT evidence. Everything else contributes ZERO:

    BLOCKED, STALE, UNKNOWN, UNVERIFIED, MANUALLY_ASSERTED, VALIDATOR_NOT_RUN  -> 0

There is no path in this file that emits a completion number from a default. If a
source is missing, the answer is null and UNKNOWN. Absence of evidence is never a pass.

SEPARATION (ratified)
---------------------
North-Star / champion-product / platform / governance progress are DISTINCT metrics and
are never averaged into one number. Founder-only gates are reported SEPARATELY and never
reduce autonomous implementation progress -- an agent is not "behind" because a human
has not yet signed something.
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CONTRACT = ROOT / "config" / "canonical_goal_contract.json"
REQUIREMENTS = ROOT / "config" / "goal_requirements.json"
OUT_DIR = ROOT / "coordination" / "goal"
STATE_PATH = OUT_DIR / "goal_state.json"

# States that contribute ZERO. Ratified list -- do not extend without founder approval.
ZERO_STATES = {
    "BLOCKED", "STALE", "UNKNOWN", "UNVERIFIED", "MANUALLY_ASSERTED", "VALIDATOR_NOT_RUN",
    "VALIDATOR_MISSING", "FAILED",
}


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _load(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def evidence_freshness_hours(path: Path) -> float | None:
    """Age of the evidence artifact. None if it does not exist -- which means UNKNOWN,
    NOT fresh. (The old wrap_telemetry_dict stamped now() when a timestamp was absent,
    so missing data rendered as maximally fresh. That bug is not repeated here.)"""
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    return round(age / 3600.0, 2)


def run_validator(req: dict, execute: bool = True) -> dict:
    """Execute the requirement's validator. Its EXIT CODE is the only thing that counts."""
    cmd = req.get("validator")
    evidence = ROOT / req["evidence_path"]

    result = {
        "id": req["id"],
        "layer": req["layer"],
        "statement": req["statement"],
        "owner": req["owner"],
        "blocking": bool(req.get("blocking")),
        "weight": float(req.get("weight", 1)),
        "validator": cmd,
        "evidence_path": req["evidence_path"],
        "evidence_exists": evidence.exists(),
        "evidence_age_hours": evidence_freshness_hours(evidence),
        "freshness_sla_hours": req.get("freshness_sla_hours"),
        "state": "VALIDATOR_NOT_RUN",
        "exit_code": None,
        "detail": "",
        "contributes": 0.0,
        "checked_at": _iso(_now()),
    }

    if not execute:
        return result

    if not cmd:
        result["state"] = "VALIDATOR_MISSING"
        result["detail"] = "no validator defined -- contributes zero by rule"
        return result

    try:
        # Prefer the same interpreter as the engine (.venv) so pytest/deps match CI.
        run_cmd = cmd
        if isinstance(cmd, str) and (cmd.startswith("python3 ") or cmd.startswith("python ")):
            run_cmd = f"{sys.executable} " + cmd.split(" ", 1)[1]
        proc = subprocess.run(run_cmd, shell=True, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=600)
        result["exit_code"] = proc.returncode
        tail = (proc.stdout or proc.stderr or "").strip().splitlines()
        result["detail"] = tail[-1][:200] if tail else ""
    except subprocess.TimeoutExpired:
        result["state"] = "BLOCKED"
        result["detail"] = "validator timed out"
        return result
    except Exception as e:
        result["state"] = "BLOCKED"
        result["detail"] = f"{type(e).__name__}: {e}"
        return result

    if result["exit_code"] != 0:
        result["state"] = "FAILED"
        return result

    # Re-check evidence AFTER the run: a validator that PRODUCES its own evidence
    # artifact must be credited for it. (Checking only beforehand marked freshly
    # generated evidence as absent.)
    result["evidence_exists"] = evidence.exists()
    result["evidence_age_hours"] = evidence_freshness_hours(evidence)

    # Validator passed. Now the evidence must ALSO exist and be fresh.
    if not result["evidence_exists"]:
        result["state"] = "UNVERIFIED"
        result["detail"] = "validator passed but its evidence artifact is absent"
        return result

    sla = req.get("freshness_sla_hours")
    age = result["evidence_age_hours"]
    if sla is not None and age is not None and age > float(sla):
        result["state"] = "STALE"
        result["detail"] = f"evidence is {age}h old, SLA is {sla}h"
        return result

    result["state"] = "SATISFIED"
    result["contributes"] = result["weight"]
    return result


def _pct(satisfied_weight: float, total_weight: float) -> float | None:
    """None -- never a default number -- when there is nothing to measure."""
    if total_weight <= 0:
        return None
    return round(100.0 * satisfied_weight / total_weight, 1)


def compute(execute: bool = True) -> dict:
    contract = _load(CONTRACT)
    reqs_doc = _load(REQUIREMENTS)
    if not contract or not reqs_doc:
        return {"status": "UNKNOWN", "reason": "CANONICAL_CONTRACT_OR_REQUIREMENTS_MISSING"}

    results = [run_validator(r, execute=execute) for r in reqs_doc["requirements"]]

    def score(rs: list[dict]) -> float | None:
        blocking = [r for r in rs if r["blocking"]]
        total = sum(r["weight"] for r in blocking)
        got = sum(r["contributes"] for r in blocking)
        return _pct(got, total)

    # --- founder-only gates are held OUT of autonomous progress -----------------
    agent_reqs = [r for r in results if r["owner"] != "FOUNDER_ONLY"]
    founder_reqs = [r for r in results if r["owner"] == "FOUNDER_ONLY"]

    by_layer = {}
    for layer in ("NS", "TO", "CP", "ES", "GOV"):
        rs = [r for r in results if r["layer"] == layer]
        if rs:
            by_layer[layer] = {
                "requirements": len(rs),
                "satisfied": sum(1 for r in rs if r["state"] == "SATISFIED"),
                # agent-owned progress excludes founder gates by ratified rule
                "completion_pct_agent_scope": score([r for r in rs if r["owner"] != "FOUNDER_ONLY"]),
                "founder_only_pending": [r["id"] for r in rs
                                         if r["owner"] == "FOUNDER_ONLY" and r["state"] != "SATISFIED"],
            }

    unresolved_blocking = [r for r in results if r["blocking"] and r["state"] != "SATISFIED"]
    # Critical path = unresolved BLOCKING requirements, ordered by weight (impact).
    # NOT a hardcoded status string (audit F-01.2).
    critical_path = sorted(unresolved_blocking,
                           key=lambda r: (-r["weight"], r["owner"] == "FOUNDER_ONLY", r["id"]))
    agent_actionable = [r for r in critical_path if r["owner"] != "FOUNDER_ONLY"]

    champ = (contract.get("goal_hierarchy", {})
                     .get("3_current_champion_product", {}))
    champion_name = champ.get("value")
    champion_selected = bool(champion_name) and champ.get("value_state") == "SELECTED"

    relay = _load(ROOT / "coordination" / "council" / "relay" / "H1D_pert_node.json") or {}
    dispatch_ledger = ROOT / "coordination" / "council" / "relay" / "dispatch_ledger.jsonl"
    founder_minutes = ROOT / "coordination" / "goal" / "founder_minutes_ledger.jsonl"

    state = {
        "schema": "HOCH_GOAL_STATE_v1",
        "computed_at": _iso(_now()),
        "canonical_north_star": contract["north_star"],
        "computation_rule": "weight-sum of requirements whose validator EXECUTED SUCCESSFULLY against current, fresh evidence. Everything else contributes zero. No fallback default exists in this engine.",

        # ---- the nine required top-level metrics (ratified) --------------------
        "metrics": {
            "north_star_completion": score([r for r in agent_reqs if r["layer"] == "NS"]),
            # CP completion is COMPUTED from the champion-gate validators, never
            # assigned from memory. UNKNOWN only while no champion is selected.
            "champion_product_completion": (
                score([r for r in agent_reqs if r["layer"] == "CP"])
                if champion_selected else None),
            "champion_product_completion_state": (
                f"COMPUTED_FROM_VALIDATORS:{champion_name}" if champion_selected
                else "UNKNOWN_NO_CHAMPION_SELECTED"),
            "champion_product": champion_name,
            "autonomous_execution_coverage": score(agent_reqs),
            "founder_intervention_rate": None,
            "verified_founder_minutes_per_shipped_dollar": None,
            "evidence_coverage": _pct(
                sum(1 for r in results if r["evidence_exists"]), len(results)) if results else None,
            "runtime_truth_freshness": None,
            "current_critical_path_blocker": (agent_actionable[0]["id"] if agent_actionable
                                              else (critical_path[0]["id"] if critical_path else None)),
            "founder_only_actions_pending": [r["id"] for r in founder_reqs
                                             if r["state"] != "SATISFIED"],
        },
        "metric_unknown_reasons": {
            "champion_product_completion": ("UNKNOWN only if no champion is selected. When one is, "
                                            "this is COMPUTED from the champion-gate validators."),
            "founder_intervention_rate": ("computed from the dispatch ledger once it accumulates routine tasks; "
                                          f"ledger present: {dispatch_ledger.exists()}"),
            "verified_founder_minutes_per_shipped_dollar": ("UNKNOWN: no founder-minutes ledger "
                                                            f"(present: {founder_minutes.exists()}) and zero shipped revenue. "
                                                            "Reporting a number here would be a fabrication."),
            "runtime_truth_freshness": "UNKNOWN until the council state endpoint is served (REQ-ES-004 currently FAILS).",
        },

        "by_layer": by_layer,
        "goal_hierarchy": contract["goal_hierarchy"],

        "critical_path": [
            {"id": r["id"], "layer": r["layer"], "weight": r["weight"], "owner": r["owner"],
             "state": r["state"], "statement": r["statement"], "detail": r["detail"]}
            for r in critical_path
        ],
        "next_recommended_task": (
            {"id": agent_actionable[0]["id"], "statement": agent_actionable[0]["statement"],
             "why": "highest-weight unresolved BLOCKING requirement on the canonical critical path that an agent can act on"}
            if agent_actionable else None
        ),

        "h1d_relay_node": {"state": relay.get("state"), "reason": relay.get("state_reason")},
        "requirements": results,
        "hard_constraint": contract["hard_constraint"]["statement"],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def main() -> int:
    execute = "--no-exec" not in sys.argv
    s = compute(execute=execute)
    m = s["metrics"]

    def fmt(v):
        return "UNKNOWN" if v is None else f"{v}%"

    print("=" * 74)
    print("HOCH CANONICAL GOAL STATE")
    print("=" * 74)
    print(f"NORTH STAR: {s['canonical_north_star']}")
    print()
    print(f"  north_star_completion            : {fmt(m['north_star_completion'])}")
    print(f"  champion_product_completion      : {fmt(m['champion_product_completion'])}  ({m['champion_product_completion_state']})")
    print(f"  autonomous_execution_coverage    : {fmt(m['autonomous_execution_coverage'])}")
    print(f"  founder_intervention_rate        : {fmt(m['founder_intervention_rate'])}")
    print(f"  founder_minutes_per_shipped_$    : {fmt(m['verified_founder_minutes_per_shipped_dollar'])}")
    print(f"  evidence_coverage                : {fmt(m['evidence_coverage'])}")
    print(f"  runtime_truth_freshness          : {fmt(m['runtime_truth_freshness'])}")
    print(f"  current_critical_path_blocker    : {m['current_critical_path_blocker']}")
    print(f"  founder_only_actions_pending     : {m['founder_only_actions_pending']}")
    print()
    print("  BY LAYER (agent scope; founder gates excluded by ratified rule):")
    for layer, d in s["by_layer"].items():
        print(f"    {layer:4} {d['satisfied']}/{d['requirements']} satisfied   "
              f"completion={fmt(d['completion_pct_agent_scope'])}   "
              f"founder_pending={d['founder_only_pending']}")
    print()
    print("  REQUIREMENTS:")
    for r in s["requirements"]:
        mark = "OK  " if r["state"] == "SATISFIED" else "    "
        print(f"    {mark}{r['id']:14} {r['state']:17} w={r['weight']:<3} {r['owner']:12} {r['detail'][:44]}")
    print()
    nxt = s["next_recommended_task"]
    print(f"  NEXT TASK: {nxt['id'] if nxt else 'NONE'} — {nxt['statement'][:70] if nxt else ''}")
    print(f"\n  written: coordination/goal/goal_state.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
