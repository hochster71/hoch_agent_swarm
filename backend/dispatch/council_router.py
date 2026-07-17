"""Council Router — HELM assigns the mission to the lane that owns it.

The founder does NOT pick a model. HELM classifies each ask into a capability,
resolves the capability → owning role → provider binding, and dispatches to that
member autonomously. For missions that need the whole brain, `orchestrate()` runs
the governed chain: Orchestrator plans → Builder solves → Auditor verifies.

Everything is fail-closed (a lane whose provider isn't enabled returns BLOCKED, never
a fake answer) and every hop is recorded on the event bus. No brand is hard-coded in
callers — routing is by capability, exactly as the Constitution requires.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.helm_runtime.capability_registry import route_capability
from backend.helm_runtime.dispatch_gateway import DispatchNotEnabledError
from backend.dispatch.live_gateway import dispatch as live_dispatch, autoload_env
from backend.dispatch.live_adapters import provider_configured, dispatch_globally_enabled

# --- Lane classification -------------------------------------------------------
# Capability → the ask-shapes that belong to it. First match wins; the registry
# then resolves capability → role → provider. Keep this brand-free.
_LANE_SIGNALS: List[Tuple[str, List[str]]] = [
    ("verification", [
        r"\bverif", r"\baudit", r"\bred[\s-]?team", r"\badversar", r"\bregression",
        r"\bsecurity\b", r"\bpen[\s-]?test", r"\bprove\b", r"\battack\b", r"\bassur",
        r"\bcheck (that|whether|if)\b", r"\bconfirm\b", r"\bvalidate the",
    ]),
    ("architecture", [
        r"\barchitect", r"\bdesign (the|a|an) (system|api|schema|module|service)",
        r"\bedr\b", r"\bengineering decision", r"\btrade[\s-]?off",
    ]),
    ("python", [
        r"\bwrite (code|a script|a function|python|tests?|the|a|an|this)\b",
        r"\bimplement\b", r"\bcode\b", r"\brefactor",
        r"\bfix (the|a|this) (bug|test|error)", r"\bbuild (the|a|an)\b",
        r"\bpytest", r"\bunit test", r"\bwebhook", r"\bhandler\b",
        r"\bendpoint", r"\bfunction\b", r"\bscript\b", r"\bwire (up|the)\b",
    ]),
    ("planning", [
        r"\bplan\b", r"\bdecompos", r"\bsequence\b", r"\broadmap", r"\bnext (\d+ )?(steps|tasks)",
        r"\bprioriti", r"\bschedule\b", r"\bwhat should we do", r"\bhow do we (get|move)",
        r"\bstrateg", r"\bcoordinate",
    ]),
]

_LANE_HUMAN = {
    "planning": "Orchestrator lane (planning / decomposition)",
    "decomposition": "Orchestrator lane (decomposition)",
    "architecture": "Builder lane (architecture)",
    "python": "Builder lane (engineering)",
    "testing": "Builder lane (testing)",
    "verification": "Auditor lane (independent verification)",
    "red_team": "Auditor lane (red team)",
}


def classify(prompt: str) -> Tuple[str, str]:
    """Infer the owning capability for an ask. Returns (capability, reason).

    Defaults to `planning` (Orchestrator) when nothing else matches — an unclassified
    mission is a planning problem: HELM asks the Chief of Staff to break it down.
    """
    text = (prompt or "").lower()
    for capability, patterns in _LANE_SIGNALS:
        for pat in patterns:
            if re.search(pat, text):
                return capability, f"matched lane signal /{pat}/ → {capability}"
    return "planning", "no specific lane signal; defaulting to Orchestrator planning lane"


def _resolve_lane(capability: str) -> Dict[str, Any]:
    """capability → role (via registry). Adds a human label. No provider call yet."""
    r = route_capability(capability)
    role = r.get("role") if r.get("resolved") else None
    return {
        "capability": capability,
        "resolved": bool(role),
        "role": role,
        "all_roles": r.get("all_roles", []),
        "lane": _LANE_HUMAN.get(capability, capability),
        "reason": r.get("reason"),
    }


def _record(kind: str, payload: Dict[str, Any]) -> None:
    try:
        from backend.helm_runtime.event_bus import publish_event
        publish_event(type=kind, producer="council_router", mission_id="COUNCIL", payload=payload)
    except Exception:
        pass  # event bus is best-effort; never block a dispatch on telemetry


def solve(prompt: str, *, hint_capability: Optional[str] = None) -> Dict[str, Any]:
    """Autonomous single-lane solve. HELM picks the lane, routes, and returns the answer.

    Never raises for a disabled lane — returns a BLOCKED status the UI can render honestly.
    """
    autoload_env()
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty_prompt"}

    if hint_capability:
        capability, reason = hint_capability, f"caller hinted capability={hint_capability}"
    else:
        capability, reason = classify(prompt)
    lane = _resolve_lane(capability)
    routing = {"capability": capability, "classification_reason": reason, **lane}

    if not lane["resolved"]:
        _record("COUNCIL_ROUTE_UNRESOLVED", {"capability": capability})
        return {"ok": False, "status": "UNROUTABLE", "routing": routing,
                "message": f"No lane advertises capability {capability!r}."}

    role = lane["role"]
    try:
        r = live_dispatch(role=role, capability=capability, prompt=prompt)
    except DispatchNotEnabledError as e:
        _record("COUNCIL_LANE_BLOCKED", {"role": role, "capability": capability})
        return {"ok": False, "status": "BLOCKED_EXTERNAL", "routing": routing,
                "message": str(e),
                "howto": "Founder enables this lane: add its provider key to ~/.helm/helm.env + HELM_DISPATCH_ENABLED=1"}
    except Exception as e:  # provider/network error — honest, not fake-green
        _record("COUNCIL_LANE_ERROR", {"role": role, "capability": capability, "error": str(e)[:200]})
        return {"ok": False, "status": "PROVIDER_ERROR", "routing": routing, "message": str(e)[:300]}

    _record("COUNCIL_SOLVED", {"role": role, "capability": capability,
                               "provider": r.get("provider"), "model": r.get("model"),
                               "prompt_chars": len(prompt)})
    return {"ok": True, "status": "SOLVED", "routing": routing,
            "provider": r.get("provider"), "model": r.get("model"),
            "text": r.get("text", ""), "usage": r.get("usage")}


def orchestrate(prompt: str) -> Dict[str, Any]:
    """Full-brain governed chain: Orchestrator plans → Builder solves → Auditor verifies.

    Each hop degrades honestly: if a lane's provider isn't enabled, that hop is marked
    BLOCKED and the chain continues with what IS available. HELM decides; models advise.
    """
    autoload_env()
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty_prompt"}

    steps: List[Dict[str, Any]] = []

    # 1) Orchestrator plans the mission.
    plan = solve(
        f"You are the HELM Orchestrator (Chief of Staff). Decompose this mission into a "
        f"concrete ordered plan; for each step name the owning lane (builder/auditor) and "
        f"the dependency. Mission:\n\n{prompt}",
        hint_capability="planning",
    )
    steps.append({"phase": "PLAN", "lane": "Orchestrator", **plan})

    # 2) Builder solves against the plan (or the raw mission if planning was blocked).
    build_context = plan.get("text") if plan.get("ok") else prompt
    build = solve(
        f"You are the HELM Builder. Execute the engineering work for this mission. "
        f"Produce the concrete artifact (code / design / decision) the plan calls for.\n\n"
        f"Mission:\n{prompt}\n\nPlan:\n{build_context}",
        hint_capability="python",
    )
    steps.append({"phase": "BUILD", "lane": "Builder", **build})

    # 3) Auditor verifies the builder's output.
    audit_target = build.get("text") if build.get("ok") else "(no builder output — lane blocked)"
    audit = solve(
        f"You are the HELM Auditor. Independently verify the following work against the "
        f"mission. State VERIFIED / VERIFIED_WITH_LIMITATIONS / REJECTED with reasons. Do not "
        f"rubber-stamp.\n\nMission:\n{prompt}\n\nWork to verify:\n{audit_target}",
        hint_capability="verification",
    )
    steps.append({"phase": "VERIFY", "lane": "Auditor", **audit})

    enabled = [s["phase"] for s in steps if s.get("ok")]
    blocked = [s["phase"] for s in steps if not s.get("ok")]
    _record("COUNCIL_ORCHESTRATED", {"enabled": enabled, "blocked": blocked})
    return {"ok": bool(enabled), "mode": "orchestrate", "steps": steps,
            "enabled_phases": enabled, "blocked_phases": blocked}


def council_status() -> Dict[str, Any]:
    """Live per-lane readiness — which council members HELM can currently fire.

    Presence only; never reads or returns a key value.
    """
    autoload_env()
    lanes = [
        ("orchestrator", "openai", "planning", "Orchestrator", "Plans & sequences the mission"),
        ("builder", "anthropic", "python", "Builder", "Engineers the solution & records EDRs"),
        ("auditor", "xai", "verification", "Auditor", "Independently verifies — no rubber-stamp"),
        ("local", "local", None, "Local", "Private-data lane (family/home/finance)"),
    ]
    money_gate = dispatch_globally_enabled()
    members = []
    for role, provider, cap, name, mandate in lanes:
        configured = provider_configured(provider)
        ready = configured and money_gate
        if ready:
            status = "READY"
        elif configured and not money_gate:
            status = "GATED"          # key present, founder money-gate off
        else:
            status = "BLOCKED_EXTERNAL"  # credential not supplied
        members.append({
            "role": role, "provider": provider, "owns_capability": cap,
            "display_name": name, "mandate": mandate,
            "configured": configured, "ready": ready, "status": status,
        })
    ready_count = sum(1 for m in members if m["ready"])
    return {"schema": "HELM_COUNCIL_STATUS_v1", "members": members,
            "ready_count": ready_count, "total": len(members),
            "money_gate_enabled": money_gate,
            "note": "presence only; no key value is ever read or returned"}
