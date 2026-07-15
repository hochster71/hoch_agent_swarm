"""Leadership role voice agents — founder, ops, ciso, cfo, qa.

Each role reuses Runtime Truth with a role-specific lens and DOORSTEP boundaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.voice.briefing import (
    _count_pending_approvals,
    _factory_lines,
    _goal_lines,
    _next_move_line,
    _observe_sources,
    _repo_lines,
    _task_summary,
    build_executive_brief,
)
from backend.voice.factory_agents import observe_all_registered_factories, observe_factory
from backend.voice.sanitizer import sanitize_for_speech

UNKNOWN = "UNKNOWN"

ROLE_CATALOG: Dict[str, Dict[str, Any]] = {
    "founder": {
        "id": "founder",
        "title": "Founder / Executive Commander",
        "focus": "north star, doorstep, critical path, next lever",
        "doorstep": ["deploy", "spend", "keys", "sign", "app_store", "clear_release_go"],
    },
    "ops": {
        "id": "ops",
        "title": "COO / Mission Control",
        "focus": "runtime, leases, tasks, overnight execution, factory utilization",
        "doorstep": ["deploy", "spend", "keys"],
    },
    "ciso": {
        "id": "ciso",
        "title": "CISO / Security Officer",
        "focus": "security posture, critical path security blockers, integrity",
        "doorstep": ["bypass_approval", "public_exposure", "disable_controls"],
    },
    "cfo": {
        "id": "cfo",
        "title": "CFO / Finance Officer",
        "focus": "spend, revenue honesty, founder-minutes per dollar UNKNOWN when unproven",
        "doorstep": ["spend", "move_money", "stripe_live"],
    },
    "qa": {
        "id": "qa",
        "title": "QA / Final Verifier Voice",
        "focus": "evidence gaps, release authority denial, verification honesty",
        "doorstep": ["clear_release_go", "fake_pass"],
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_roles() -> List[Dict[str, Any]]:
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "focus": r["focus"],
            "path": f"/api/v1/helm/voice/role/{r['id']}",
            "doorstep": r["doorstep"],
        }
        for r in ROLE_CATALOG.values()
    ]


def _role_founder(src: Dict[str, Any]) -> Dict[str, Any]:
    brief = build_executive_brief()
    glabel, glines, gdata = _goal_lines(src)
    acount, alabel, alines = _count_pending_approvals(src)
    parts = [
        "Founder executive lens.",
        brief.get("speech_text") or "",
    ]
    if gdata.get("critical_path_blocker"):
        parts.append(f"Your critical path is {gdata['critical_path_blocker']}.")
    if alabel != "UNKNOWN":
        parts.append(f"Items needing you: {acount}.")
    parts.append("I cannot deploy, spend, provision keys, or clear release GO by voice.")
    return {
        "status": brief.get("status") or "PARTIAL",
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": {**brief.get("labels", {}), "role": "LIVE", "goal": glabel, "approvals": alabel},
        "data": {
            "goal": gdata,
            "approvals_pending": acount if alabel != "UNKNOWN" else None,
            "brief_status": brief.get("status"),
        },
    }


def _role_ops(src: Dict[str, Any]) -> Dict[str, Any]:
    tcount, tlabel, tline = _task_summary(src)
    flabel, flines = _factory_lines(src)
    rt = src.get("runtime")
    rt_unk = isinstance(rt, dict) and rt.get("state") == UNKNOWN
    parts = [
        "Mission control lens.",
        tline,
        " ".join(flines[:2]),
    ]
    if rt_unk:
        parts.append("Runtime: UNKNOWN.")
        rt_label = "UNKNOWN"
    else:
        parts.append(f"Runtime snapshot observed: {str(rt)[:200]}")
        rt_label = "LIVE"
    parts.append(_next_move_line(src))
    roster = observe_all_registered_factories()
    parts.append(f"Registered factory roster status: {roster.get('status')}.")
    status = "LIVE"
    if tlabel == "UNKNOWN" and rt_label == "UNKNOWN":
        status = "UNKNOWN"
    elif tlabel == "UNKNOWN" or flabel in ("UNKNOWN", "STALE") or rt_label == "UNKNOWN":
        status = "PARTIAL"
    return {
        "status": status,
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": {
            "role": "LIVE",
            "tasks": tlabel,
            "factories": flabel,
            "runtime": rt_label,
        },
        "data": {
            "active_tasks": tcount if tlabel != "UNKNOWN" else None,
            "factory_roster_status": roster.get("status"),
        },
    }


def _role_ciso(src: Dict[str, Any]) -> Dict[str, Any]:
    glabel, glines, gdata = _goal_lines(src)
    sec = src.get("security")
    parts = ["CISO lens. Security claims only from observed sources."]
    labels: Dict[str, str] = {"role": "LIVE"}

    # Deep-bind HCF observe (posture + cyber swarm + conmon)
    hcf = observe_factory("HCF")
    parts.append(hcf.get("speech_text") or "HCF: UNKNOWN.")
    labels["hcf"] = hcf.get("status") or "UNKNOWN"
    for k, v in (hcf.get("labels") or {}).items():
        labels[f"hcf_{k}"] = v

    if isinstance(sec, dict) and sec.get("state") == UNKNOWN:
        parts.append(f"live_security helper: UNKNOWN — {sec.get('reason')}.")
        labels["security"] = "UNKNOWN"
    elif isinstance(sec, dict):
        pct = sec.get("posture_percent")
        high = sec.get("high_findings")
        open_f = sec.get("open_findings")
        parts.append(
            f"API security posture percent {pct}, high findings {high}, open {open_f}."
        )
        labels["security"] = "LIVE"
    else:
        labels["security"] = labels.get("hcf_posture") or "UNKNOWN"

    blocker = gdata.get("critical_path_blocker")
    if blocker:
        parts.append(f"Goal critical path blocker: {blocker}.")
        if "SECURITY" in str(blocker).upper():
            parts.append(
                "REQ-CP-SECURITY (or security-class blocker) is binding — "
                "close open NIST gaps and HIGH findings before claiming secure."
            )
    labels["goal"] = glabel

    hasf = observe_factory("HASF")
    parts.append(f"HASF gates: {', '.join((hasf.get('data') or {}).get('gates') or [])}.")
    parts.append("I will not disable controls or bypass approval by voice.")

    status = "PARTIAL"
    if labels.get("security") == "LIVE" or labels.get("hcf") in ("LIVE", "PARTIAL", "STALE"):
        status = "PARTIAL" if "STALE" in str(labels.values()) or labels.get("hcf") == "PARTIAL" else "LIVE"
    if labels.get("security") == "UNKNOWN" and labels.get("hcf") == "UNKNOWN":
        status = "UNKNOWN"
    return {
        "status": status,
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": {
            "hcf": hcf.get("data"),
            "security_api": sec if not (isinstance(sec, dict) and sec.get("state") == UNKNOWN) else None,
            "critical_path_blocker": blocker,
            "hasf_gates": (hasf.get("data") or {}).get("gates"),
        },
    }


def _role_cfo(src: Dict[str, Any]) -> Dict[str, Any]:
    glabel, glines, gdata = _goal_lines(src)
    parts = ["CFO lens. Money metrics are LIVE only when ledgers observe them."]
    labels: Dict[str, str] = {"role": "LIVE", "goal": glabel}

    # Spend from helm live if available
    spend = None
    spend_label = "UNKNOWN"
    try:
        import backend.helm_live_api as helm

        spend = helm.live_spend()
        if isinstance(spend, dict) and spend.get("state") == UNKNOWN:
            parts.append(f"Spend: UNKNOWN — {spend.get('reason')}.")
        else:
            parts.append(f"Spend observed: {str(spend)[:300]}")
            spend_label = "LIVE"
    except Exception as e:
        parts.append(f"Spend: UNKNOWN — {e}.")
        spend = None

    labels["spend"] = spend_label

    # North star money metric
    parts.append(" ".join([ln for ln in glines if "dollar" in ln.lower() or "north star" in ln.lower()][:3])
                or "Founder-minutes per shipped dollar: UNKNOWN.")
    hsf = observe_factory("HSF")
    hff = observe_factory("HFF")
    parts.append(
        f"HSF revenue path: stripe env {(hsf.get('labels') or {}).get('stripe', 'UNKNOWN')}; "
        f"revenue label {(hsf.get('labels') or {}).get('revenue', 'UNKNOWN')}."
    )
    parts.append(
        "Verified revenue dollars: UNKNOWN until a payment ledger shows a real dollar. "
        "Null is not zero-green. Voice will not move money or enable live Stripe."
    )
    labels["hsf_stripe"] = (hsf.get("labels") or {}).get("stripe") or "UNKNOWN"
    labels["revenue"] = "UNKNOWN"

    census = src.get("census")
    if isinstance(census, dict) and census.get("state") != UNKNOWN:
        parts.append(f"Factory census snippet: {str(census)[:200]}")
        labels["census"] = "LIVE"
    else:
        labels["census"] = "UNKNOWN"

    status = "PARTIAL" if spend_label == "UNKNOWN" else "LIVE"
    return {
        "status": status,
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": {
            "spend": spend if spend_label == "LIVE" else None,
            "north_star_completion": gdata.get("north_star_completion"),
            "hsf": hsf.get("data"),
            "hff_status": hff.get("status"),
            "verified_founder_minutes_per_shipped_dollar": None,
            "note": "null money metrics are UNKNOWN, not zero-green",
        },
    }


def _role_qa(src: Dict[str, Any]) -> Dict[str, Any]:
    flabel, flines = _factory_lines(src)
    glabel, glines, gdata = _goal_lines(src)
    rlabel, rlines, rdata = _repo_lines(src)
    parts = [
        "QA and Final Verifier lens. I do not grant release GO.",
        "Evidence gaps from observed blockers only:",
        " ".join(flines[:3]),
        f"Critical path blocker: {gdata.get('critical_path_blocker') or 'UNKNOWN'}.",
        rlines[0] if rlines else "Repo: UNKNOWN.",
        "Release authority remains blocked for voice. Unknown is not pass. Stale is not verified.",
    ]
    status = flabel if flabel != "UNKNOWN" else "UNKNOWN"
    if flabel == "STALE":
        status = "STALE"
    return {
        "status": status if status in ("LIVE", "STALE", "UNKNOWN", "PARTIAL") else "PARTIAL",
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": {
            "role": "LIVE",
            "factories": flabel,
            "goal": glabel,
            "repo": rlabel,
            "release_authority": "BLOCKED",
        },
        "data": {
            "critical_path_blocker": gdata.get("critical_path_blocker"),
            "repo": rdata,
            "release_authority": False,
        },
    }


_HANDLERS = {
    "founder": _role_founder,
    "ops": _role_ops,
    "ciso": _role_ciso,
    "cfo": _role_cfo,
    "qa": _role_qa,
}


def observe_role(role_id: str) -> Dict[str, Any]:
    rid = (role_id or "").strip().lower()
    meta = ROLE_CATALOG.get(rid)
    if not meta:
        return {
            "truth_class": "HELM_VOICE_ROLE",
            "status": "UNKNOWN",
            "role": rid or UNKNOWN,
            "observed_at": _now(),
            "speech_text": sanitize_for_speech(
                f"Leadership role '{role_id}' is not defined. "
                f"Known roles: {', '.join(ROLE_CATALOG)}. Status UNKNOWN."
            ),
            "labels": {"role": "UNKNOWN"},
            "data": {"known_roles": list(ROLE_CATALOG)},
        }

    src = _observe_sources()
    body = _HANDLERS[rid](src)
    return {
        "truth_class": "HELM_VOICE_ROLE",
        "role": rid,
        "title": meta["title"],
        "focus": meta["focus"],
        "doorstep": meta["doorstep"],
        "observed_at": _now(),
        "persona": f"HELM {meta['title']}",
        **body,
    }
