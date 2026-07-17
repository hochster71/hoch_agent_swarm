"""HELM Executive Brief — the single integration surface over ALL HELM projections.

Composes every existing runtime-truth projection (mission, runtime engines, HMAI,
external milestones, workers/AI, cybersecurity/ConMon, factories) into one honest
Executive Brief payload. This is INTEGRATION of the Executive Projections layer that
already exists in the ratified Constitution — it adds no architecture and touches no
frozen verification-target file (the helm_runtime bridge).

NO FAKE GREEN, fail-closed per section: if a source errors or is absent, that section
renders UNKNOWN / NOT_CONNECTED with the reason — never synthesized.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict


def _safe(fn, label: str) -> Dict[str, Any]:
    try:
        return {"ok": True, "data": fn()}
    except Exception as e:  # fail-closed
        return {"ok": False, "status": "UNKNOWN", "error": f"{type(e).__name__}: {e}", "section": label}


def build_executive_brief() -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "schema": "HELM_EXECUTIVE_BRIEF_v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "doctrine": "integration over existing projections; no fake green; unconnected domains render honestly",
        "sections": {},
    }
    S = out["sections"]

    # --- MISSION + runtime engines ---------------------------------------
    def _mission():
        from backend.helm_runtime.mission_store import read_mission
        from backend.helm_runtime.dispatch_gateway import default_gateway
        doc = read_mission()
        mh = default_gateway().mission_health()
        return {
            "mission_id": (doc.get("mission") or {}).get("id"),
            "mission_name": (doc.get("mission") or {}).get("name"),
            "state": doc.get("state") or doc.get("operational_status"),
            "mission_version": doc.get("mission_version"),
            "constitutional_baseline": "RATIFIED",
            "implementation_verification": "PENDING",
            "runtime": mh.get("runtime"),
            "founder_gate": mh.get("founder_gate"),
            "critical_path": doc.get("critical_path"),
        }
    S["mission"] = _safe(_mission, "mission")

    # --- HMAI (mission assurance index) ----------------------------------
    def _hmai():
        from backend.truth.hmai import compute_hmai
        h = compute_hmai()
        return {
            "index": h.get("index"), "band": h.get("band"),
            "coverage_pct": h.get("coverage_pct"),
            "can_mission_safely_proceed": h.get("can_mission_safely_proceed"),
            "recommended_next_action": h.get("recommended_next_action"),
            "founder_only_actions_pending": h.get("founder_only_actions_pending"),
            "unknown_pillars": h.get("unknown_pillars"),
        }
    S["assurance_hmai"] = _safe(_hmai, "assurance_hmai")

    # --- EXTERNAL milestones (release + revenue) -------------------------
    def _external():
        from backend.truth.external_milestones import compute_external_milestones
        e = compute_external_milestones()
        ms = e.get("milestones") or {}
        return {
            "truth_class": e.get("truth_class"),
            "freshness_seconds": e.get("freshness_seconds"),
            "release": (ms.get("RELEASE") or {}).get("current_state"),
            "revenue": (ms.get("REVENUE") or {}).get("current_state"),
        }
    S["external_milestones"] = _safe(_external, "external_milestones")

    # --- AI / WORKERS (frontier + local, by role not brand) --------------
    def _ai():
        from backend.helm_runtime.dispatch_gateway import default_gateway
        gw = default_gateway()
        ws = gw.worker_status()
        return {
            "configured": ws.get("configured"),
            "available": ws.get("available"),
            "blocked": ws.get("blocked"),
            "total": ws.get("total"),
            "workers": gw.worker_role_health(),
            "dispatch": "READY (skeleton; live dispatch founder-gated)",
        }
    S["ai_workers"] = _safe(_ai, "ai_workers")

    # --- CYBERSECURITY / ConMon (NIST 800-53 Rev5 + 800-137) -------------
    def _cyber():
        from backend.security.helm_conmon import assess
        c = assess()
        return {
            "framework": c.get("framework"),
            "conmon_standard": c.get("conmon_standard"),
            "posture_percent": c.get("posture_percent"),
            "posture_scope": c.get("posture_percent_scope"),
            "controls_assessed": c.get("controls_assessed"),
            "implemented": c.get("implemented"),
            "not_implemented": c.get("not_implemented"),
            "unknown": c.get("unknown"),
            "open_findings": c.get("open_findings"),
            "high_findings": c.get("high_findings"),
        }
    S["cybersecurity"] = _safe(_cyber, "cybersecurity")

    # --- FACTORIES (plugins over the runtime) ----------------------------
    def _factories():
        from backend.truth.integrity import canonical_factories
        f = canonical_factories()
        # canonical_factories returns the registry dict; surface the factory list honestly
        fl = f.get("factories") if isinstance(f, dict) else f
        rows = []
        if isinstance(fl, list):
            for x in fl:
                if isinstance(x, dict):
                    rows.append({"id": x.get("id") or x.get("code") or x.get("name"),
                                 "status": x.get("status") or x.get("readiness") or "UNKNOWN"})
        elif isinstance(fl, dict):
            for k, v in fl.items():
                rows.append({"id": k, "status": (v.get("status") if isinstance(v, dict) else v) or "UNKNOWN"})
        return {"count": len(rows), "factories": rows}
    S["factories"] = _safe(_factories, "factories")

    # --- LIFESTYLE domains — honest NOT_CONNECTED (vision, no connectors) -
    S["lifestyle"] = {"ok": True, "data": {
        "family": "NOT_CONNECTED",
        "home": "NOT_CONNECTED",
        "finance": "NOT_CONNECTED",
        "health": "NOT_CONNECTED",
        "note": "HOCH Family OS domains are PLANNED (vision); each enters via its own EDR + connector.",
    }}

    # --- FOUNDER DECISIONS (derived from mission gates + HMAI) ------------
    def _founder():
        pend = []
        m = S.get("mission", {}).get("data", {})
        for item in (m.get("critical_path") or []):
            if isinstance(item, dict):
                st = str(item.get("status", "")).upper()
                owner = str(item.get("owner_role", "")).lower()
                if "FOUNDER" in st or owner.startswith("founder"):
                    pend.append({"id": item.get("id"), "label": item.get("label"), "status": item.get("status")})
        h = S.get("assurance_hmai", {}).get("data", {})
        return {"pending_count": len(pend), "items": pend,
                "founder_only_actions_pending": h.get("founder_only_actions_pending")}
    S["founder_decisions"] = _safe(_founder, "founder_decisions")

    # --- RECOMMENDED NEXT ACTION (prefer HMAI's, else the critical path) --
    rec = None
    h = S.get("assurance_hmai", {})
    if h.get("ok"):
        rec = (h.get("data") or {}).get("recommended_next_action")
    # Normalize to a readable string (HMAI may return a dict/list).
    if isinstance(rec, dict):
        rec = rec.get("statement") or rec.get("action") or rec.get("label") or rec.get("text") or rec.get("next") or str(rec)
    elif isinstance(rec, (list, tuple)):
        first = rec[0] if rec else None
        rec = (first.get("action") or first.get("label") or str(first)) if isinstance(first, dict) else (str(first) if first else None)
    out["recommended_next_action"] = rec or "Launch the independent implementation verification (Auditor → conformance verdict)."

    # top-line honesty banner
    out["headline"] = "HELM Core 1.0.0-alpha — Constitutional Baseline Ratified. Independent implementation verification pending."
    return out
