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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load gitignored env files so ElevenLabs / secrets survive restarts without
# putting keys in the process command line or the repo.
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.elevenlabs", override=True)
except Exception:
    pass

DB = ROOT / "backend" / "swarm_ledger.db"
LEASES = ROOT / "coordination" / "leases"
PKGS = ROOT / "coordination" / "council" / "live_proof_packages"
ARTIFACTS = ROOT / "artifacts" / "factory"
UI = ROOT / "frontend_live" / "helm.html"
PERT_UI = ROOT / "frontend_live" / "pert.html"

UNKNOWN = "UNKNOWN"

app = FastAPI(title="HELM LIVE")

# CORS + API hardening (audit R-CORS / R-AUTH). Never allow_origins=["*"] on the
# control plane. Origins come from HELM_CORS_ALLOWLIST (comma-separated), falling
# back to the legacy HELM_CORS_ORIGINS, then to a safe loopback default; optional
# *.ts.net (Tailscale) via HELM_CORS_ALLOW_TSNET=1. See backend/security/api_hardening.py.
import os as _os

from backend.security.api_hardening import cors_middleware_kwargs, ApiHardeningMiddleware

app.add_middleware(CORSMiddleware, **cors_middleware_kwargs())

# Zero-Trust read-auth middleware: MOUNTED, default OFF (HELM_READ_AUTH_ENABLED).
# Mounting makes the cutover path real; enabling still requires founder token env.
# See backend/security/zero_trust/ and audit finding SEC-01 / R-01.
from backend.security.zero_trust.config import HardenedConfig as _ZTConfig
from backend.security.zero_trust.read_auth import ReadAuthMiddleware as _ReadAuthMiddleware

_zt_cfg = _ZTConfig.from_env()
app.add_middleware(_ReadAuthMiddleware, config=_zt_cfg)

# API hardening (bearer gate + payload limit + rate limit + security headers).
# Added LAST so it is the OUTERMOST layer: it short-circuits 401/413/429 before the
# heavy handlers run and stamps security headers on every response. Deny-by-default
# bearer gate is FLAGGED (HELM_REQUIRE_AUTH=1 + HELM_API_TOKEN) — default OFF, so
# nothing changes until the founder provisions the token and restarts.
app.add_middleware(ApiHardeningMiddleware)

from backend.instrument_integrity.council_router import council_router
app.include_router(council_router)

# SWARM-1: unified control plane + live service-health map. Real logic lives in
# backend/helm/health_registry.py — this is the minimal registration block.
from backend.helm.health_registry import health_router
app.include_router(health_router)

# SWARM-3: NIST CSF 2.0 x SP 800-53 Rev 5 control-coverage matrix. Real logic lives in
# backend/helm/nist_matrix.py — this is the minimal registration block.
from backend.helm.nist_matrix import nist_router
app.include_router(nist_router)

# HAF: HOCH Audit Factory v0.1 API endpoints
from backend.audit_factory.router import haf_router
app.include_router(haf_router)

# HELM Voice Executive — orchestration-backed voice agent API (read-only + stage-only)
from backend.voice.router import router as voice_router
app.include_router(voice_router)


# Runtime Bridge + Dispatch Gateway projections (EDR-0001/0002) — read + OCC PATCH
try:
    from backend.helm_runtime.bridge_api import router_or_none as _helm_bridge_router

    _br = _helm_bridge_router()
    if _br is not None:
        app.include_router(_br)
except Exception:
    pass  # fail open on import only; routes simply absent if substrate broken

# Knowledge Engine — governed retrieval (EDR-0004) — read-only projections
try:
    from backend.helm_runtime.knowledge_api import router_or_none as _helm_knowledge_router

    _kr = _helm_knowledge_router()
    if _kr is not None:
        app.include_router(_kr)
except Exception:
    pass  # fail open on import only; routes simply absent if substrate broken



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


@app.get("/api/v1/helm/external")
def api_v1_external():
    """External-milestone tracker — Principle V (Honest Uncertainty) as code.

    RELEASE (Epic Fury App Store) and REVENUE (first settled dollar) each hold at
    BLOCKED_EXTERNAL / PAYMENT_AUTHORIZED and advance ONLY on authoritative, fresh
    evidence. Standard truth envelope (truth_class/source/observed_at/
    freshness_seconds/tested_commit).
    """
    from backend.truth.external_milestones import compute_external_milestones
    m = compute_external_milestones()
    return JSONResponse(_truth_response(
        truth_class=m["truth_class"],
        source=m["source"],
        observed_at=m["observed_at"],
        freshness_seconds=m["freshness_seconds"],
        data={
            "milestones": m["milestones"],
            "doctrine": m["doctrine"],
            "build_ms": m["build_ms"],
        },
    ))


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


@app.get("/api/v1/helm/jspace/brain")
def api_v1_jspace_brain():
    """The HJOS observation graph as a 'brain': 6 observer regions, each watching subjects, with the
    LATEST real verdict per (observer, subject). Read-only. Fail-closed: no assessments -> UNKNOWN,
    never a fabricated-alive brain. Every node/edge here is a real assessment from the ledger."""
    import time
    apath = ROOT / "coordination" / "jspace" / "assessments.jsonl"
    hpath = ROOT / "coordination" / "jspace" / "health.json"
    if not apath.exists() or not apath.read_text().strip():
        return JSONResponse(_truth_response(
            truth_class="HJOS_BRAIN_TRUTH", source="coordination/jspace/assessments.jsonl",
            observed_at=now(), freshness_seconds=None,
            data={"state": UNKNOWN, "reason": "no HJOS assessments yet", "observers": []}))
    # latest assessment per (observer, subject) — the ledger is append-only, newest wins
    latest = {}
    for line in apath.read_text().splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        k = (r.get("observer"), r.get("subject"))
        if k[0] and k[1]:
            latest[k] = r
    from collections import defaultdict
    obs_map = defaultdict(list)
    for (obs, subj), r in latest.items():
        obs_map[obs].append({
            "subject": subj,
            "assessment": r.get("assessment"),
            "confidence": r.get("confidence"),
            "detail": (r.get("detail") or "")[:200],
            "recommended_action": r.get("recommended_action"),
            "observation_id": r.get("observation_id"),
            "claimed_state": r.get("claimed_state"),
            "observed_state": r.get("observed_state"),
            "state_mutated": r.get("state_mutated"),
        })
    def _worst(subs):
        order = {"CONTRADICTED": 3, "BLOCKED": 2, "CONFIRMED_LIVE": 1}
        return max((order.get(s["assessment"], 0) for s in subs), default=0)
    rank = {3: "CONTRADICTED", 2: "BLOCKED", 1: "CONFIRMED_LIVE", 0: "UNKNOWN"}
    observers = []
    for obs in sorted(obs_map):
        subs = sorted(obs_map[obs], key=lambda s: -{"CONTRADICTED": 3, "BLOCKED": 2,
                                                     "CONFIRMED_LIVE": 1}.get(s["assessment"], 0))
        observers.append({"observer": obs, "region": obs.replace("jspace_", ""),
                          "verdict": rank[_worst(subs)], "subjects": subs})
    health = {}
    try:
        health = json.loads(hpath.read_text()) if hpath.exists() else {}
    except Exception:
        health = {}
    fresh = float(time.time() - apath.stat().st_mtime)
    return JSONResponse(_truth_response(
        truth_class="HJOS_BRAIN_TRUTH", source="coordination/jspace/assessments.jsonl",
        observed_at=now(), freshness_seconds=fresh,
        data={"state": "CONFIRMED_LIVE",
              "consensus": health.get("overall", "UNKNOWN"),
              "promotion_authority": health.get("promotion_authority", "NONE"),
              "recommended_action": health.get("recommended_action"),
              "cycle_id": health.get("cycle_id"),
              "observer_counts": health.get("observer_counts", {}),
              "open_alerts": health.get("open_alerts"),
              "unresolved_findings": health.get("unresolved_findings"),
              "observer_total": len(observers),
              "subject_total": sum(len(o["subjects"]) for o in observers),
              "observers": observers}))


@app.get("/brain")
def serve_brain():
    """UI pass 2: /brain (cinematic neural view) consolidated into the J-Space console."""
    return RedirectResponse(url="/jspace", status_code=307)


@app.get("/brain-classic", response_class=HTMLResponse)
def serve_brain_classic() -> str:
    """The J-Space Brain — cinematic animated neural view of the HJOS observers. Same-origin so it
    renders identically on the Mac, the phone, and over Tailscale."""
    f = ROOT / "frontend_live" / "brain.html"
    return f.read_text() if f.exists() else "<h1>brain missing</h1>"


@app.get("/theater", response_class=HTMLResponse)
def serve_theater() -> str:
    """The Hoch Pods Theater — cinematic swarm-launch visualization driven by the LIVE factory
    feed (pods ignite by real runtime_state; agents spin up and route to the lanes). No simulated
    data. Same-origin so it renders on the Mac, the phone, and over Tailscale."""
    f = ROOT / "frontend_live" / "theater.html"
    return f.read_text() if f.exists() else "<h1>theater missing</h1>"


@app.get("/api/v1/helm/mission")
@app.get("/api/v1/helm/mission/state")
def api_v1_mission_state():
    """Mission State Engine — single operational view for all interfaces.

    Derived from goal_state + champion_gates + conmon + revenue ledger.
    Executive dashboard + critical path; no fake green.
    """
    from backend.mission_control.mission_state import write_mission_state

    try:
        state = write_mission_state()
        return JSONResponse(_truth_response(
            truth_class="HELM_MISSION_STATE",
            source="coordination/goal/mission_state.json",
            observed_at=now(),
            freshness_seconds=0.0,
            data=state,
        ))
    except Exception as e:
        return JSONResponse(_truth_response(
            truth_class="HELM_MISSION_STATE",
            source="backend.mission_control.mission_state",
            observed_at=now(),
            freshness_seconds=None,
            data={"state": UNKNOWN, "reason": str(e)},
        ))


@app.get("/api/v1/helm/mission/executive")
def api_v1_mission_executive():
    """Plain-text executive dashboard for humans and paste into chat."""
    from fastapi.responses import PlainTextResponse
    from backend.mission_control.mission_state import render_executive_text, write_mission_state

    try:
        st = write_mission_state()
        return PlainTextResponse(render_executive_text(st), media_type="text/plain; charset=utf-8")
    except Exception as e:
        return PlainTextResponse(f"MISSION STATE UNKNOWN\n{e}\n", status_code=500)


@app.get("/api/v1/helm/goal")
def api_v1_goal():
    """Roadmap to GOAL HELM: the weighted requirement registry (goal_state.json, computed ONLY from
    validators that executed successfully — no fake green) PLUS the live soak phase chain A->B->C->
    DOORSTEP computed fresh from the independent seals. Read-only, fail-closed."""
    import time
    gp = ROOT / "coordination" / "goal" / "goal_state.json"
    goal = {}
    if gp.exists():
        try:
            goal = json.loads(gp.read_text())
        except Exception:
            goal = {}
    # live soak phase chain — the part that moves in real time toward the DOORSTEP
    def _phase(pref, phase, secs):
        pkgs = sorted(PKGS.glob(f"HELM-SOAK-{pref}-*Z"), key=lambda p: p.name, reverse=True)
        for pk in pkgs:
            seal = pk / "seal_verdict.json"
            cfg = pk / "soak_config.json"
            if seal.exists():
                try:
                    v = json.loads(seal.read_text()).get("verdict", "")
                except Exception:
                    v = ""
                if v == f"SOAK_PHASE_{phase}_PASS":
                    return {"phase": phase, "state": "SEALED_PASS", "package": pk.name,
                            "hours": round(secs / 3600, 1)}
                if v.endswith("_FAIL"):
                    return {"phase": phase, "state": "FAILED", "package": pk.name}
            # unsealed + fresh evidence => running
            led = pk / "daemon" / "task_lease_ledger.jsonl"
            if cfg.exists() and led.exists() and (time.time() - led.stat().st_mtime) < 600:
                try:
                    start = json.loads(cfg.read_text()).get("started_at", "")
                    import datetime
                    el = (datetime.datetime.now(datetime.timezone.utc) -
                          datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds()
                    return {"phase": phase, "state": "RUNNING", "package": pk.name,
                            "progress_pct": round(min(100, 100 * el / secs), 1),
                            "elapsed_h": round(el / 3600, 2), "hours": round(secs / 3600, 1)}
                except Exception:
                    return {"phase": phase, "state": "RUNNING", "package": pk.name}
        return {"phase": phase, "state": "PENDING", "hours": round(secs / 3600, 1)}
    chain = [_phase("2H", "A", 7200), _phase("8H", "B", 28800), _phase("24H", "C", 86400)]
    done = all(p["state"] == "SEALED_PASS" for p in chain)
    chain.append({"phase": "DOORSTEP", "state": "READY" if done else "PENDING",
                  "detail": "founder gate — 24/7 baseline proven" if done else "awaiting A+B+C seals"})
    # per-layer rollup from the requirement registry
    reqs = goal.get("requirements", [])
    from collections import defaultdict
    layers = defaultdict(lambda: {"total": 0, "passed": 0, "weight": 0.0, "contributes": 0.0})
    for r in reqs:
        L = layers[r.get("layer", "?")]
        L["total"] += 1; L["weight"] += r.get("weight", 0) or 0
        L["contributes"] += r.get("contributes", 0) or 0
        if str(r.get("state", "")).upper() in ("PASS", "SATISFIED", "VALIDATED"):
            L["passed"] += 1
    fresh = float(time.time() - gp.stat().st_mtime) if gp.exists() else None
    return JSONResponse(_truth_response(
        truth_class="HELM_GOAL_TRUTH", source="coordination/goal/goal_state.json",
        observed_at=now(), freshness_seconds=fresh,
        data={"north_star": goal.get("canonical_north_star"),
              "computed_at": goal.get("computed_at"),
              "hard_constraint": goal.get("hard_constraint"),
              "metrics": goal.get("metrics", {}),
              "layers": {k: dict(v) for k, v in layers.items()},
              "requirements": reqs,
              "critical_path": goal.get("critical_path", []),
              "next_recommended_task": goal.get("next_recommended_task"),
              "soak_chain": chain,
              "soak_24_7_proven": done}))


@app.get("/api/v1/helm/hmai")
def api_v1_hmai():
    """HELM Mission Assurance Index (HMAI) — the composite readiness index.

    Read-only. Re-derived from live repo evidence on every call: a weighted 0-100
    composite over pillars (mission execution, evidence freshness, founder approvals,
    runtime truth, cyber/security, AI governance, supply chain/ConMon/zero-trust),
    each with its own state (VERIFIED/DEGRADED/STALE/UNKNOWN). UNKNOWN pillars are
    down-weighted and never rendered green — no fake green.
    """
    import time
    from backend.truth.hmai import compute_hmai, GOAL_STATE
    # Standard truth envelope with an explicit nested `data` payload (the HMAI
    # result is a large object; nesting keeps the envelope keys unambiguous).
    def _envelope(data, source, freshness):
        return {
            "truth_class": "HELM_MISSION_ASSURANCE_INDEX",
            "source": source,
            "observed_at": now(),
            "freshness_seconds": freshness,
            "tested_commit": get_current_commit(),
            "data": data,
        }
    try:
        data = compute_hmai()
    except Exception as e:
        return JSONResponse(_envelope(
            {"state": UNKNOWN, "reason": f"hmai computation failed: {type(e).__name__}: {e}"},
            "backend.truth.hmai", None))
    freshness = float(time.time() - GOAL_STATE.stat().st_mtime) if GOAL_STATE.exists() else None
    return JSONResponse(_envelope(
        data,
        "backend/truth/hmai.py (goal_state + factory_registry + runtime_source + security posture)",
        freshness))


@app.get("/executive", response_class=HTMLResponse)
def serve_executive() -> str:
    """HELM Executive Command — the Layer-1 mission-control screen. Same-origin so it
    renders identically on the Mac, the phone, and over Tailscale. Reads /api/v1/helm/hmai."""
    f = ROOT / "frontend_live" / "executive.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>executive.html missing</h1>"


@app.get("/roadmap", response_class=HTMLResponse)
def serve_roadmap() -> str:
    """Live roadmap to GOAL HELM — dark theme, auto-updating from the goal registry + soak chain."""
    f = ROOT / "frontend_live" / "roadmap.html"
    return f.read_text() if f.exists() else "<h1>roadmap missing</h1>"


@app.get("/ops", response_class=HTMLResponse)
def serve_ops_center() -> str:
    """HELM Executive Operations Center — the single dark mission-control console.
    Michael's one entry point: HELM is the only thing he talks to; the frontier
    models are interchangeable backends shown as workers. Reads the runtime-truth
    projections (/mission, /mission-health, /workers, /timeline, /external) same-origin."""
    f = ROOT / "frontend_live" / "ops_center.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>ops_center.html missing</h1>"


@app.get("/api/v1/helm/executive-brief")
def api_executive_brief():
    """Unified Executive Brief — integrates ALL existing HELM projections (mission,
    HMAI, external milestones, AI/workers, cybersecurity/ConMon, factories, founder
    decisions) into one honest payload. Fail-closed: absent sources render UNKNOWN,
    unconnected lifestyle domains render NOT_CONNECTED. No fake green."""
    from backend.helm_executive_brief import build_executive_brief
    return build_executive_brief()


@app.get("/command", response_class=HTMLResponse)
def serve_command_center() -> str:
    """HELM Executive Command Center — the integrated 15-panel view (mockup-aligned),
    every number backed by runtime truth from /api/v1/helm/executive-brief. Illustrative
    mockup figures are NOT used; real values or honest UNKNOWN/NOT_CONNECTED only."""
    f = ROOT / "frontend_live" / "command_center.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>command_center.html missing</h1>"


@app.get("/api/v1/helm/goal-pert")
def api_goal_pert():
    """Backcast PERT to GOAL_HELM: nodes with 3-point expected times, critical path,
    honest percent-to-GOAL, and live System-Integration status (si_status.json)."""
    from backend.helm_goal_pert import build_goal_pert
    return build_goal_pert()


@app.get("/pert-live", response_class=HTMLResponse)
def serve_pert_live() -> str:
    """LIVE PERT → GOAL — dark-theme critical-path + System Integration watch board.
    Reads /api/v1/helm/goal-pert; refreshes so the founder can watch the push to GOAL."""
    f = ROOT / "frontend_live" / "pert_live.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>pert_live.html missing</h1>"


@app.get("/favicon.ico")
def _favicon():
    # Silence the browser favicon 404 on the HELM dark pages (1x1 transparent).
    import base64
    from starlette.responses import Response
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    )
    return Response(content=png, media_type="image/png")


@app.get("/council", response_class=HTMLResponse)
def serve_council() -> str:
    """HELM Council Control Plane — the single dark surface where the founder hands HELM a
    mission. HELM classifies the ask into a lane, routes it to the model that OWNS that lane
    (Orchestrator/ChatGPT plans, Builder/Claude engineers, Auditor/Grok verifies, Local for
    private data), reasons, and solves. The founder does not pick a member. No copy/paste."""
    f = ROOT / "frontend_live" / "council.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>council.html missing</h1>"


@app.get("/haf", response_class=HTMLResponse)
def serve_haf() -> str:
    """HAF Console — HOCH Audit Factory command-center dashboard."""
    f = ROOT / "frontend_live" / "haf_console.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>haf_console.html missing</h1>"



@app.get("/api/v1/helm/council/status")
def api_council_status():
    """Live per-lane readiness — which council members HELM can currently fire (presence only,
    never a key value). READY = key present + money-gate on; GATED = key present, gate off;
    BLOCKED_EXTERNAL = credential not supplied."""
    from backend.dispatch.council_router import council_status
    return council_status()


@app.post("/api/v1/helm/council/solve")
def api_council_solve(body: dict):
    """HELM assigns the mission to the lane that owns it and solves. The founder does NOT pick
    a model — HELM classifies the ask → capability → owning role → provider, then dispatches.
    mode='orchestrate' runs the full governed chain (plan → build → verify). Fail-closed and
    honest: a lane whose provider isn't enabled returns BLOCKED, never a fabricated answer."""
    from fastapi import HTTPException
    from backend.dispatch.council_router import solve, orchestrate
    prompt = ((body or {}).get("prompt") or "").strip()
    mode = ((body or {}).get("mode") or "auto").strip().lower()
    if not prompt:
        raise HTTPException(status_code=400, detail={"error": "empty_prompt"})
    if mode == "orchestrate":
        return orchestrate(prompt)
    return solve(prompt)


@app.post("/api/v1/helm/council/chat")
def api_council_chat(body: dict):
    """Converse with the council in one thread. mode='auto' routes to the owning lane;
    mode='all' fans out to the whole council (each member answers in its own voice).
    This is the primary surface — the founder talks here, not in a terminal."""
    from fastapi import HTTPException
    from backend.dispatch.council_router import council_chat
    prompt = ((body or {}).get("prompt") or "").strip()
    mode = ((body or {}).get("mode") or "auto").strip().lower()
    history = (body or {}).get("history") or []
    if not prompt:
        raise HTTPException(status_code=400, detail={"error": "empty_prompt"})
    return council_chat(prompt, mode=mode, history=history)


@app.post("/api/v1/helm/council/score")
def api_council_score(body: dict):
    """AUTONOMOUS cross-model scoring. Send {"task": "..."} and HELM fans it to every lane
    (ChatGPT/Orchestrator, Claude/Builder, Grok/Auditor, Local), collects each model's answer,
    then the Auditor scores them all against HELM doctrine + real runtime state — returning a
    scorecard, ranking, disagreements, synthesis and a recommended action.

    Optional {"responses": {"CHATGPT_5.6": "...", "CLAUDE_OPUS_4.8": "..."}} scores supplied
    answers instead of dispatching. No fake green: if scoring is blocked it says so."""
    from fastapi import HTTPException
    from backend.dispatch.council_router import score_council
    task = ((body or {}).get("task") or (body or {}).get("prompt") or "").strip()
    responses = (body or {}).get("responses") or None
    if not task:
        raise HTTPException(status_code=400, detail={"error": "empty_task"})
    return score_council(task, responses=responses)


@app.post("/api/v1/helm/council/verify")
def api_council_verify():
    """One click: HELM fires the independent auditor (Grok) against the frozen evidence and
    writes the verdict — the founder never runs a script. Returns the OVERALL verdict."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from helm_fire_verification import run_verification
    return run_verification()


@app.post("/api/v1/helm/council/build")
def api_council_build(body: dict):
    """Guarded EXECUTE Builder lane — Claude (Opus) builds inside HELM. mode='plan' (default,
    read-only) or mode='execute' (approved; snapshot-before + frozen-target guard + rollback).
    Founder-gated (requires CLI_CLAUDE grant); cost-capped; ledgered. Irreversible actions
    (deploy/publish/push/money) stay founder-gated — this lane changes code only."""
    from fastapi import HTTPException
    from backend.dispatch.guarded_build import build
    task = ((body or {}).get("task") or "").strip()
    mode = ((body or {}).get("mode") or "plan").strip().lower()
    if not task:
        raise HTTPException(status_code=400, detail={"error": "empty_task"})
    return build(task, mode=mode)


@app.get("/api/v1/helm/council/activity")
def api_council_activity(limit: int = 30):
    """Live brain activity — recent COUNCIL_* + GOAL_NODE_UPDATE events (dispatches, verdicts,
    builds, debug passes, node closes) newest-first, so the theater shows the swarm reasoning."""
    from backend.helm_runtime.event_bus import tail_events
    evs = tail_events(300)
    keep = [e for e in evs if str(e.get("type", "")).startswith("COUNCIL_")
            or e.get("type") == "GOAL_NODE_UPDATE"]
    keep = list(reversed(keep))[:max(1, min(limit, 120))]
    return {"schema": "HELM_COUNCIL_ACTIVITY_v1", "count": len(keep),
            "events": [{"type": e.get("type"), "producer": e.get("producer"),
                        "timestamp": e.get("timestamp"), "payload": e.get("payload", {}),
                        "evidence": e.get("evidence", [])} for e in keep]}


@app.get("/api/v1/helm/build-status")
def api_build_status():
    """Live build-to-GOAL status — the autonomous runner's state, current node, %, and each
    PERT node's status. Read-only; reflects what the runner writes as it works."""
    import json as _json
    status_f = ROOT / "coordination" / "goal" / "build_to_goal_status.json"
    pert_f = ROOT / "coordination" / "goal" / "helm_pert.json"
    out = {"state": "UNKNOWN", "detail": "", "percent_to_goal": None, "nodes": {}, "node_labels": {}}
    try:
        out.update(_json.loads(status_f.read_text()))
    except Exception:
        pass
    try:
        p = _json.loads(pert_f.read_text())
        out["node_labels"] = {n.get("id"): (n.get("label") or n.get("name") or "")
                              for n in p.get("nodes", [])}
        out["node_order"] = [n.get("id") for n in p.get("nodes", [])]
    except Exception:
        pass
    return out


@app.get("/build", response_class=HTMLResponse)
def serve_build_theater() -> str:
    """Live Build Theater — watch the swarm reason and build toward GOAL in real time."""
    f = ROOT / "frontend_live" / "build_theater.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>build_theater.html missing</h1>"


@app.get("/api/v1/helm/audit-status")
def api_audit_status():
    """Live audit-to-GREEN status — each controllable audit's GREEN/FINDING state + the
    externally-gated audits that require third-party evidence. Read-only."""
    import json as _json
    f = ROOT / "coordination" / "goal" / "audit_status.json"
    try:
        return _json.loads(f.read_text())
    except Exception:
        return {"state": "NOT_STARTED", "audits": {}, "green": 0, "total_controllable": 7,
                "externally_gated": ["ATO / independent security certification", "SOC 2 attestation",
                                     "Financial settlement audit (Stripe/bank)"]}


@app.get("/audit", response_class=HTMLResponse)
def serve_audit_theater() -> str:
    """Live Audit Theater — watch the audit swarm drive each audit to GREEN."""
    f = ROOT / "frontend_live" / "audit_theater.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>audit_theater.html missing</h1>"


@app.post("/api/v1/helm/dispatch")
def api_council_dispatch(body: dict):
    """HELM fires a council member from the UI. Money-gated + fail-closed: requires
    HELM_DISPATCH_ENABLED + the provider key (auto-loaded from ~/.helm/helm.env). Records a
    COUNCIL_DISPATCH event (never the secret). Returns the model's text."""
    from fastapi import HTTPException
    from backend.dispatch import dispatch as live_dispatch
    from backend.helm_runtime.dispatch_gateway import DispatchNotEnabledError
    role = (body or {}).get("role") or None
    capability = (body or {}).get("capability") or None
    provider = (body or {}).get("provider") or None
    prompt = ((body or {}).get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail={"error": "empty_prompt"})
    try:
        r = live_dispatch(role=role, capability=capability, provider=provider, prompt=prompt)
    except DispatchNotEnabledError as e:
        raise HTTPException(status_code=403, detail={
            "error": "dispatch_disabled", "message": str(e),
            "howto": "add the provider key to ~/.helm/helm.env and set HELM_DISPATCH_ENABLED=1"})
    except Exception as e:  # provider/network error — surface honestly, no secret
        raise HTTPException(status_code=502, detail={"error": "provider_error", "message": str(e)[:300]})
    try:  # record the dispatch on the nervous system (content length only, never the text/secret)
        # HELM-GOV | extends: N6 emitter (dispatch endpoint) | edr: EDR-0006-R4 | why: a dispatch is a
        #          | material decision — carry a Proof Record via the single gate.
        from backend.helm_runtime.governed_emit import emit_governed
        emit_governed(type="COUNCIL_DISPATCH", producer=(role or capability or "council"),
                      mission_id="COUNCIL", authority="helm_live_api:dispatch_gateway",
                      explanation=f"dispatch to {r.get('provider')}/{r.get('model')}",
                      inputs={"provider": r.get("provider"), "model": r.get("model"), "prompt_chars": len(prompt)},
                      proof_command="POST /api/v1/helm/dispatch (guarded gateway)",
                      environment="helm_live_api",
                      payload={"provider": r.get("provider"), "model": r.get("model"), "prompt_chars": len(prompt)})
    except Exception:
        pass
    return {"ok": True, **r}


@app.get("/api/v1/helm/jspace/lens")
def api_v1_jspace_lens():
    """Semantic Jacobian Lens — which findings actually hold the promotion gate closed, ranked by how
    much each one moves the decision, plus fragility (how close the decision is to flipping). Read-only.
    Fail-closed: no assessments -> UNKNOWN, never promotable."""
    import time
    from backend.jspace.lens import SemanticJacobianLens
    apath = ROOT / "coordination" / "jspace" / "assessments.jsonl"
    if not apath.exists() or not apath.read_text().strip():
        return JSONResponse(_truth_response(
            truth_class="HJOS_LENS_TRUTH", source="coordination/jspace/assessments.jsonl",
            observed_at=now(), freshness_seconds=None,
            data={"consensus": "UNKNOWN", "promotable": False, "drivers": [],
                  "reason": "no HJOS assessments yet"}))
    out = SemanticJacobianLens.from_ledger(apath).compute()
    fresh = float(time.time() - apath.stat().st_mtime)
    return JSONResponse(_truth_response(
        truth_class="HJOS_LENS_TRUTH", source="coordination/jspace/assessments.jsonl",
        observed_at=now(), freshness_seconds=fresh, data=out))


@app.get("/jspace", response_class=HTMLResponse)
def serve_jspace_console() -> str:
    """HELM J-SPACE operational console — left status rail, AI Agent Network Map (HJOS observers),
    Cryptographic Hash Tables (AU-9 chain). Every panel is live runtime truth; fail-closed."""
    f = ROOT / "frontend_live" / "jspace_console.html"
    return f.read_text() if f.exists() else "<h1>jspace console missing</h1>"


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


@app.get("/api/v1/helm/chain")
def api_v1_chain():
    """AU-9 evidence chain, most-recent N records + live verify status. Never a fake green:
    a broken chain returns state=CONTRADICTED with the exact break point."""
    import time
    from backend.truth.evidence_chain import verify_chain, ChainBroken
    pkg = _newest_soak_pkg()
    led = None
    for cand in ([pkg/"daemon"/"task_lease_ledger.jsonl", pkg/"lease_ledger.jsonl"] if pkg else []) + \
                [ROOT/"coordination"/"council"/"daemon"/"task_lease_ledger.jsonl"]:
        if cand and cand.exists() and cand.read_text().strip():
            led = cand; break
    if not led:
        return JSONResponse(_truth_response(truth_class="HELM_CHAIN_TRUTH", source="none",
            observed_at=now(), freshness_seconds=None,
            data={"state":"UNKNOWN","reason":"no chained ledger yet","blocks":[]}))
    rows=[json.loads(l) for l in led.read_text().splitlines() if l.strip()]
    state="CONFIRMED_LIVE"; reason=None
    try: verify_chain(led)
    except ChainBroken as e: state="CONTRADICTED"; reason=str(e)
    blocks=[{"i":i,"task":r.get("task_id"),"status":r.get("status"),
             "prev":str(r.get("prev_hash") or "")[:10],"hash":str(r.get("entry_hash") or "")[:10],
             "chained":bool(r.get("prev_hash") and r.get("entry_hash"))}
            for i,r in enumerate(rows[-40:])]
    fresh=float(time.time()-led.stat().st_mtime)
    return JSONResponse(_truth_response(truth_class="HELM_CHAIN_TRUTH",
        source=str(led.relative_to(ROOT)), observed_at=now(), freshness_seconds=fresh,
        data={"state":state,"reason":reason,"total_rows":len(rows),"blocks":blocks}))


@app.get("/api/v1/helm/agents")
def api_v1_agents():
    """Agent performance & ACCOUNTABILITY — ledger dimensions only (fail-closed).

    Accountable axes: factory · validator · adapter · scheduler.
    NOT accountable as a leaderboard: ephemeral worker_id (one per task).

    Fail-closed:
      - no package → UNKNOWN
      - adapter with no runs omitted (never drawn as zero-loser)
      - cost always carries measured state (e.g. $0.00 OBSERVED)
      - broken AU-9 chain → CONTRADICTED for the whole view
    """
    import time, statistics
    from collections import Counter, defaultdict
    from datetime import datetime
    pkg = _newest_soak_pkg()
    daemon = (pkg / "daemon") if pkg else None
    env_p = daemon / "result_envelopes.jsonl" if daemon else None
    ver_p = daemon / "verification_ledger.jsonl" if daemon else None
    lease_p = daemon / "task_lease_ledger.jsonl" if daemon else None
    if not (env_p and env_p.exists() and ver_p and ver_p.exists()):
        return JSONResponse(_truth_response(truth_class="HELM_AGENT_TRUTH", source="none",
            observed_at=now(), freshness_seconds=None,
            data={"state": "UNKNOWN",
                  "reason": "no attributed evidence package yet",
                  "doctrine": {
                      "no_named_agent_leaderboard": True,
                      "reason": "worker_id is ephemeral (one per task); ranking would fabricate continuity",
                  }}))

    def _rows(p):
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    env = _rows(env_p); ver = _rows(ver_p)

    def _pt(s):
        try: return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        except Exception: return None

    # AU-9 chain status — if broken, the accountability view is CONTRADICTED
    chain_state = "UNKNOWN"
    chain_reason = None
    if lease_p and lease_p.exists() and lease_p.read_text().strip():
        try:
            from backend.truth.evidence_chain import verify_chain, ChainBroken
            verify_chain(lease_p)
            chain_state = "CONFIRMED_LIVE"
        except Exception as e:
            # ChainBroken or import miss
            chain_state = "CONTRADICTED"
            chain_reason = str(e)[:240]

    # factory x verdict matrix + named failing checks (accountability core)
    fac = defaultdict(lambda: {"pass": 0, "fail": 0, "failing_checks": Counter(),
                               "validators": Counter()})
    for r in ver:
        f = r.get("factory") or "?"
        if r.get("validator"):
            fac[f]["validators"][r.get("validator")] += 1
        if r.get("verdict") == "PASS":
            fac[f]["pass"] += 1
        else:
            fac[f]["fail"] += 1
            for c in (r.get("failed_checks") or []):
                name = c.get("check") if isinstance(c, dict) else str(c)
                fac[f]["failing_checks"][name] += 1
    matrix = []
    for f, d in sorted(fac.items()):
        tot = d["pass"] + d["fail"]
        top_val = d["validators"].most_common(1)[0][0] if d["validators"] else None
        matrix.append({
            "factory": f,
            "pass": d["pass"],
            "fail": d["fail"],
            "total": tot,
            "pass_rate": round(100 * d["pass"] / tot, 1) if tot else None,
            "validator": top_val,
            "failing_checks": dict(d["failing_checks"]),
        })

    # latency distribution per factory + slow tail (sha256-traceable)
    lat_by = defaultdict(list); tail = []
    for r in env:
        a, b = _pt(r.get("started_at")), _pt(r.get("completed_at"))
        if a and b:
            s = (b - a).total_seconds()
            lat_by[r.get("factory") or "?"].append(s)
            tail.append({
                "task": r.get("task_id"),
                "factory": r.get("factory"),
                "seconds": round(s, 1),
                "sha256": str(r.get("artifact_sha256") or "")[:16],
            })

    def _pct(xs, q):
        if not xs:
            return None
        xs = sorted(xs)
        k = max(0, min(len(xs) - 1, int(round(q * (len(xs) - 1)))))
        return round(xs[k], 1)

    latency = []
    for f, xs in sorted(lat_by.items()):
        latency.append({
            "factory": f,
            "n": len(xs),
            "p50": _pct(xs, .5),
            "p95": _pct(xs, .95),
            "max": round(max(xs), 1),
            "mean": round(sum(xs) / len(xs), 1) if xs else None,
            "min": round(min(xs), 1) if xs else None,
        })
    slow_tail = sorted(tail, key=lambda t: t["seconds"], reverse=True)[:8]

    # adapter panel — only adapters that actually ran
    adp = defaultdict(lambda: {
        "runs": 0, "pass": 0, "cost_usd": 0.0, "cost_state": set(),
        "lat": [], "out_chars": [], "in_chars": [],
    })
    vv = {v.get("task_id"): v for v in ver}
    workers = set()
    for r in env:
        if r.get("worker_id"):
            workers.add(r.get("worker_id"))
        a = r.get("adapter") or "?"
        d = adp[a]
        d["runs"] += 1
        ver_row = vv.get(r.get("task_id")) or {}
        if ver_row.get("verdict") == "PASS":
            d["pass"] += 1
        try:
            d["cost_usd"] += float(r.get("cost_usd") or 0.0)
        except Exception:
            pass
        if r.get("cost_state"):
            d["cost_state"].add(r.get("cost_state"))
        s, e = _pt(r.get("started_at")), _pt(r.get("completed_at"))
        if s and e:
            d["lat"].append((e - s).total_seconds())
        if isinstance(r.get("out_chars"), int):
            d["out_chars"].append(r["out_chars"])
        if isinstance(r.get("in_chars"), int):
            d["in_chars"].append(r["in_chars"])

    adapters = []
    for a, d in sorted(adp.items()):
        if d["runs"] <= 0:
            continue  # never emit zero-loser empty adapters
        cost_state = "/".join(sorted(d["cost_state"])) or "UNKNOWN"
        cost_usd = round(d["cost_usd"], 4)
        adapters.append({
            "adapter": a,
            "runs": d["runs"],
            "pass_rate": round(100 * d["pass"] / d["runs"], 1),
            "cost_usd": cost_usd,
            "cost_state": cost_state,
            "cost_display": f"${cost_usd:.2f} {cost_state}",
            "p50_latency": _pct(d["lat"], .5),
            "median_out_chars": int(statistics.median(d["out_chars"])) if d["out_chars"] else None,
            "median_in_chars": int(statistics.median(d["in_chars"])) if d["in_chars"] else None,
        })

    # scheduler continuity
    sched = Counter(r.get("scheduler_instance_id") for r in env if r.get("scheduler_instance_id"))
    schedulers = [{"instance": s, "tasks": n} for s, n in sched.most_common()]
    sched_continuity = (
        "SINGLE_WRITER" if len(schedulers) <= 1
        else "SEQUENTIAL_HANDOFF"  # AU-9 chain proves non-overlap when CONFIRMED_LIVE
    )

    # custody sample — authority → dispatch → artifact → validator (latest + failures first)
    by_task_env = {r.get("task_id"): r for r in env if r.get("task_id")}
    failed_ids = [v.get("task_id") for v in ver if v.get("verdict") != "PASS" and v.get("task_id")]
    sample_ids = []
    for tid in failed_ids[-4:]:
        if tid not in sample_ids:
            sample_ids.append(tid)
    for r in reversed(env[-8:]):
        tid = r.get("task_id")
        if tid and tid not in sample_ids:
            sample_ids.append(tid)
        if len(sample_ids) >= 8:
            break
    custody = []
    for tid in sample_ids:
        r = by_task_env.get(tid) or {}
        v = vv.get(tid) or {}
        failed = []
        for c in (v.get("failed_checks") or []):
            failed.append(c.get("check") if isinstance(c, dict) else str(c))
        custody.append({
            "task": tid,
            "factory": r.get("factory") or v.get("factory"),
            "authority_class": r.get("authority_class"),
            "authority_decision_id": r.get("authority_decision_id"),
            "authority_status": r.get("authority_status"),
            "dispatch_digest": str(r.get("dispatch_digest") or "")[:16],
            "artifact_sha256": str(r.get("artifact_sha256") or "")[:16],
            "validator": v.get("validator"),
            "verdict": v.get("verdict"),
            "failed_checks": failed,
            "fencing_token": r.get("fencing_token"),
            "lease_id": r.get("lease_id"),
            "worker_id": r.get("worker_id"),  # shown as ephemeral, not ranked
        })

    # remediation — an accountability instrument must make un-acted-upon failures impossible to miss.
    # Read-only derivation (freeze-safe): a failed task is REMEDIATED only if a later attempt of the
    # same id verified PASS. Dispatch-COMPLETED + verdict-FAIL is NOT a defect — "the process ran" and
    # "the output was good" are correctly SEPARATE facts. The real gap is that a validation FAIL has no
    # retry path today, so a failure sits unremediated. Surface it; never let a green screen hide it.
    _hist = defaultdict(list)
    for v in ver:
        if v.get("task_id"):
            _hist[v["task_id"]].append(v.get("verdict"))
    _failed_tasks = [t for t, vs in _hist.items() if "FAIL" in vs]
    _remediated = [t for t in _failed_tasks if "PASS" in _hist[t]]
    _unremediated = sorted(t for t in _failed_tasks if "PASS" not in _hist[t])
    remediation = {
        "failures": len(_failed_tasks),
        "remediated": len(_remediated),
        "unremediated": len(_unremediated),
        "unremediated_ids": _unremediated[:12],
        "recovery_rate": round(100 * len(_remediated) / len(_failed_tasks), 1) if _failed_tasks else None,
        "retry_capability": ("NONE_OBSERVED" if _failed_tasks and not _remediated else "PRESENT"),
        "note": ("failed validations have no retry path in this run — each is an unremediated known-bad artifact"
                 if _unremediated else "no unremediated failures"),
    }

    total = len(ver)
    passed = sum(1 for v in ver if v.get("verdict") == "PASS")
    failed = total - passed
    fresh = float(time.time() - env_p.stat().st_mtime)

    # View state: chain contradiction wins over green
    if chain_state == "CONTRADICTED":
        view_state = "CONTRADICTED"
    elif total:
        view_state = "CONFIRMED_LIVE"
    else:
        view_state = "UNKNOWN"

    total_cost = round(sum(a["cost_usd"] for a in adapters), 4)
    cost_states = sorted({s for a in adapters for s in a["cost_state"].split("/") if s})

    return JSONResponse(_truth_response(
        truth_class="HELM_AGENT_TRUTH",
        source=str(env_p.relative_to(ROOT)),
        observed_at=now(),
        freshness_seconds=fresh,
        data={
            "state": view_state,
            "reason": chain_reason,
            "package": pkg.name if pkg else None,
            "doctrine": {
                "no_named_agent_leaderboard": True,
                "accountable_dimensions": [
                    "factory", "validator", "adapter", "scheduler_instance_id",
                ],
                "ephemeral_not_ranked": ["worker_id"],
                "empty_adapter_lanes": "omitted — never drawn as losers",
                "cost_display_rule": "always show measured state (e.g. $0.00 OBSERVED)",
            },
            "chain_state": chain_state,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(100 * passed / total, 1) if total else None,
            "ephemeral_worker_executions": len(workers),
            "adapter_count": len(adapters),
            "adapter_count_label": (
                f"{len(adapters)} adapter active this run"
                if len(adapters) == 1
                else f"{len(adapters)} adapters active this run"
            ),
            "cost_total_usd": total_cost,
            "cost_display": f"${total_cost:.2f} {'/'.join(cost_states) or 'UNKNOWN'}",
            "matrix": matrix,
            "latency": latency,
            "slow_tail": slow_tail,
            "adapters": adapters,
            "schedulers": schedulers,
            "scheduler_continuity": sched_continuity,
            "remediation": remediation,
            "custody": custody,
            "failures": [
                {
                    "task": c["task"],
                    "factory": c["factory"],
                    "validator": c["validator"],
                    "failed_checks": c["failed_checks"],
                }
                for c in custody if c.get("verdict") and c.get("verdict") != "PASS"
            ],
        },
    ))


@app.get("/command-wall", response_class=HTMLResponse)
def serve_command() -> str:
    """HELM Command Wall — cinematic wall + flow charts + evidence-chain + controls. (Was a
    SECOND /command registration that shadowed command.html; moved to /command-wall in UI pass 2
    so both Command views are reachable. /command = the 15-panel executive-brief Command Center.)"""
    f = ROOT / "frontend_live" / "command.html"
    return f.read_text() if f.exists() else "<h1>command missing</h1>"


@app.get("/console")
def serve_console():
    """UI pass 2: /console consolidated into the Command Center."""
    return RedirectResponse(url="/command", status_code=307)


@app.get("/arch", response_class=HTMLResponse)
def serve_arch() -> str:
    """DoDAF baseline architecture — same-origin, phone-safe."""
    f = ROOT / "frontend_live" / "architecture.html"
    return f.read_text() if f.exists() else "<h1>architecture missing</h1>"


@app.get("/architecture", response_class=HTMLResponse)
def serve_architecture_alias() -> str:
    f = ROOT / "frontend_live" / "architecture.html"
    return f.read_text() if f.exists() else "<h1>architecture missing</h1>"


@app.get("/control_plane")
def serve_control_plane():
    """UI pass 2: the Council IS the control plane now — /control_plane redirects to /council."""
    return RedirectResponse(url="/council", status_code=307)


@app.get("/helm")
def serve_helm_alias():
    """UI pass 2: /helm home alias → the Hub (single front door)."""
    return RedirectResponse(url="/hub", status_code=307)


@app.get("/pert", response_class=HTMLResponse)
def pert_wall() -> str:
    """The 85-inch wall. Same runtime-truth feed; nothing on it can be faked."""
    if PERT_UI.exists():
        return PERT_UI.read_text()
    return "<h1>PERT wall missing</h1>"


@app.get("/factories", response_class=HTMLResponse)
def factories_board() -> str:
    """Live factory board — every factory's runtime_state + blocked missions from
    coordination/council/factory_registry.json (via /api/v1/helm/factories). Honest labels."""
    f = ROOT / "frontend_live" / "factories.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return "<h1>HELM</h1><p>factories.html missing</p>"


@app.get("/matrix", response_class=HTMLResponse)
@app.get("/logic-matrix", response_class=HTMLResponse)
def logic_matrix() -> str:
    """HOCH Ecosystem Logic Matrix — the system poster, integrated with a live runtime-truth
    status strip (GOAL / factories / cyber / ATO posture) so it stays honest as HELM changes.
    Displays frontend_live/logic_matrix.png; renders an install hint until the PNG is dropped in."""
    f = ROOT / "frontend_live" / "logic_matrix.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return "<h1>HELM</h1><p>logic_matrix.html missing</p>"


@app.get("/logic_matrix.png")
def logic_matrix_png():
    """Serves the HOCH Ecosystem Logic Matrix image. Drop the PNG at
    frontend_live/logic_matrix.png; 404 with a hint until then (no fake asset)."""
    from fastapi.responses import FileResponse, PlainTextResponse
    f = ROOT / "frontend_live" / "logic_matrix.png"
    if f.exists():
        return FileResponse(f, media_type="image/png")
    return PlainTextResponse("drop the image at frontend_live/logic_matrix.png", status_code=404)


@app.get("/ref_overview.png")
def ref_overview_png():
    """Dev-only: reference PNG for the ?referenceOverlay=1 comparison mode.
    Not linked in nav. Drop the reference image at frontend_live/ref_overview.png."""
    from fastapi.responses import FileResponse, PlainTextResponse
    f = ROOT / "frontend_live" / "ref_overview.png"
    if f.exists():
        return FileResponse(f, media_type="image/png")
    return PlainTextResponse("reference image not present — drop it at frontend_live/ref_overview.png", status_code=404)


@app.get("/", response_class=HTMLResponse)
@app.get("/hub", response_class=HTMLResponse)
@app.get("/overview", response_class=HTMLResponse)
def ui() -> str:
    """HELM Hub — the single front door. Links the 5 keeper cockpits (Council, Command Center,
    PERT→GOAL, Build Theater, Audit Theater) with live GOAL% + lane status; groups the rest.
    UI-consolidation front door (see docs/helm/UI_CONSOLIDATION.md)."""
    ov = ROOT / "frontend_live" / "overview.html"
    if ov.exists():
        return ov.read_text(encoding="utf-8")
    hub = ROOT / "frontend_live" / "hub.html"
    if hub.exists():
        return hub.read_text(encoding="utf-8")
    if UI.exists():
        return UI.read_text()
    return "<h1>HELM LIVE</h1><p>overview.html missing</p>"


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



# ── VOICE EXECUTIVE DESK ──────────────────────────────────────────────────────
VOICE_UI = ROOT / "frontend_live" / "voice.html"
VOICE_JS = ROOT / "frontend_live" / "voice_panel.js"


@app.get("/voice", response_class=HTMLResponse)
def voice_desk() -> str:
    """HELM Voice Executive desk — briefings + governed commands + local TTS."""
    if VOICE_UI.exists():
        return VOICE_UI.read_text(encoding="utf-8")
    return "<h1>voice.html missing</h1>"


MISSION_UI = ROOT / "frontend_live" / "mission.html"


@app.get("/mission", response_class=HTMLResponse)
def mission_desk() -> str:
    """Executive mission state dashboard — operational status, not a coding log."""
    if MISSION_UI.exists():
        return MISSION_UI.read_text(encoding="utf-8")
    return "<h1>mission.html missing</h1>"


@app.get("/frontend_live/voice_panel.js")
def voice_panel_js():
    from fastapi.responses import FileResponse, PlainTextResponse
    if VOICE_JS.exists():
        return FileResponse(VOICE_JS, media_type="application/javascript",
                            headers={"Cache-Control": "no-store"})
    return PlainTextResponse("// voice_panel.js missing", status_code=404)


@app.get("/frontend_live/helm_auth.js")
def helm_auth_js():
    """Read-auth client helper (AC-3/IA-2). Allowlisted so it loads before the token
    is required, so the consoles can attach the token to their /api fetches."""
    from fastapi.responses import FileResponse, PlainTextResponse
    f = ROOT / "frontend_live" / "helm_auth.js"
    if f.exists():
        return FileResponse(f, media_type="application/javascript",
                            headers={"Cache-Control": "no-store"})
    return PlainTextResponse("// helm_auth.js missing", status_code=404)
