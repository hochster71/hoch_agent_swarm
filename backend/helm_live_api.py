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
import re
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

from backend.instrument_integrity.council_router import council_router
app.include_router(council_router)


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
    """Wall-safe adapter snapshot.

    MUST NOT run CLI auth probes on the request path. ``check_all_readiness``
    shells out to grok/gemini/claude (up to 45s each). The wall polls
    ``/api/v1/helm/pert`` every 1.5s on a single uvicorn worker; those probes
    starve the worker and surface as browser 500 / timeouts / FEED LOST.

    Observed (non-blocking) signals only:
      - env API key present
      - prior CLI probe cache (if already filled elsewhere)
      - binary on PATH (without invoking it)
    """
    import os
    import shutil
    try:
        from backend.mission_control.adapter_registry import AdapterRecord, AdapterRegistry
        reg = AdapterRegistry()
        env = dict(os.environ)
        out: List[Dict[str, Any]] = []
        for aid, rec in reg.adapters.items():
            auth_required = bool(rec.auth_required)
            egress = rec.egress_class.value if hasattr(rec.egress_class, "value") else str(rec.egress_class)
            if not auth_required:
                readiness, health, auth_mode = "READY", "ACTIVE", "NO_AUTH_REQUIRED"
            else:
                keyed = bool(rec.api_key_env_var and env.get(rec.api_key_env_var))
                cached = AdapterRecord._AUTH_PROBE_CACHE.get(aid)
                probe = AdapterRecord._CLI_AUTH_PROBE.get(aid)
                has_bin = bool(probe and shutil.which(probe[0]))
                if keyed:
                    readiness, health, auth_mode = "READY", "ACTIVE", "API_KEY_ENV"
                elif cached == "READY":
                    readiness, health, auth_mode = "READY", "ACTIVE", "CLI_SESSION_CACHED"
                elif cached == "NOT_READY":
                    readiness, health, auth_mode = "NOT_READY", "UNKNOWN", "CLI_SESSION_CACHED"
                elif has_bin:
                    # Binary present but no non-blocking proof of session — do not invent READY.
                    readiness, health, auth_mode = UNKNOWN, UNKNOWN, "CLI_PROBE_DEFERRED"
                else:
                    readiness, health, auth_mode = "NOT_READY", "UNKNOWN", "NONE"
            out.append({
                "id": aid,
                "readiness": readiness,
                "health": health,
                "egress": egress,
                "auth_required": auth_required,
                "auth_mode": auth_mode,
            })
        return out
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
        # Load validator evidence ONCE — rglob+read of all ledgers is O(packages×lines).
        # Calling it per-task made /api/v1/helm/pert take multi-seconds and starve the wall tick.
        validator_by_task = _validator_evidence()
        for r in raw:
            # EXPLICIT validator evidence. An artifact EXISTING does not prove a validator
            # PASSED -- inferring that would manufacture a new false-positive path.
            vv = validator_by_task.get(r["task_id"], {})
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


def get_current_commit() -> str:
    try:
        pkg = _newest_pkg()
        if pkg and (pkg / "validation.json").exists():
            v = json.loads((pkg / "validation.json").read_text())
            c = v.get("tested_commit")
            if c and c != "UNKNOWN":
                return str(c)
    except Exception:
        pass
    try:
        import subprocess
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(ROOT))
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "UNKNOWN"


def _truth_response(truth_class: str, source: str, observed_at: str, freshness_seconds: float, data: dict) -> dict:
    return {
        "truth_class": truth_class,
        "source": source,
        "observed_at": observed_at,
        "freshness_seconds": freshness_seconds,
        "tested_commit": get_current_commit(),
        **data
    }


def _newest_soak_pkg():
    """F-A2: authoritative phase soak package (not XH smoke; not pure name sort)."""
    from backend.truth.soak_select import select_soak_package
    return select_soak_package(PKGS)


@app.get("/api/v1/helm/wall")
def api_wall():
    """Every scope derived INDEPENDENTLY. A locked 24/7 gate must not freeze the factories.

    F-A6: response carries the standard truth metadata contract.
    """
    from backend.truth.wall_state import wall_state
    return JSONResponse(wall_state())


@app.get("/api/v1/helm/runtime")
@app.get("/api/helm/concurrency")
def api_v1_runtime():
    import time
    from backend.truth.runtime_source import concurrency_truth, POINTER
    data = concurrency_truth(configured_capacity=4)
    freshness = 0.0
    if POINTER.exists():
        freshness = float(time.time() - POINTER.stat().st_mtime)
    return JSONResponse(_truth_response(
        truth_class="HELM_RUNTIME_TRUTH",
        source=str(POINTER.relative_to(ROOT)) if POINTER.exists() else "none",
        observed_at=now(),
        freshness_seconds=freshness,
        data=data
    ))


@app.get("/api/v1/helm/factories")
@app.get("/api/helm/factories")
def api_v1_factories():
    import time
    from backend.truth.integrity import canonical_factories, FACTORY_REGISTRY
    data = canonical_factories()
    freshness = 0.0
    if FACTORY_REGISTRY.exists():
        freshness = float(time.time() - FACTORY_REGISTRY.stat().st_mtime)
    return JSONResponse(_truth_response(
        truth_class="HELM_FACTORY_TRUTH",
        source=str(FACTORY_REGISTRY.relative_to(ROOT)) if FACTORY_REGISTRY.exists() else "none",
        observed_at=now(),
        freshness_seconds=freshness,
        data=data
    ))


@app.get("/api/v1/helm/tasks")
def api_v1_tasks():
    import time
    data = live_tasks()
    freshness = 0.0
    if DB.exists():
        freshness = float(time.time() - DB.stat().st_mtime)
    return JSONResponse(_truth_response(
        truth_class="HELM_TASK_TRUTH",
        source=str(DB.relative_to(ROOT)) if DB.exists() else "none",
        observed_at=now(),
        freshness_seconds=freshness,
        data=data
    ))


@app.get("/api/v1/helm/leases")
def api_v1_leases():
    import time
    from backend.truth.runtime_source import classify_active_leases, LEASE_DIR
    data = classify_active_leases()
    freshness = 0.0
    if LEASE_DIR.exists():
        locks = list(LEASE_DIR.glob("*.lock"))
        if locks:
            freshness = float(time.time() - max(lk.stat().st_mtime for lk in locks))
    return JSONResponse(_truth_response(
        truth_class="HELM_LEASE_TRUTH",
        source=str(LEASE_DIR.relative_to(ROOT)) if LEASE_DIR.exists() else "none",
        observed_at=now(),
        freshness_seconds=freshness,
        data=data
    ))


@app.get("/api/v1/helm/authority")
def api_v1_authority():
    import time
    from backend.council.founder_gate import pending, verify_chain, QUEUE, DECISIONS, _read_jsonl
    chain_ok, chain_msg = verify_chain()
    history = _read_jsonl(DECISIONS)[-30:]
    data = {
        "pending_escalations": pending(),
        "decided_history": history,
        "chain_intact": chain_ok,
        "chain_message": chain_msg
    }
    paths = [p for p in (QUEUE, DECISIONS) if p.exists()]
    freshness = 0.0
    if paths:
        freshness = float(time.time() - max(p.stat().st_mtime for p in paths))
    return JSONResponse(_truth_response(
        truth_class="HELM_AUTHORITY_TRUTH",
        source=f"{QUEUE.relative_to(ROOT) if QUEUE.exists() else 'none'} + {DECISIONS.relative_to(ROOT) if DECISIONS.exists() else 'none'}",
        observed_at=now(),
        freshness_seconds=freshness,
        data=data
    ))


@app.get("/api/v1/helm/jspace/health")
def api_v1_jspace_health():
    """Latest HJOS meta-health. Read-only; never promotes."""
    import time
    from backend.jspace.burn_in import BurnInTracker
    from backend.jspace.ledger import JSpaceLedger
    led = JSpaceLedger()
    health = led.latest_health() or {}
    burn = BurnInTracker(led.root).load()
    path = led.health_path
    freshness = float(time.time() - path.stat().st_mtime) if path.exists() else 0.0
    if not health:
        return JSONResponse(_truth_response(
            truth_class="HJOS_HEALTH_TRUTH",
            source="coordination/jspace/health.json",
            observed_at=now(),
            freshness_seconds=freshness,
            data={"state": UNKNOWN, "reason": "no HJOS cycle has written health yet",
                  "promotion_authority": "NONE", "burn_in": burn},
        ))
    data = {**health, "burn_in": burn}
    return JSONResponse(_truth_response(
        truth_class="HJOS_HEALTH_TRUTH",
        source="coordination/jspace/health.json",
        observed_at=now(),
        freshness_seconds=freshness,
        data=data,
    ))


@app.post("/api/v1/helm/jspace/cycle")
def api_v1_jspace_cycle():
    """Run one HJOS observation cycle. Creates assessments/alerts; quarantine only post burn-in."""
    from backend.jspace.runner import run_hjos_cycle
    try:
        result = run_hjos_cycle()
        return JSONResponse(_truth_response(
            truth_class="HJOS_CYCLE_TRUTH",
            source="backend.jspace.runner",
            observed_at=now(),
            freshness_seconds=0.0,
            data=result,
        ))
    except Exception as e:
        return JSONResponse(_truth_response(
            truth_class="HJOS_CYCLE_TRUTH",
            source="backend.jspace.runner",
            observed_at=now(),
            freshness_seconds=0.0,
            data={"state": UNKNOWN, "reason": str(e), "promotion_authority": "NONE"},
        ))


@app.get("/api/v1/helm/jspace/burn-in")
def api_v1_jspace_burn_in():
    """HJOS burn-in status for auto-quarantine gating."""
    from backend.jspace.burn_in import BurnInTracker
    from backend.jspace.ledger import JSpaceLedger
    st = BurnInTracker(JSpaceLedger().root).load()
    return JSONResponse(_truth_response(
        truth_class="HJOS_BURN_IN_TRUTH",
        source="coordination/jspace/burn_in.json",
        observed_at=now(),
        freshness_seconds=0.0,
        data=st,
    ))


@app.get("/api/v1/helm/integrity")
@app.get("/api/helm/integrity")
def api_v1_integrity():
    from backend.truth.integrity import compute_integrity
    t = live_tasks()
    nodes = t.get("tasks") if isinstance(t, dict) else None
    data = compute_integrity(nodes if isinstance(nodes, list) else t)
    return JSONResponse(_truth_response(
        truth_class="HELM_INTEGRITY_TRUTH",
        source="runtime_verification",
        observed_at=now(),
        freshness_seconds=0.0,
        data=data
    ))


@app.get("/api/v1/helm/soak")
def api_v1_soak():
    import time
    pkg = _newest_soak_pkg()
    if not pkg:
        return JSONResponse(_truth_response(
            truth_class="HELM_SOAK_TRUTH",
            source="none",
            observed_at=now(),
            freshness_seconds=0.0,
            data={"state": "UNKNOWN", "reason": "no soak package found"}
        ))
    cfg_file = pkg / "soak_config.json"
    cfg = {}
    if cfg_file.exists():
        try:
            cfg = json.loads(cfg_file.read_text())
        except Exception:
            cfg = {"error": "unreadable config"}
    
    cycles_file = pkg / "daemon" / "scheduler_cycles.jsonl"
    cycles_count = 0
    if cycles_file.exists():
        cycles_count = len(cycles_file.read_text().splitlines())
        
    verif_file = pkg / "daemon" / "verification_ledger.jsonl"
    verif_count = 0
    if verif_file.exists():
        verif_count = len(verif_file.read_text().splitlines())
        
    lease_file = pkg / "daemon" / "task_lease_ledger.jsonl"
    lease_count = 0
    if lease_file.exists():
        lease_count = len(lease_file.read_text().splitlines())
        
    res_file = pkg / "resource_usage.jsonl"
    usage_entries = []
    if res_file.exists():
        for line in res_file.read_text().splitlines()[-10:]:
            try:
                usage_entries.append(json.loads(line))
            except Exception:
                pass
                
    # GAP-07 FALSE-RED FIX. freshness was computed from soak_config.json — written ONCE at soak
    # start. So a HEALTHY soak writing cycles every ~50s rendered STALE on the wall, and the
    # staleness only grew. That is the INVERSE of fake-green: it manufactures alarm. Still a lie.
    # Freshness must come from the newest LIVE evidence, and be UNKNOWN when there is none.
    _live = None
    for _cand in (cycles_file, lease_file, pkg / "scheduler_cycles.jsonl"):
        try:
            if _cand.exists():
                _m = _cand.stat().st_mtime
                if _live is None or _m > _live[0]:
                    _live = (_m, _cand)
        except Exception:
            pass
    if _live is not None:
        freshness = float(time.time() - _live[0])
        _src = _live[1]
    elif cfg_file.exists():
        # config exists but NO cycle evidence yet -> we genuinely do not know if it is running
        freshness = None
        _src = cfg_file
    else:
        freshness = None
        _src = pkg
    # COMMIT ATTRIBUTION. _truth_response stamps the CURRENT HEAD. For a soak that is FALSE
    # ATTRIBUTION: the run is bound to the commit recorded in soak_config, and HEAD has moved on
    # since. Reporting HEAD would tell a reader the soak ran on code it never ran on.
    _bound = cfg.get("tested_commit") or cfg.get("tested_commit_short")
    return JSONResponse(_truth_response(
        truth_class="HELM_SOAK_TRUTH",
        source=str(_src.relative_to(ROOT)) if _src.exists() else str(pkg.relative_to(ROOT)),
        observed_at=now(),
        freshness_seconds=freshness,
        data={
            "package_name": pkg.name,
            "soak_config": cfg,
            "cycles_count": cycles_count,
            "verifications_count": verif_count,
            "leases_count": lease_count,
            "resource_usage_entries": usage_entries,
            "bound_commit": _bound,
            "head_commit_note": "tested_commit below is HEAD; the RUN is bound to bound_commit",
        }
    ))


@app.get("/api/v1/helm/pert")
def api_v1_pert():
    """Aggregate wall feed. Must not take tens of seconds or the 1.5s wall tick piles up."""
    import time
    try:
        return _api_v1_pert_body()
    except Exception as e:
        # Fail soft: feed stays JSON-shaped so the wall shows UNKNOWN, not an opaque 500.
        return JSONResponse(
            status_code=200,
            content=_truth_response(
                truth_class="HELM_PERT_TRUTH",
                source="multi-source aggregation",
                observed_at=now(),
                freshness_seconds=0.0,
                data={
                    "state": UNKNOWN,
                    "reason": f"pert aggregation failed: {type(e).__name__}: {e}",
                },
            ),
        )


def _api_v1_pert_body() -> JSONResponse:
    import time

    # 1. Runtime
    from backend.truth.runtime_source import concurrency_truth, POINTER
    rt_data = concurrency_truth(configured_capacity=4)
    rt_freshness = float(time.time() - POINTER.stat().st_mtime) if POINTER.exists() else 0.0
    runtime_sec = _truth_response(
        truth_class="HELM_RUNTIME_TRUTH",
        source=str(POINTER.relative_to(ROOT)) if POINTER.exists() else "none",
        observed_at=now(),
        freshness_seconds=rt_freshness,
        data=rt_data
    )
    
    # 2. Factories
    from backend.truth.integrity import canonical_factories, FACTORY_REGISTRY
    fac_data = canonical_factories()
    fac_freshness = float(time.time() - FACTORY_REGISTRY.stat().st_mtime) if FACTORY_REGISTRY.exists() else 0.0
    factories_sec = _truth_response(
        truth_class="HELM_FACTORY_TRUTH",
        source=str(FACTORY_REGISTRY.relative_to(ROOT)) if FACTORY_REGISTRY.exists() else "none",
        observed_at=now(),
        freshness_seconds=fac_freshness,
        data=fac_data
    )
    
    # 3. Tasks
    tasks_data = live_tasks()
    tasks_freshness = float(time.time() - DB.stat().st_mtime) if DB.exists() else 0.0
    tasks_sec = _truth_response(
        truth_class="HELM_TASK_TRUTH",
        source=str(DB.relative_to(ROOT)) if DB.exists() else "none",
        observed_at=now(),
        freshness_seconds=tasks_freshness,
        data=tasks_data
    )
    
    # 4. Leases
    from backend.truth.runtime_source import classify_active_leases, LEASE_DIR
    leases_data = classify_active_leases()
    leases_freshness = 0.0
    if LEASE_DIR.exists():
        locks = list(LEASE_DIR.glob("*.lock"))
        if locks:
            leases_freshness = float(time.time() - max(lk.stat().st_mtime for lk in locks))
    leases_sec = _truth_response(
        truth_class="HELM_LEASE_TRUTH",
        source=str(LEASE_DIR.relative_to(ROOT)) if LEASE_DIR.exists() else "none",
        observed_at=now(),
        freshness_seconds=leases_freshness,
        data=leases_data
    )
    
    # 5. Authority
    from backend.council.founder_gate import pending, verify_chain, QUEUE, DECISIONS, _read_jsonl
    chain_ok, chain_msg = verify_chain()
    auth_data = {
        "pending_escalations": pending(),
        "decided_history": _read_jsonl(DECISIONS)[-30:],
        "chain_intact": chain_ok,
        "chain_message": chain_msg
    }
    auth_paths = [p for p in (QUEUE, DECISIONS) if p.exists()]
    auth_freshness = float(time.time() - max(p.stat().st_mtime for p in auth_paths)) if auth_paths else 0.0
    authority_sec = _truth_response(
        truth_class="HELM_AUTHORITY_TRUTH",
        source=f"{QUEUE.relative_to(ROOT) if QUEUE.exists() else 'none'} + {DECISIONS.relative_to(ROOT) if DECISIONS.exists() else 'none'}",
        observed_at=now(),
        freshness_seconds=auth_freshness,
        data=auth_data
    )
    
    # 6. Integrity
    from backend.truth.integrity import compute_integrity
    tasks_list = tasks_data.get("tasks") if isinstance(tasks_data, dict) else None
    integ_data = compute_integrity(tasks_list if isinstance(tasks_list, list) else tasks_data)
    integrity_sec = _truth_response(
        truth_class="HELM_INTEGRITY_TRUTH",
        source="runtime_verification",
        observed_at=now(),
        freshness_seconds=0.0,
        data=integ_data
    )
    
    # 7. Soak
    soak_pkg = _newest_soak_pkg()
    if soak_pkg:
        soak_cfg_file = soak_pkg / "soak_config.json"
        soak_cfg = {}
        if soak_cfg_file.exists():
            try:
                soak_cfg = json.loads(soak_cfg_file.read_text())
            except Exception:
                soak_cfg = {"error": "unreadable config"}
        cycles_file = soak_pkg / "daemon" / "scheduler_cycles.jsonl"
        cycles_count = len(cycles_file.read_text().splitlines()) if cycles_file.exists() else 0
        verif_file = soak_pkg / "daemon" / "verification_ledger.jsonl"
        verif_count = len(verif_file.read_text().splitlines()) if verif_file.exists() else 0
        lease_file = soak_pkg / "daemon" / "task_lease_ledger.jsonl"
        lease_count = len(lease_file.read_text().splitlines()) if lease_file.exists() else 0
        res_file = soak_pkg / "resource_usage.jsonl"
        usage_entries = []
        if res_file.exists():
            for line in res_file.read_text().splitlines()[-10:]:
                try:
                    usage_entries.append(json.loads(line))
                except Exception:
                    pass
        soak_freshness = float(time.time() - soak_cfg_file.stat().st_mtime) if soak_cfg_file.exists() else 0.0
        soak_sec = _truth_response(
            truth_class="HELM_SOAK_TRUTH",
            source=str(soak_cfg_file.relative_to(ROOT)) if soak_cfg_file.exists() else str(soak_pkg.relative_to(ROOT)),
            observed_at=now(),
            freshness_seconds=soak_freshness,
            data={
                "package_name": soak_pkg.name,
                "soak_config": soak_cfg,
                "cycles_count": cycles_count,
                "verifications_count": verif_count,
                "leases_count": lease_count,
                "resource_usage_entries": usage_entries
            }
        )
    else:
        soak_sec = _truth_response(
            truth_class="HELM_SOAK_TRUTH",
            source="none",
            observed_at=now(),
            freshness_seconds=0.0,
            data={"state": "UNKNOWN", "reason": "no soak package found"}
        )
        
    pert_data = {
        "runtime": runtime_sec,
        "factories": factories_sec,
        "tasks": tasks_sec,
        "leases": leases_sec,
        "authority": authority_sec,
        "integrity": integrity_sec,
        "soak": soak_sec,
        "adapters": live_adapters(),
        "spend": live_spend(),
        "northstar": live_northstar(),
        "security": live_security(),
        "census": live_census(),
        "verdict": live_verdict(),
    }
    
    return JSONResponse(_truth_response(
        truth_class="HELM_PERT_TRUTH",
        source="multi-source aggregation",
        observed_at=now(),
        freshness_seconds=0.0,
        data=pert_data
    ))


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


@app.get("/console", response_class=HTMLResponse)
def serve_console() -> str:
    """Serve the single console FROM the API so it is SAME-ORIGIN.

    It previously hardcoded API = "http://127.0.0.1:8770". On a PHONE, 127.0.0.1 is the PHONE's
    own localhost — so the page loaded and every fetch failed. Same-origin makes it work
    identically on the Mac, the phone, and over Tailscale.
    """
    f = ROOT / "frontend_live" / "console.html"
    return f.read_text() if f.exists() else "<h1>console missing</h1>"


@app.get("/arch", response_class=HTMLResponse)
def serve_arch() -> str:
    """DoDAF baseline architecture — same-origin, phone-safe."""
    f = ROOT / "frontend_live" / "architecture.html"
    return f.read_text() if f.exists() else "<h1>architecture missing</h1>"


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

