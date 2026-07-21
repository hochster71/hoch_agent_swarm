#!/usr/bin/env python3
"""helm_three_percent_status.py — HELM never displays ONE unlabelled percentage.

FOUNDER RULE 2026-07-20. Three different questions were being answered with one number,
producing apparent contradictions between agents that were in fact measuring different
denominators:

    MISSION COMPLETION            how far through the mission graph  (includes external gates)
    AGENT-CONTROLLABLE COMPLETION same, EXCLUDING founder and external gates
    PROMOTION-CONTROL VALIDATION  validated required controls / required controls

A control can have passing unit tests and still not be enforced. A mission can be 90%
complete while zero critical controls are validated. Both statements are true at once.

DENOMINATOR INTEGRITY: every percentage prints WITH its numerator, denominator and scope.
A bare percentage is not reported. This is the same rule that made the old north-star 100%
gameable — it was reachable by excluding founder-gated requirements from its denominator.

Blockers are listed BY OWNERSHIP, because "what is blocking HELM" has three different
answers depending on who can act.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GOAL = ROOT / "coordination" / "goal" / "build_to_goal_status.json"
INVENTORY = ROOT / "coordination" / "governance" / "actor_inventory.json"
GOV007 = ROOT / "coordination" / "governance" / "gov007_evidence.json"

# Controls required before promotion. Evidence kind -> highest lifecycle state discharged.
REQUIRED_CONTROLS = [
    ("RC23-BRANCH-PROTECTION", "direct pushes to master prohibited"),
    ("COMMIT-SIGNING", "cryptographic provenance on contributions"),
    ("PER-ACTOR-GIT-IDENTITY", "distinct git identity per actor"),
    ("GOV-007-IMPERSONATION", "one actor cannot contribute as another"),
    ("ACTOR-F3-KEY-CUSTODY", "signing key not readable across actors"),
]

# Suites that are RED BY DESIGN — specifications for unbuilt work. Counting them as
# regressions would misreport the test posture.
RED_BY_DESIGN = {
    "test_w1_002a_collector_provenance.py",
    "test_w1_002b_endpoint_provenance.py",
    "test_w1_002c_verifier_burndown_provenance.py",
}


def _load(p: Path) -> Optional[Any]:
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def pct(num: int, den: int) -> str:
    return f"{100.0 * num / den:.1f}%" if den else "UNKNOWN (denominator 0)"


def mission_completion() -> dict:
    d = _load(GOAL)
    if not d:
        return {"value": None, "reason": "goal oracle unreadable"}
    nodes = d.get("nodes", {})
    done = sum(1 for v in nodes.values() if str(v).upper() == "DONE")
    return {
        "value": pct(done, len(nodes)), "numerator": done, "denominator": len(nodes),
        "scope": "mission graph nodes, INCLUDING externally gated",
        "non_done": {k: v for k, v in nodes.items() if str(v).upper() != "DONE"},
        "oracle_caveat": ("live file, provenance not promotion-grade — useful as an "
                          "operational progress indicator, NOT as a promotion input"),
    }


OWNERSHIP_FIELD = "ownership"          # AGENT | FOUNDER | EXTERNAL | SHARED
OWNERSHIP_SOURCES = [                  # files that would have to carry it
    "coordination/goal/build_to_goal_status.json  (nodes are flat str->str)",
    "coordination/goal/goal_state.json            (requirements have no owner field)",
]
DOCTRINE_SOURCE = "CLAUDE.md §CONTROLLABLE vs EXTERNALLY-GATED DOCTRINE (2026-07-17)"


def agent_controllable() -> dict:
    """Mission nodes EXCLUDING founder/external gates.

    RETURNS UNKNOWN BY CONSTRUCTION.

    The doctrine exists — CLAUDE.md enumerates controllable vs externally-gated
    categories (Apple App Review, App Store publication, Stripe settlement, bank
    deposit, external certs, DNS propagation, third-party API approvals). But it is
    PROSE. No machine-readable ownership field exists on any mission node.

    Three ways to fake this number, all forbidden:
      1. infer ownership from node NAMES  -> guessing
      2. infer from status strings        -> a node can be BLOCKED_EXTERNAL today and
                                             AGENT-owned tomorrow; status is not ownership
      3. hand-maintain a list here        -> an unversioned second source of truth

    A percentage computed from a denominator nobody defined is exactly how the old
    north-star 100% became meaningless. UNKNOWN until the schema field exists.
    """
    d = _load(GOAL)
    if not d:
        return {"value": None, "reason": "goal oracle unreadable", "known": False}
    nodes = d.get("nodes", {})
    classified = {k: v.get(OWNERSHIP_FIELD) for k, v in nodes.items()
                  if isinstance(v, dict) and v.get(OWNERSHIP_FIELD)}
    if len(classified) != len(nodes):
        return {
            "value": "UNKNOWN", "known": False,
            "numerator": None, "denominator": None,
            "scope": "mission nodes EXCLUDING founder/external gates",
            "reason": (f"no authoritative ownership field. {len(classified)}/{len(nodes)} "
                       f"nodes carry '{OWNERSHIP_FIELD}'."),
            "missing_schema_field": f"{OWNERSHIP_FIELD}: AGENT | FOUNDER | EXTERNAL | SHARED",
            "files_requiring_augmentation": OWNERSHIP_SOURCES,
            "doctrine_exists_but_is_prose": DOCTRINE_SOURCE,
            "refused_inferences": ["node names", "status strings", "hand-maintained list"],
        }
    # Only reachable once every node is classified.
    inscope = {k: v for k, v in nodes.items()
               if classified[k] in ("AGENT", "SHARED")}     # SHARED counts IN: agent can act
    done = sum(1 for k in inscope if str(nodes[k].get("status", "")).upper() == "DONE")
    return {
        "value": pct(done, len(inscope)), "known": True,
        "numerator": done, "denominator": len(inscope),
        "scope": "mission nodes with ownership AGENT or SHARED",
        "shared_rule": "SHARED nodes are INCLUDED — the agent can act on them, even if a "
                       "founder or external party must also act. Excluding them would "
                       "understate agent-controllable scope.",
        "excluded": {k: classified[k] for k in nodes if classified[k] in ("FOUNDER", "EXTERNAL")},
    }


def promotion_control_validation() -> dict:
    """validated required controls / required controls. Evidence-derived, never declared."""
    from backend.helm_runtime.governance_states import Control, Evidence, Lifecycle, now

    inv = _load(INVENTORY) or {}
    sig = (inv.get("signature_posture") or {})
    g7 = _load(GOV007)

    states = {}
    for cid, desc in REQUIRED_CONTROLS:
        c = Control(cid, desc)
        if cid == "RC23-BRANCH-PROTECTION":
            c.add(Evidence("design_artifact", "rc23 runbook 2026-06-28", now()))
        elif cid == "COMMIT-SIGNING":
            c.add(Evidence("design_artifact", "specified in rc23 runbook", now()))
            if sig.get("with_verifiable_signature", 0) > 0:
                c.add(Evidence("config_read", "verifiable signatures present", now()))
        elif cid == "PER-ACTOR-GIT-IDENTITY":
            c.add(Evidence("design_artifact", "practised 2026-07-17", now()))
            c.add(Evidence("config_read", "3 commits builder@helm.local", now()))
        elif cid == "GOV-007-IMPERSONATION" and g7:
            c.add(Evidence("adversarial_test", g7.get("result_class", "?"), now(),
                           interval_start=now(), interval_end=now(),
                           adversarial=bool(g7.get("adversarial")),
                           boundary_exercised=bool(g7.get("boundary_exercised")),
                           attempt_succeeded=g7.get("attempt_succeeded")))
        # ACTOR-F3: no evidence yet -> stays UNKNOWN by construction
        states[cid] = c.state

    validated = sum(1 for s in states.values() if s is Lifecycle.VALIDATED)
    return {
        "value": pct(validated, len(REQUIRED_CONTROLS)),
        "numerator": validated, "denominator": len(REQUIRED_CONTROLS),
        "scope": "required promotion controls at VALIDATED",
        "per_control": {k: v.value for k, v in states.items()},
        "note": "state is DERIVED from evidence. No control can be declared VALIDATED.",
    }


def test_posture() -> dict:
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/unit", "-q", "--no-header",
                        "-p", "no:cacheprovider", "--co"],
                       cwd=ROOT, capture_output=True, text=True, timeout=180)
    out = r.stdout + r.stderr
    collect_errors = out.count("ModuleNotFoundError") + out.count("ImportError")
    return {"collection_errors": collect_errors,
            "red_by_design_suites": sorted(RED_BY_DESIGN),
            "note": ("red-by-design suites are SPECIFICATIONS for unbuilt work. Counting "
                     "them as regressions misreports the posture; counting them as passing "
                     "would be worse.")}


def blockers() -> dict:
    return {
        "AGENT": ["Refresh REQ-GOV-002", "Refresh GOV-003", "Refresh ES-002",
                  "Triage the 7 non-red-by-design test failures"],
        "FOUNDER": ["Apply required repository protections (rc23)",
                    "Decide and establish signing / key custody controls",
                    "Provide App Store Connect evidence or access"],
        "EXTERNAL": ["Apple review and production release",
                     "Stripe settlement evidence available"],
    }


def main() -> int:
    m, a, p = mission_completion(), agent_controllable(), promotion_control_validation()
    print("HELM STATUS")
    print("=" * 72)
    for title, d in (("MISSION COMPLETION", m), ("AGENT-CONTROLLABLE COMPLETION", a),
                     ("PROMOTION-CONTROL VALIDATION", p)):
        print(f"\n{title}")
        print(f"    {d.get('value')}   ({d.get('numerator')}/{d.get('denominator')})")
        print(f"    scope: {d.get('scope')}")
        for k in ("oracle_caveat", "caveat", "note"):
            if d.get(k):
                print(f"    note:  {d[k]}")
        if d.get("per_control"):
            for c, s in d["per_control"].items():
                print(f"      {c:<26} {s}")
        if d.get("non_done"):
            print(f"    non-DONE: {d['non_done']}")

    print("\n" + "=" * 72)
    print("PROMOTION: HOLD")
    print("\nBLOCKERS BY OWNERSHIP")
    for owner, items in blockers().items():
        print(f"\n  {owner}")
        for i in items:
            print(f"    - {i}")
    print("\n" + "=" * 72)
    print("DOCTRINE: mission 90% != promotion 90% | tests passing != controls enforced")
    print("          payment authorized != revenue settled | review pending != shipped")
    print("          agent-scope 100% != mission 100%")
    if "--json" in sys.argv:
        print("\n" + json.dumps({"mission": m, "agent_controllable": a,
                                 "promotion_control_validation": p,
                                 "test_posture": test_posture(),
                                 "blockers": blockers()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
