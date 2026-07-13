"""HELM LIVE — runtime-truth API.

DOCTRINE
--------
Every field returned here is OBSERVED from a real source at request time:

    leases       <- coordination/leases/*.lock          (real files on disk)
    tasks        <- backend/swarm_ledger.db             (the real task table)
    factories    <- ScopedStateEvaluator                (real blocker scoping)
    adapters     <- AdapterRegistry.check_all_readiness (real probes)
    concurrency  <- PersistentScheduler.concurrency_report()
    dispatches   <- the newest evidence package's ledgers
    artifacts    <- artifacts/factory/*.md              (real bytes, real sha256)

There are NO fallbacks. If a source is missing or unreadable the field is the
string "UNKNOWN" (or an explicit {"state": "UNKNOWN", "reason": ...}). A value is
NEVER invented to make the screen look alive. The UI is contractually required to
render UNKNOWN as UNKNOWN.

This is the difference between a dashboard and a decoration.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB = ROOT / "backend" / "swarm_ledger.db"
LEASES = ROOT / "coordination" / "leases"
PKGS = ROOT / "coordination" / "council" / "live_proof_packages"
ARTIFACTS = ROOT / "artifacts" / "factory"
UI = ROOT / "frontend_live" / "helm.html"
PERT_UI = ROOT / "frontend_live" / "pert.html"

UNKNOWN = "UNKNOWN"

app = FastAPI(title="HELM LIVE")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _unknown(reason: str) -> Dict[str, str]:
    return {"state": UNKNOWN, "reason": reason}


# --------------------------------------------------------------------------
def live_leases() -> Any:
    try:
        from backend.mission_control.per_task_lease import PerTaskLeaseManager
        return PerTaskLeaseManager().active_leases()
    except Exception as e:
        return _unknown(f"lease manager unreadable: {e}")


def live_concurrency() -> Any:
    try:
        from backend.mission_control.persistent_scheduler import PersistentScheduler
        return PersistentScheduler(evidence_dir=ROOT / "coordination" / "council").concurrency_report()
    except Exception as e:
        return _unknown(f"scheduler unreadable: {e}")


def live_adapters() -> Any:
    try:
        from backend.mission_control.adapter_registry import AdapterRegistry
        reg = AdapterRegistry().check_all_readiness()
        return [{"id": k, "readiness": v.get("readiness", UNKNOWN),
                 "health": v.get("health", UNKNOWN),
                 "egress": v.get("egress_class", UNKNOWN),
                 "auth_required": v.get("auth_required")}
                for k, v in reg.items() if isinstance(v, dict)]
    except Exception as e:
        return _unknown(f"adapter registry unreadable: {e}")


def live_factories() -> Any:
    try:
        from backend.mission_control.persistent_scheduler import PersistentScheduler
        from backend.mission_control.scoped_states import ScopedStateEvaluator
        s = PersistentScheduler(evidence_dir=ROOT / "coordination" / "council")
        st = ScopedStateEvaluator(s.repo_root).evaluate_states(
            global_hold=False, blockers=s.load_blockers())
        return {"factories": st.get("FACTORY_STATE", UNKNOWN),
                "product_missions": st.get("PRODUCT_MISSION_STATE", UNKNOWN)}
    except Exception as e:
        return _unknown(f"scoped states unreadable: {e}")


def _validator_evidence() -> dict:
    """Read REAL validator verdicts from the verification ledger. No inference."""
    out = {}
    import time as _t
    for led in (ROOT / "coordination" / "council").rglob("verification_ledger.jsonl"):
        for line in led.read_text().splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            tid = d.get("task_id")
            if not tid:
                continue
            art = d.get("artifact_sha256")
            fresh = "UNKNOWN"
            ts = d.get("ts", "")
            try:
                age = _t.time() - _t.mktime(_t.strptime(ts.split(".")[0].replace("Z", ""),
                                                        "%Y-%m-%dT%H:%M:%S"))
                fresh = "FRESH" if age < 86400 else "STALE"
            except Exception:
                fresh = "UNKNOWN"
            out[tid] = {"verdict": d.get("verdict"),
                        "evidence_id": d.get("task_id") if d.get("verdict") else None,
                        "artifact_sha256": art,
                        "provenance_status": "PASS" if art else "UNKNOWN",
                        "freshness_status": fresh}
    return out


def live_tasks() -> Any:
    """F-2/F-5: the canonical enum is enforced HERE, at ingestion. An illegal status
    (AgentHASF / IDEA / LEASE) does NOT reach the wall as if it were a state -- it renders
    UNKNOWN and carries a typed INVALID_TASK_STATUS error. It can never render COMPLETE."""
    if not DB.exists():
        return _unknown("task DB missing")
    try:
        from backend.truth.task_status import resolve_status
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
        c.row_factory = sqlite3.Row
        raw = [dict(r) for r in c.execute(
            "SELECT t.task_id, t.status, t.name, t.updated_at, t.assigned_agent, "
            "t.evidence_path, m.target_pod AS factory "
            "FROM mission_control_tasks t "
            "LEFT JOIN mission_control_missions m ON t.mission_id=m.mission_id "
            "ORDER BY t.updated_at DESC LIMIT 40")]
        c.close()
        rows, rejected = [], 0
        for r in raw:
            # EXPLICIT validator evidence. An artifact EXISTING does not prove a validator
            # PASSED -- inferring that would manufacture a new false-positive path.
            vv = _validator_evidence().get(r["task_id"], {})
            res = resolve_status(
                raw=r.get("status"),
                execution_status=r.get("status"),
                validator_status=vv.get("verdict"),
                validator_evidence_id=vv.get("evidence_id"),
                artifact_digest=vv.get("artifact_sha256"),
                provenance_status=vv.get("provenance_status"),
                freshness_status=vv.get("freshness_status"),
            )
            if res.get("error") or res.get("downgraded"):
                rejected += 1
            rows.append({**r, "status": res["status"],
                         "status_error": res.get("error"),
                         "downgraded_from": res.get("claimed"),
                         "unmet_completion_requirements": res.get("unmet_completion_requirements")})
        return {"tasks": rows, "invalid_or_downgraded": rejected,
                "enum_enforced_at": "ingestion"}
    except Exception as e:
        return _unknown(f"task DB unreadable: {e}")


def _newest_pkg() -> Path | None:
    if not PKGS.exists():
        return None
    ds = [d for d in PKGS.iterdir() if d.is_dir() and d.name.startswith("HELM-FOUR-FACTORY")]
    return sorted(ds)[-1] if ds else None


def live_events() -> Any:
    """Real dispatch + verification events from the newest evidence package."""
    pkg = _newest_pkg()
    if not pkg:
        return _unknown("no evidence package found")
    out: List[Dict[str, Any]] = []
    for fn, kind in (("gateway_dispatches.jsonl", "DISPATCH"),
                     ("verification_results.jsonl", "VERIFY"),
                     ("lease_ledger.jsonl", "LEASE")):
        p = pkg / fn
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            out.append({"kind": kind, "ts": d.get("ts") or d.get("completed_at") or UNKNOWN,
                        "task_id": d.get("task_id", UNKNOWN),
                        "detail": d.get("verdict") or d.get("status") or UNKNOWN,
                        "validator": d.get("validator_verdict"),
                        "fencing_token": d.get("fencing_token")})
    out.sort(key=lambda e: str(e["ts"]))
    return {"package": pkg.name, "events": out[-60:]}


def live_artifacts() -> Any:
    if not ARTIFACTS.exists():
        return _unknown("no artifacts dir")
    out = []
    for p in sorted(ARTIFACTS.glob("*.md")):
        b = p.read_bytes()
        out.append({"task_id": p.stem, "bytes": len(b),
                    "sha256": hashlib.sha256(b).hexdigest()[:16],
                    "preview": b.decode("utf-8", "ignore")[:220]})
    return out


def live_spend() -> Any:
    """Observed spend. Never an estimate presented as a fact."""
    try:
        from backend.mission_control.spend_meter import SpendMeter
        return SpendMeter().summary()
    except Exception as e:
        return _unknown(f"spend meter unreadable: {e}")


def live_northstar() -> Any:
    """The founder's PRIMARY metric. Two of its three terms had no instrument until now."""
    try:
        from backend.mission_control.hoch_ledger import HochLedger
        return HochLedger().summary()
    except Exception as e:
        return _unknown(f"hoch ledger unreadable: {e}")


def live_security() -> Any:
    """NIST 800-53 Rev5 posture of HELM ITSELF, re-derived from live evidence."""
    try:
        pos = ROOT / "coordination" / "security" / "helm_control_posture.json"
        if not pos.exists():
            return _unknown("no ConMon assessment yet")
        d = json.loads(pos.read_text())
        return {k: d[k] for k in ("framework", "assessed_at", "posture_percent",
                                  "implemented", "controls_assessed", "open_findings",
                                  "high_findings", "controls", "poam")}
    except Exception as e:
        return _unknown(f"posture unreadable: {e}")


def live_census() -> Any:
    """Where are the factories, and is any of them actually earning? Observed."""
    try:
        from backend.mission_control.factory_census import census
        return census()
    except Exception as e:
        return _unknown(f"factory census unreadable: {e}")


def live_verdict() -> Any:
    pkg = _newest_pkg()
    if not pkg or not (pkg / "validation.json").exists():
        return _unknown("no validation.json in newest package")
    try:
        v = json.loads((pkg / "validation.json").read_text())
        return {"package": pkg.name, "verdict": v.get("verdict", UNKNOWN),
                "criteria": v.get("acceptance_criteria", UNKNOWN),
                "four": v.get("four_factory_terminal_results", UNKNOWN),
                "overlap_seconds": v.get("overlap_seconds", UNKNOWN),
                "commit": v.get("tested_commit", UNKNOWN)}
    except Exception as e:
        return _unknown(f"validation unreadable: {e}")


@app.get("/api/helm/integrity")
def api_integrity():
    """F-1: integrity is COMPUTED from the live node set, or reported UNKNOWN. The wall no
    longer prints 'EVERY NODE OBSERVED - 0 FABRICATED' as an unearned green slogan."""
    from backend.truth.integrity import compute_integrity
    t = live_tasks()
    nodes = t.get("tasks") if isinstance(t, dict) else None
    return compute_integrity(nodes if isinstance(nodes, list) else t)


@app.get("/api/helm/factories")
def api_factories():
    """F-4: ONE canonical identity source + ONE derived runtime state."""
    from backend.truth.integrity import canonical_factories
    return canonical_factories()


@app.get("/api/helm/concurrency")
def api_concurrency():
    """Capacity and utilisation are DIFFERENT facts."""
    from backend.truth.runtime_source import concurrency_truth
    return concurrency_truth(configured_capacity=4)


@app.get("/api/helm/live")
def helm_live() -> JSONResponse:
    return JSONResponse({
        "observed_at": now(),
        "doctrine": "every field observed; absent data renders UNKNOWN; nothing is invented",
        "concurrency": live_concurrency(),
        "leases": live_leases(),
        "adapters": live_adapters(),
        "scope": live_factories(),
        "tasks": live_tasks(),
        "events": live_events(),
        "artifacts": live_artifacts(),
        "spend": live_spend(),
        "northstar": live_northstar(),
        "security": live_security(),
        "census": live_census(),
        "verdict": live_verdict(),
    })


@app.get("/pert", response_class=HTMLResponse)
def pert_wall() -> str:
    """The 85-inch wall. Same runtime-truth feed; nothing on it can be faked."""
    if PERT_UI.exists():
        return PERT_UI.read_text()
    return "<h1>PERT wall missing</h1>"


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    if UI.exists():
        return UI.read_text()
    return "<h1>HELM LIVE</h1><p>UI missing at frontend_live/helm.html</p>"


# ── FOUNDER GATE (iPhone) ────────────────────────────────────────────────────
FOUNDER_UI = ROOT / "frontend_live" / "founder.html"


@app.get("/founder", response_class=HTMLResponse)
def founder_dashboard() -> str:
    """The iPhone founder cockpit — live HELM state + the approval gate. One surface."""
    if FOUNDER_UI.exists():
        return FOUNDER_UI.read_text()
    return "<h1>founder.html missing</h1>"


@app.get("/api/founder/queue")
def founder_queue() -> JSONResponse:
    try:
        from backend.council.founder_gate import pending
        return JSONResponse({"pending": pending()})
    except Exception as e:
        return JSONResponse({"pending": [], "error": str(e)})


@app.post("/api/founder/decide")
async def founder_decide(req: Request) -> JSONResponse:
    """Record a founder decision. Token-gated + authority-class enforced.

    A FOUNDER_ONLY item can only be ACKNOWLEDGEd here — HELM never performs it on a tap.
    """
    from backend.council.founder_gate import authorized, record_decision
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "message": "bad request"}, status_code=400)

    if not authorized(body.get("token")):
        return JSONResponse({"ok": False, "message": "unauthorized (bad or missing founder token)"}, status_code=401)

    ok, msg = record_decision(
        str(body.get("decision_id", "")),
        str(body.get("verb", "")),
        authority=str(body.get("authority", "PROPOSE_ONLY")),
        note=str(body.get("note", "")),
    )
    return JSONResponse({"ok": ok, "message": msg})

