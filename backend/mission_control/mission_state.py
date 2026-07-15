"""Mission State Engine — single authoritative operational state for a mission.

Every interface (voice, dashboard, CLI, mobile, Grok tools) should read this
document rather than re-interpreting raw ledgers.

Doctrine:
  - Derived only from existing Runtime Truth / goal engine / champion gates / conmon
  - No fake green: UNKNOWN and founder-pending stay explicit
  - Monetization PASS ≠ revenue
  - overall status reflects external blockers honestly
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
GOAL_STATE = ROOT / "coordination" / "goal" / "goal_state.json"
CHAMPION_GATES = ROOT / "coordination" / "goal" / "champion_gates.json"
POSTURE = ROOT / "coordination" / "security" / "helm_control_posture.json"
OUT = ROOT / "coordination" / "goal" / "mission_state.json"

# Canonical mission ids map to champion / product codes
DEFAULT_MISSION_ID = "EPIC-FURY-2026"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _age_hours(path: Path) -> Optional[float]:
    if not path.exists():
        return None
    return round((time.time() - path.stat().st_mtime) / 3600.0, 2)


def _conf(status: str, *, age_h: Optional[float] = None, sla_h: float = 168.0) -> str:
    if status in ("PENDING", "BLOCKED_EXTERNAL", "NOT_STARTED", "WAITING_FOUNDER"):
        return "Certain"
    if status in ("UNKNOWN", "STALE"):
        return "Low"
    if age_h is not None and age_h > sla_h:
        return "Medium"
    if status in ("VERIFIED", "PASS", "LIVE"):
        return "High"
    if status in ("PARTIAL", "IN_PROGRESS"):
        return "Medium"
    return "Medium"


def _gate_map(gates: List[dict]) -> Dict[str, dict]:
    return {g.get("gate"): g for g in gates if isinstance(g, dict) and g.get("gate")}


def _area(
    name: str,
    status: str,
    *,
    confidence: Optional[str] = None,
    detail: str = "",
    evidence: Optional[List[str]] = None,
    age_h: Optional[float] = None,
) -> Dict[str, Any]:
    return {
        "area": name,
        "status": status,
        "confidence": confidence or _conf(status, age_h=age_h),
        "detail": detail,
        "evidence": evidence or [],
        "evidence_age_hours": age_h,
    }


def build_mission_state(mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Compose mission state from authoritative on-disk / engine artifacts."""
    goal = _load(GOAL_STATE) or {}
    gates_doc = _load(CHAMPION_GATES) or {}
    posture = _load(POSTURE) or {}
    metrics = goal.get("metrics") or {}
    by_layer = goal.get("by_layer") or {}
    gates = _gate_map(gates_doc.get("gates") or [])

    mid = mission_id or metrics.get("champion_product") or gates_doc.get("champion_product") or DEFAULT_MISSION_ID
    mid = str(mid).replace("_", "-")

    goal_age = _age_hours(GOAL_STATE)
    gates_age = _age_hours(CHAMPION_GATES)
    posture_age = _age_hours(POSTURE)

    # --- Engineering (agent CP + ES layers) ---
    cp = by_layer.get("CP") or {}
    es = by_layer.get("ES") or {}
    cp_pct = cp.get("completion_pct_agent_scope")
    es_pct = es.get("completion_pct_agent_scope")
    eng_parts = [p for p in (cp_pct, es_pct) if isinstance(p, (int, float))]
    eng_score = round(sum(eng_parts) / len(eng_parts), 1) if eng_parts else None
    eng_status = (
        "VERIFIED"
        if eng_score is not None and eng_score >= 99.9
        else ("PARTIAL" if eng_score is not None else "UNKNOWN")
    )
    engineering = _area(
        "Engineering",
        eng_status,
        detail=f"agent CP {cp_pct}% · ES {es_pct}% (goal engine)",
        evidence=["coordination/goal/goal_state.json"],
        age_h=goal_age,
    )
    engineering["score_pct"] = eng_score

    # --- Testing ---
    test_g = gates.get("TEST") or {}
    testing = _area(
        "Testing",
        "VERIFIED" if test_g.get("status") == "PASS" else (test_g.get("status") or "UNKNOWN"),
        detail=str(test_g.get("detail") or ""),
        evidence=test_g.get("evidence") or [],
        age_h=test_g.get("evidence_age_hours"),
    )

    # --- Security (champion SECURITY + conmon) ---
    sec_g = gates.get("SECURITY") or {}
    posture_pct = posture.get("posture_percent")
    high = posture.get("high_findings")
    open_f = posture.get("open_findings")
    sec_ok = sec_g.get("status") == "PASS" and (high is None or int(high) == 0)
    security = _area(
        "Security",
        "VERIFIED" if sec_ok else ("PARTIAL" if sec_g.get("status") == "PASS" else (sec_g.get("status") or "UNKNOWN")),
        detail=(
            f"champion SECURITY={sec_g.get('status')}; "
            f"NIST posture {posture_pct}% open={open_f} high={high}"
        ),
        evidence=(sec_g.get("evidence") or []) + (
            ["coordination/security/helm_control_posture.json"] if posture else []
        ),
        age_h=sec_g.get("evidence_age_hours") or posture_age,
    )
    security["posture_percent"] = posture_pct

    # --- Evidence / Runtime Truth ---
    gov = by_layer.get("GOV") or {}
    gov_pct = gov.get("completion_pct_agent_scope")
    evidence_cov = metrics.get("evidence_coverage")
    ev_status = (
        "VERIFIED"
        if isinstance(gov_pct, (int, float)) and gov_pct >= 99.9 and evidence_cov is not None
        else ("PARTIAL" if gov_pct is not None else "UNKNOWN")
    )
    evidence = _area(
        "Evidence",
        ev_status,
        detail=f"GOV agent {gov_pct}% · evidence_coverage field {evidence_cov}",
        evidence=["coordination/goal/goal_state.json"],
        age_h=goal_age,
    )
    runtime_truth = _area(
        "Runtime Truth",
        "VERIFIED" if goal and goal.get("computed_at") and (goal_age is None or goal_age < 24) else "STALE",
        detail=f"goal_state age_h={goal_age}; doctrine no_fake_green",
        evidence=["coordination/goal/goal_state.json"],
        age_h=goal_age,
    )

    # --- Approvals / distribution ---
    founder_pending = list(metrics.get("founder_only_actions_pending") or [])
    tf = gates.get("TESTFLIGHT") or {}
    asc = gates.get("APP_STORE_CONNECT") or {}

    founder_status = "PENDING" if founder_pending else "CLEAR"
    apple_status = "PENDING"
    if tf.get("status") == "PASS" and asc.get("status") == "PASS":
        apple_status = "VERIFIED"
    elif tf.get("status") in ("UNKNOWN", None) or asc.get("status") in ("UNKNOWN", None):
        apple_status = "BLOCKED_EXTERNAL"  # needs ASC credentials / live read

    approvals = {
        "founder": {
            "status": founder_status,
            "pending": founder_pending,
            "confidence": "Certain",
        },
        "apple": {
            "status": apple_status,
            "testflight": tf.get("status") or "UNKNOWN",
            "app_store_connect": asc.get("status") or "UNKNOWN",
            "confidence": "Certain",
            "detail": "Live Apple state requires founder credentials; local ledger claims are not re-verified here",
        },
    }

    distribution = _area(
        "Distribution",
        "BLOCKED_EXTERNAL" if apple_status != "VERIFIED" else "VERIFIED",
        detail="Production distribution blocked until TestFlight + App Store Connect are founder-cleared",
        confidence="Certain",
        evidence=[str(CHAMPION_GATES.relative_to(ROOT))],
        age_h=gates_age,
    )

    # --- Revenue (never confuse with monetization gate) ---
    rev_usd = None
    rev_status = "NOT_STARTED"
    rev_detail = "No verified settled revenue observed"
    try:
        from backend.mission_control.hoch_ledger import HochLedger

        ns = HochLedger().north_star()
        rev_usd = float(ns.get("revenue_settled_usd") or 0)
        if rev_usd > 0:
            rev_status = "LIVE"
            rev_detail = f"Verified settled revenue ${rev_usd:.2f}"
        else:
            rev_status = "NOT_STARTED"
            rev_detail = "$0 verified settled revenue (expected until release earns)"
    except Exception as e:
        rev_status = "UNKNOWN"
        rev_detail = f"ledger unreadable: {e}"

    revenue = _area(
        "Revenue",
        rev_status,
        detail=rev_detail,
        confidence="Certain" if rev_status != "UNKNOWN" else "Low",
        evidence=["coordination/council/revenue_ledger.jsonl"],
    )
    revenue["settled_usd"] = rev_usd

    # --- Critical path steps (executive ladder) ---
    def step(name: str, done: bool, waiting: bool = False, external: bool = False) -> dict:
        if done:
            st = "DONE"
        elif external:
            st = "WAITING_EXTERNAL"
        elif waiting:
            st = "WAITING_FOUNDER"
        else:
            st = "PENDING"
        return {"name": name, "status": st, "mark": "✓" if done else ("⏳" if (waiting or external) else "·")}

    eng_done = eng_status == "VERIFIED"
    sec_done = security["status"] == "VERIFIED"
    ev_done = evidence["status"] == "VERIFIED"
    founder_wait = founder_status == "PENDING"
    apple_wait = apple_status != "VERIFIED"
    ship_done = "REQ-TO-002" not in founder_pending and not apple_wait

    critical_path = [
        step("Engineering", eng_done),
        step("Security", sec_done),
        step("Evidence", ev_done),
        step("Founder Review", not founder_wait, waiting=founder_wait),
        step("Apple Review", not apple_wait, external=apple_wait),
        step("Production Release", ship_done, waiting=not ship_done and not apple_wait, external=apple_wait),
    ]

    # --- Overall ---
    if apple_wait or founder_wait:
        overall = "BLOCKED_EXTERNAL" if apple_wait else "BLOCKED_FOUNDER"
    elif eng_done and sec_done and ev_done:
        overall = "READY_INTERNAL"
    else:
        overall = "IN_PROGRESS"

    next_task = goal.get("next_recommended_task") or {
        "id": metrics.get("current_critical_path_blocker"),
    }

    areas = [
        engineering,
        testing,
        security,
        evidence,
        runtime_truth,
        _area(
            "Apple Review",
            "Waiting on Founder" if apple_wait else "VERIFIED",
            confidence="Certain",
            detail=f"TestFlight={tf.get('status')} ASC={asc.get('status')}",
        ),
        revenue,
        _area("Overall Mission", overall, confidence="High", detail=str((next_task or {}).get("id") or "")),
    ]

    state = {
        "schema": "HELM_MISSION_STATE_v1",
        "mission": {
            "id": mid,
            "champion_product": metrics.get("champion_product") or gates_doc.get("champion_product"),
            "north_star": goal.get("canonical_north_star"),
        },
        "computed_at": _now(),
        "sources": {
            "goal_state": str(GOAL_STATE.relative_to(ROOT)),
            "champion_gates": str(CHAMPION_GATES.relative_to(ROOT)),
            "control_posture": str(POSTURE.relative_to(ROOT)) if POSTURE.exists() else None,
            "goal_computed_at": goal.get("computed_at"),
            "goal_age_hours": goal_age,
        },
        "areas": {a["area"]: a for a in areas},
        "dashboard": [
            {
                "area": a["area"],
                "status": a["status"] if a["area"] != "Engineering" or a.get("score_pct") is None
                else f"{a.get('score_pct')}%",
                "confidence": a["confidence"],
            }
            for a in areas
            if a["area"] != "Overall Mission"
        ]
        + [
            {
                "area": "Overall Mission",
                "status": overall,
                "confidence": "High",
            }
        ],
        "critical_path": critical_path,
        "approvals": approvals,
        "distribution": distribution,
        "revenue": revenue,
        "engineering": engineering,
        "security": security,
        "testing": testing,
        "evidence": evidence,
        "runtime_truth": runtime_truth,
        "overall": {
            "status": overall,
            "confidence": "High",
            "blocker": metrics.get("current_critical_path_blocker"),
            "next": next_task,
        },
        "metrics_snapshot": {
            "north_star_completion": metrics.get("north_star_completion"),
            "champion_product_completion": metrics.get("champion_product_completion"),
            "autonomous_execution_coverage": metrics.get("autonomous_execution_coverage"),
            "evidence_coverage": metrics.get("evidence_coverage"),
        },
        "doctrine": [
            "no_fake_green",
            "monetization_is_not_revenue",
            "founder_and_apple_gates_are_external",
            "single_mission_state_for_all_interfaces",
        ],
    }
    return state


def write_mission_state(mission_id: Optional[str] = None) -> Dict[str, Any]:
    state = build_mission_state(mission_id=mission_id)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def render_executive_text(state: Optional[Dict[str, Any]] = None) -> str:
    """Compact executive report for CLI / voice / chat."""
    s = state or build_mission_state()
    lines = [
        f"MISSION {s['mission']['id']} — overall {s['overall']['status']} ({s['overall']['confidence']})",
        "",
        f"{'Area':<18} {'Status':<28} {'Confidence'}",
        f"{'-'*18} {'-'*28} {'-'*10}",
    ]
    for row in s.get("dashboard") or []:
        lines.append(f"{row['area']:<18} {str(row['status']):<28} {row['confidence']}")
    lines.append("")
    lines.append("Critical Path")
    for step in s.get("critical_path") or []:
        lines.append(f"  {step['mark']} {step['name']} ({step['status']})")
    nxt = (s.get("overall") or {}).get("next") or {}
    if nxt:
        lines.append("")
        lines.append(f"Next: {nxt.get('id')} — {str(nxt.get('statement') or nxt.get('why') or '')[:100]}")
    rev = s.get("revenue") or {}
    lines.append("")
    lines.append(f"Revenue: {rev.get('status')} — {rev.get('detail')}")
    lines.append("Doctrine: no fake green · monetization ≠ revenue · founder/Apple gates external")
    return "\n".join(lines)


def render_speech(state: Optional[Dict[str, Any]] = None) -> str:
    s = state or build_mission_state()
    o = s.get("overall") or {}
    parts = [
        f"Mission {s['mission']['id']}. Overall {o.get('status')}.",
    ]
    for row in s.get("dashboard") or []:
        if row["area"] == "Overall Mission":
            continue
        parts.append(f"{row['area']}: {row['status']}.")
    cp_wait = [c["name"] for c in (s.get("critical_path") or []) if c["status"] != "DONE"]
    if cp_wait:
        parts.append("Still open on critical path: " + ", ".join(cp_wait) + ".")
    nxt = o.get("next") or {}
    if nxt.get("id"):
        parts.append(f"Next recommended: {nxt.get('id')}.")
    return " ".join(parts)
