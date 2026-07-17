"""HELM Mission Assurance Index (HMAI) — the composite readiness index.

DOCTRINE (inherits the repo-wide NO FAKE GREEN rule)
----------------------------------------------------
HMAI answers ONE Layer-1 question in under five seconds: *can this mission
safely proceed right now, and if not, what needs founder action?*

It is a weighted composite (0-100) of independent PILLARS. Every pillar is
derived from a REAL evidence file on disk. Nothing is invented:

    mission_execution   <- coordination/goal/goal_state.json          (north_star / champion / autonomy)
    evidence_freshness  <- mtimes of the live runtime-truth signals    (goal / factories / runtime / wall)
    founder_approvals   <- goal_state.metrics.founder_only_actions_pending
    runtime_truth       <- coordination/council/active_runtime_source.json + factory_registry.json
    cyber_security      <- coordination/security/helm_control_posture.json (NIST 800-53 ConMon)
    ai_governance       <- (no live producer)  -> honest UNKNOWN / PLANNED
    supply_chain_zt     <- helm_control_posture.json SR-3/SC-7/AC-3 + conmon_ledger.jsonl

Each pillar carries its OWN state, reusing the doctrine states:
    VERIFIED  fresh evidence, healthy signal
    DEGRADED  fresh evidence, but the signal shows a real problem / partial coverage
    STALE     evidence exists but is older than its freshness SLA
    UNKNOWN   no evidence producer yet — NEVER rendered as green, NEVER scored as pass

COMPOSITE RULE (the anti-fake-green core)
-----------------------------------------
    composite = sum(weight_i * score_i  for pillars that have a real score)
                --------------------------------------------------------------
                                 sum(weight_i for ALL pillars)

UNKNOWN pillars contribute ZERO to the numerator but keep their weight in the
denominator, so a missing pillar DRAGS THE INDEX DOWN — it can never lift it.
A `coverage_pct` is reported explicitly so the reader knows how much of the
index is actually evidenced. This is a deliberate down-weight, not a hide.

This module is read-only. It mutates nothing.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]

GOAL_STATE = ROOT / "coordination" / "goal" / "goal_state.json"
CHAMPION_GATES = ROOT / "coordination" / "goal" / "champion_gates.json"
RUNTIME_POINTER = ROOT / "coordination" / "council" / "active_runtime_source.json"
FACTORY_REGISTRY = ROOT / "coordination" / "council" / "factory_registry.json"
WALL_SIGNAL = ROOT / "coordination" / "council" / "factory_registry.json"  # wall reads factory truth
SECURITY_POSTURE = ROOT / "coordination" / "security" / "helm_control_posture.json"
CONMON_LEDGER = ROOT / "coordination" / "security" / "conmon_ledger.jsonl"

# Doctrine states (reused verbatim from the wall / truth modules).
VERIFIED = "VERIFIED"
DEGRADED = "DEGRADED"
STALE = "STALE"
UNKNOWN = "UNKNOWN"

# A pillar in these states carries NO real score and is treated as un-evidenced
# in the composite numerator (down-weighted, never green).
UNSCORED_STATES = {UNKNOWN}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(p: Path) -> Optional[dict]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _age_seconds(p: Path) -> Optional[float]:
    try:
        return float(time.time() - p.stat().st_mtime)
    except Exception:
        return None


def _freshness_state(age: Optional[float], sla_seconds: float) -> str:
    """VERIFIED if fresh, STALE if past SLA, UNKNOWN if no timestamp."""
    if age is None:
        return UNKNOWN
    return VERIFIED if age <= sla_seconds else STALE


def _pillar(
    key: str,
    label: str,
    weight: float,
    state: str,
    score: Optional[float],
    source: str,
    age_seconds: Optional[float],
    detail: str,
    evidence: Optional[List[str]] = None,
) -> Dict[str, Any]:
    scored = state not in UNSCORED_STATES and score is not None
    return {
        "key": key,
        "label": label,
        "weight": weight,
        "state": state,
        "score": round(float(score), 1) if scored else None,
        # Green requires BOTH a fresh-verified state AND a high score. A DEGRADED
        # or STALE pillar is never green even if its score is high (no fake green).
        "counts_as_green": bool(state == VERIFIED and score is not None and score >= 85.0),
        "scored": scored,
        "source": source,
        "age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
        "detail": detail,
        "evidence": evidence or ([source] if source else []),
    }


# --------------------------------------------------------------------------- #
# PILLAR PRODUCERS — one function per pillar, each fail-closed to UNKNOWN.
# --------------------------------------------------------------------------- #
def _pillar_mission_execution() -> Dict[str, Any]:
    src = "coordination/goal/goal_state.json"
    gs = _load_json(GOAL_STATE)
    age = _age_seconds(GOAL_STATE)
    if not gs:
        return _pillar("mission_execution", "Mission Execution", 20.0,
                       UNKNOWN, None, src, age, "goal_state.json missing or unreadable")
    m = gs.get("metrics", {}) or {}
    parts = []
    for k in ("north_star_completion", "champion_product_completion",
              "autonomous_execution_coverage"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            parts.append(float(v))
    if not parts:
        return _pillar("mission_execution", "Mission Execution", 20.0,
                       UNKNOWN, None, src, age, "no numeric mission metrics present")
    score = sum(parts) / len(parts)
    # Fresh evidence but an unresolved critical-path blocker => DEGRADED not VERIFIED.
    blocker = m.get("current_critical_path_blocker")
    fstate = _freshness_state(age, 24 * 3600)  # goal_state SLA: 24h
    if fstate == STALE:
        state = STALE
    elif blocker:
        state = DEGRADED
    else:
        state = VERIFIED
    detail = (f"north_star={m.get('north_star_completion')} "
              f"champion={m.get('champion_product_completion')} "
              f"autonomy={m.get('autonomous_execution_coverage')} "
              f"blocker={blocker or 'none'}")
    return _pillar("mission_execution", "Mission Execution", 20.0,
                   state, score, src, age, detail)


def _pillar_evidence_freshness() -> Dict[str, Any]:
    """Freshness of the four live runtime-truth signals. The pillar score is how
    fresh the OLDEST signal is, relative to a 15-minute liveness SLA."""
    sla = 15 * 60  # 900s — HELM runs a continuous freshness refresher
    signals = {
        "goal_state.json": GOAL_STATE,
        "factory_registry.json": FACTORY_REGISTRY,
        "active_runtime_source.json": RUNTIME_POINTER,
        "champion_gates.json": CHAMPION_GATES,
    }
    ages: Dict[str, Optional[float]] = {name: _age_seconds(p) for name, p in signals.items()}
    present = {k: v for k, v in ages.items() if v is not None}
    if not present:
        return _pillar("evidence_freshness", "Evidence Freshness", 15.0,
                       UNKNOWN, None, "runtime truth signals", None,
                       "no runtime-truth signal files present")
    worst = max(present.values())
    # linear score: 100 at age 0, 0 at age = 24h (past which it is clearly dead)
    dead = 24 * 3600
    score = max(0.0, 100.0 * (1.0 - worst / dead))
    state = VERIFIED if worst <= sla else (STALE if worst <= dead else STALE)
    if worst > sla:
        state = STALE
    detail = "; ".join(
        f"{name}={'MISSING' if ages[name] is None else str(round(ages[name]))+'s'}"
        for name in signals
    )
    return _pillar("evidence_freshness", "Evidence Freshness", 15.0,
                   state, score, "coordination/goal + coordination/council signals",
                   worst, f"oldest live signal {round(worst)}s (SLA {sla}s) | {detail}",
                   evidence=[f"coordination/**/{n}" for n in signals])


def _pillar_founder_approvals() -> Dict[str, Any]:
    src = "coordination/goal/goal_state.json"
    gs = _load_json(GOAL_STATE)
    age = _age_seconds(GOAL_STATE)
    if not gs:
        return _pillar("founder_approvals", "Founder Approvals", 10.0,
                       UNKNOWN, None, src, age, "goal_state.json unreadable")
    pending = (gs.get("metrics", {}) or {}).get("founder_only_actions_pending")
    if pending is None:
        return _pillar("founder_approvals", "Founder Approvals", 10.0,
                       UNKNOWN, None, src, age, "founder_only_actions_pending not published")
    n = len(pending)
    # 0 pending = fully clear (100). Each pending founder-gate drops readiness.
    score = max(0.0, 100.0 - 25.0 * n)
    fstate = _freshness_state(age, 24 * 3600)
    if fstate == STALE:
        state = STALE
    elif n == 0:
        state = VERIFIED
    else:
        state = DEGRADED  # founder action is REQUIRED — an honest attention state
    detail = (f"{n} founder-only action(s) pending: {', '.join(pending) if pending else 'none'}")
    return _pillar("founder_approvals", "Founder Approvals", 10.0,
                   state, score, src, age, detail)


def _pillar_runtime_truth() -> Dict[str, Any]:
    ptr = _load_json(RUNTIME_POINTER)
    reg = _load_json(FACTORY_REGISTRY)
    ptr_age = _age_seconds(RUNTIME_POINTER)
    src = "coordination/council/active_runtime_source.json + factory_registry.json"
    if not ptr and not reg:
        return _pillar("runtime_truth", "Runtime Truth", 15.0,
                       UNKNOWN, None, src, ptr_age, "no runtime pointer and no factory registry")
    # (a) runtime source published & fresh -> 50 pts
    published = bool(ptr and ptr.get("published_at"))
    ptr_fresh = ptr_age is not None and ptr_age <= 15 * 60
    src_pts = 50.0 if (published and ptr_fresh) else (25.0 if published else 0.0)
    # (b) productised factories that are actually healthy -> up to 50 pts
    fac_pts = 0.0
    total_fac = 0
    ready_fac = 0
    if reg and isinstance(reg.get("factories"), dict):
        for fid, f in reg["factories"].items():
            # only count factories that carry a declared product / readiness basis
            basis = (f or {}).get("readiness_basis") or ""
            if not basis:
                continue
            total_fac += 1
            health = (f or {}).get("health")
            readiness = (f or {}).get("readiness")
            if health == "ACTIVE" or readiness == "READY":
                ready_fac += 1
            elif health in ("PARTIAL",) or readiness == "DEGRADED":
                ready_fac += 0.5  # partial credit — evidenced, not green
        if total_fac:
            fac_pts = 50.0 * (ready_fac / total_fac)
    score = src_pts + fac_pts
    # State: fresh published source + at least one fully-ready factory => VERIFIED,
    # else DEGRADED; stale pointer => STALE.
    if ptr_age is not None and ptr_age > 15 * 60:
        state = STALE
    elif published and ptr_fresh and total_fac and ready_fac >= 1:
        state = VERIFIED if score >= 75 else DEGRADED
    else:
        state = DEGRADED
    detail = (f"runtime_source_published={published} pointer_age="
              f"{round(ptr_age) if ptr_age is not None else 'NA'}s | "
              f"factories ready/partial {round(ready_fac,1)}/{total_fac}")
    return _pillar("runtime_truth", "Runtime Truth", 15.0,
                   state, score, src, ptr_age, detail)


def _pillar_cyber_security() -> Dict[str, Any]:
    src = "coordination/security/helm_control_posture.json"
    pos = _load_json(SECURITY_POSTURE)
    age = _age_seconds(SECURITY_POSTURE)
    if not pos:
        return _pillar("cyber_security", "Cyber / Security", 15.0,
                       UNKNOWN, None, src, age, "no ConMon posture assessment on disk")
    pct = pos.get("posture_percent")
    high = pos.get("high_findings")
    openf = pos.get("open_findings")
    if not isinstance(pct, (int, float)):
        return _pillar("cyber_security", "Cyber / Security", 15.0,
                       UNKNOWN, None, src, age, "posture_percent not published")
    score = float(pct)
    # High-severity findings are a hard readiness ceiling.
    if isinstance(high, int) and high > 0:
        score = min(score, 40.0)
    fstate = _freshness_state(age, 24 * 3600)
    if fstate == STALE:
        state = STALE
    elif isinstance(high, int) and high > 0:
        state = DEGRADED
    elif isinstance(openf, int) and openf > 0:
        state = DEGRADED
    else:
        state = VERIFIED
    detail = (f"posture={pct}% (scope={pos.get('posture_percent_scope')}) "
              f"high_findings={high} open_findings={openf} "
              f"controls={pos.get('implemented')}/{pos.get('controls_assessed')}")
    return _pillar("cyber_security", "Cyber / Security", 15.0,
                   state, score, src, age, detail)


def _pillar_ai_governance() -> Dict[str, Any]:
    """No live AI-governance producer exists in the repo (only frontend fixtures
    and a design doc). Honesty requires UNKNOWN / PLANNED, never a green square."""
    return _pillar(
        "ai_governance", "AI Governance", 10.0,
        UNKNOWN, None, "(no live producer)", None,
        "PLANNED: no runtime AI-governance evidence producer yet — "
        "reported UNKNOWN so it can never be scored as green",
        evidence=[],
    )


def _pillar_supply_chain_zt() -> Dict[str, Any]:
    """Supply-chain / ConMon / Zero-Trust posture, derived from the REAL NIST
    controls in helm_control_posture.json (SR-3 supply chain, SC-7 boundary,
    AC-3 access enforcement) plus the presence of a ConMon ledger.

    Partial real evidence exists, so this is DEGRADED (evidenced but incomplete),
    NOT invented green. If the posture file is absent it fails to UNKNOWN."""
    src = "coordination/security/helm_control_posture.json (SR-3/SC-7/AC-3) + conmon_ledger.jsonl"
    pos = _load_json(SECURITY_POSTURE)
    age = _age_seconds(SECURITY_POSTURE)
    if not pos or not isinstance(pos.get("controls"), list):
        return _pillar("supply_chain_zt", "Supply Chain / ConMon / Zero Trust", 15.0,
                       UNKNOWN, None, src, age, "no ConMon posture with controls on disk")
    watch = {"SR-3", "SC-7", "AC-3", "CA-7"}  # supply chain, boundary, zero-trust access, conmon
    found = {c.get("control_id"): c.get("status") for c in pos["controls"]
             if c.get("control_id") in watch}
    if not found:
        return _pillar("supply_chain_zt", "Supply Chain / ConMon / Zero Trust", 15.0,
                       UNKNOWN, None, src, age,
                       "none of SR-3/SC-7/AC-3/CA-7 present in posture")
    impl = sum(1 for s in found.values() if s == "IMPLEMENTED")
    total = len(found)
    score = 100.0 * impl / total
    conmon_live = CONMON_LEDGER.exists() and CONMON_LEDGER.read_text().strip() != ""
    fstate = _freshness_state(age, 24 * 3600)
    if fstate == STALE:
        state = STALE
    elif impl == total:
        state = VERIFIED
    else:
        state = DEGRADED  # e.g. SR-3 TOOL_DIGEST_MISMATCH is unresolved
    unmet = [cid for cid, s in found.items() if s != "IMPLEMENTED"]
    detail = (f"{impl}/{total} controls implemented "
              f"({', '.join(f'{k}={v}' for k, v in sorted(found.items()))}) | "
              f"conmon_ledger={'live' if conmon_live else 'absent'} | "
              f"unmet={unmet or 'none'}")
    return _pillar("supply_chain_zt", "Supply Chain / ConMon / Zero Trust", 15.0,
                   state, score, src, age, detail)


PILLAR_PRODUCERS = (
    _pillar_mission_execution,
    _pillar_evidence_freshness,
    _pillar_founder_approvals,
    _pillar_runtime_truth,
    _pillar_cyber_security,
    _pillar_ai_governance,
    _pillar_supply_chain_zt,
)


def _band(index: Optional[float]) -> str:
    if index is None:
        return UNKNOWN
    if index >= 85:
        return "MISSION_READY"
    if index >= 70:
        return "OPERATIONAL_ATTENTION"
    if index >= 50:
        return "AT_RISK"
    return "NOT_READY"


def compute_hmai() -> Dict[str, Any]:
    """Compute the HELM Mission Assurance Index from live repo evidence.

    Returns a composite 0-100 index, per-pillar breakdown (each with its own
    state + freshness), a can-safely-proceed boolean, and the top-3 reasons.
    """
    pillars = [producer() for producer in PILLAR_PRODUCERS]

    total_weight = sum(p["weight"] for p in pillars)
    scored = [p for p in pillars if p["scored"]]
    scored_weight = sum(p["weight"] for p in scored)

    # Composite: UNKNOWN pillars keep their weight in the denominator (down-weight),
    # contribute zero to the numerator — they can only DRAG the index down.
    numerator = sum(p["weight"] * p["score"] for p in scored)
    composite = round(numerator / total_weight, 1) if total_weight else None
    coverage_pct = round(100.0 * scored_weight / total_weight, 1) if total_weight else 0.0

    unknown_pillars = [p["key"] for p in pillars if p["state"] == UNKNOWN]
    stale_pillars = [p["key"] for p in pillars if p["state"] == STALE]
    degraded_pillars = [p["key"] for p in pillars if p["state"] == DEGRADED]

    # ---- can this mission safely proceed? ------------------------------------
    # Autonomous operation is safe to continue only if: no high-severity security
    # finding, mission execution is evidenced & fresh, runtime truth is not UNKNOWN,
    # and evidence is not STALE. Founder-only external gates (App Store) do NOT block
    # autonomous operation — they block SHIP, and are surfaced separately.
    by_key = {p["key"]: p for p in pillars}
    blockers: List[str] = []

    sec = by_key.get("cyber_security", {})
    if sec.get("state") == UNKNOWN:
        blockers.append("Cyber/Security posture is UNKNOWN — no live ConMon evidence")
    elif sec.get("score") is not None and sec["score"] <= 40:
        blockers.append("Cyber/Security below floor (high-severity finding open)")

    me = by_key.get("mission_execution", {})
    if me.get("state") in (UNKNOWN, STALE):
        blockers.append(f"Mission Execution evidence is {me.get('state')}")

    rt = by_key.get("runtime_truth", {})
    if rt.get("state") == UNKNOWN:
        blockers.append("Runtime Truth is UNKNOWN — no canonical runtime source")

    if stale_pillars:
        blockers.append(f"Stale evidence: {', '.join(stale_pillars)}")

    if composite is None or composite < 50:
        blockers.append(f"Composite index below 50 ({composite})")

    can_proceed = len(blockers) == 0

    # ---- top 3 reasons -------------------------------------------------------
    # Rank by the size of the readiness gap each pillar leaves on the table
    # (weight-scaled shortfall from 100, UNKNOWN counted as full shortfall).
    def _shortfall(p: Dict[str, Any]) -> float:
        if p["state"] == UNKNOWN or p["score"] is None:
            return p["weight"] * 100.0  # full gap — un-evidenced
        return p["weight"] * (100.0 - p["score"])

    ranked = sorted(pillars, key=_shortfall, reverse=True)
    top_reasons = []
    for p in ranked[:3]:
        top_reasons.append({
            "pillar": p["key"],
            "label": p["label"],
            "state": p["state"],
            "score": p["score"],
            "weight": p["weight"],
            "why": p["detail"],
        })

    # ---- founder action (surfaced separately from autonomous-proceed) --------
    gs = _load_json(GOAL_STATE) or {}
    founder_pending = (gs.get("metrics", {}) or {}).get("founder_only_actions_pending") or []
    next_task = gs.get("next_recommended_task") or {}

    return {
        "index": composite,
        "band": _band(composite),
        "coverage_pct": coverage_pct,
        "coverage_note": (
            "coverage_pct is the share of index weight backed by real evidence. "
            "UNKNOWN pillars are excluded from the numerator but kept in the "
            "denominator, so they down-weight the index and can never make it green."
        ),
        "can_mission_safely_proceed": can_proceed,
        "proceed_scope": "autonomous operation (SHIP still gated on founder-only actions below)",
        "top_reasons": top_reasons,
        "proceed_blockers": blockers,
        "pillars": pillars,
        "pillar_state_counts": {
            "VERIFIED": sum(1 for p in pillars if p["state"] == VERIFIED),
            "DEGRADED": len(degraded_pillars),
            "STALE": len(stale_pillars),
            "UNKNOWN": len(unknown_pillars),
        },
        "unknown_pillars": unknown_pillars,
        "founder_only_actions_pending": founder_pending,
        "recommended_next_action": next_task,
        "computed_at": _now_iso(),
        "doctrine": (
            "HMAI is re-derived from live evidence on every call. UNKNOWN is never "
            "green and never scored as pass; a missing pillar lowers the index. "
            "No fake green."
        ),
    }


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import pprint
    pprint.pprint(compute_hmai())
