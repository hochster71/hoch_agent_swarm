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

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB = ROOT / "backend" / "swarm_ledger.db"
LEASES = ROOT / "coordination" / "leases"
PKGS = ROOT / "coordination" / "council" / "live_proof_packages"
ARTIFACTS = ROOT / "artifacts" / "factory"
UI = ROOT / "frontend_live" / "helm.html"

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


def live_tasks() -> Any:
    if not DB.exists():
        return _unknown("task DB missing")
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
        c.row_factory = sqlite3.Row
        rows = [dict(r) for r in c.execute(
            "SELECT t.task_id, t.status, t.name, t.updated_at, m.target_pod AS factory "
            "FROM mission_control_tasks t "
            "LEFT JOIN mission_control_missions m ON t.mission_id=m.mission_id "
            "ORDER BY t.updated_at DESC LIMIT 40")]
        c.close()
        return rows
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
        "verdict": live_verdict(),
    })


@app.get("/", response_class=HTMLResponse)
def ui() -> str:
    if UI.exists():
        return UI.read_text()
    return "<h1>HELM LIVE</h1><p>UI missing at frontend_live/helm.html</p>"
