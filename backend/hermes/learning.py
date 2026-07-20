"""HERMES Learning Engine — INTERFACE + LOGGING HOOKS ONLY (by founder scope).

Scope decision (2026-07-18): the Learning Engine is deliberately NOT implemented as a
routing influencer yet. This module defines the contract and records the evidence, so
routing can later be learned from real history instead of guesses. Until an EDR
authorizes it, `recommend_worker()` returns NO_RECOMMENDATION — HERMES routing stays
deterministic (manifest + observed availability), which is auditable.

WHY NO NEW STORE: mission records append to the EXISTING HELM event ledger
(backend/dispatch/council_router._record → event bus). No second bus, no second DB.
If the ledger is unavailable, we fail closed to a local JSONL under coordination/hermes/
and say so — we never drop evidence silently.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

ROOT = Path(__file__).resolve().parents[2]
FALLBACK_LOG = ROOT / "coordination" / "hermes" / "mission_log.jsonl"


class LearningEngine(Protocol):
    """The contract a future learning engine must satisfy."""

    def record(self, mission: Dict[str, Any]) -> None: ...
    def recommend_worker(self, capability: str) -> Dict[str, Any]: ...
    def worker_stats(self, worker: str) -> Dict[str, Any]: ...


def record_mission(*, capability: str, worker: Optional[str], ok: bool,
                   latency_ms: int, selection_reason: Optional[str] = None,
                   fallback_used: bool = False, verification: Optional[str] = None,
                   cost_usd: Optional[float] = None, quality: Optional[float] = None,
                   error: Optional[str] = None) -> Dict[str, Any]:
    """Mission analytics hook — called by the dispatcher on every dispatch.

    Records: worker · mission(capability) · latency · cost · quality · verification ·
    success/failure · selection reason · fallback used.
    """
    rec = {
        "schema": "HERMES_MISSION_RECORD_v1",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capability": capability, "worker": worker, "ok": bool(ok),
        "latency_ms": latency_ms, "cost_usd": cost_usd, "quality": quality,
        "verification": verification, "selection_reason": selection_reason,
        "fallback_used": bool(fallback_used), "error": error,
    }
    # Primary: the EXISTING HELM ledger (no new bus).
    try:
        from backend.dispatch.council_router import _record
        _record("HERMES_MISSION", rec)
        rec["sink"] = "helm_event_ledger"
        return rec
    except Exception as e:
        rec["sink"] = "fallback_jsonl"
        rec["ledger_error"] = f"{type(e).__name__}: {e}"
    try:
        FALLBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with FALLBACK_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        rec["sink"] = "DROPPED"
        rec["write_error"] = f"{type(e).__name__}: {e}"
    return rec


def read_missions(limit: int = 200) -> List[Dict[str, Any]]:
    """Read back recorded missions from the fallback log (ledger reads live in HELM)."""
    if not FALLBACK_LOG.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in FALLBACK_LOG.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def recommend_worker(capability: str) -> Dict[str, Any]:
    """INTERFACE ONLY — deliberately not implemented (see module docstring)."""
    return {
        "capability": capability,
        "recommendation": "NO_RECOMMENDATION",
        "status": "INTERFACE_ONLY",
        "reason": "Learning Engine is a defined interface with logging hooks by founder "
                  "scope. Enabling learned routing is an architectural change and "
                  "requires an EDR. Routing remains deterministic and auditable.",
    }


def worker_stats(worker: Optional[str] = None) -> Dict[str, Any]:
    """Honest aggregate over recorded missions. Evidence, not inference."""
    rows = read_missions(limit=1000)
    if worker:
        rows = [r for r in rows if r.get("worker") == worker]
    if not rows:
        return {"worker": worker, "missions": 0, "status": "NO_EVIDENCE_YET",
                "note": "no missions recorded in the fallback log; ledger holds the rest"}
    ok = [r for r in rows if r.get("ok")]
    lat = [r.get("latency_ms") or 0 for r in rows]
    return {
        "worker": worker, "missions": len(rows),
        "success_rate": round(len(ok) / len(rows), 3),
        "avg_latency_ms": int(sum(lat) / len(lat)) if lat else None,
        "fallbacks": sum(1 for r in rows if r.get("fallback_used")),
        "status": "OBSERVED",
    }
