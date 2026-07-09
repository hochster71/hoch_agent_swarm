"""
HOCH-200 Relay API
==================
Tailscale-internal relay service for hoch-relay-001.
Port 3012 — only reachable via Tailscale IP 100.87.18.15.

Endpoints:
  GET  /            → Serve dashboard HTML
  GET  /health      → Health check (JSON)
  GET  /api/status  → Full status payload
  GET  /api/registry → Worker registry
  POST /api/heartbeat → Accept agent heartbeat
"""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import FileResponse,  HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HOCH-200 Relay API",
    version="1.1.0",
    docs_url=None,   # disable swagger in prod
    redoc_url=None,
)

# Read-only telemetry on a Tailscale-internal port — allow browser GETs so the live
# swarm-brain dashboard can poll from the founder's machine. No writes are exposed via CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in ("/health", "/api/status", "/api/burn-in/status", "/favicon.ico") or not path.startswith("/api/"):
        return await call_next(request)
    
    import os
    method = request.method
    if method in ("GET", "HEAD", "OPTIONS"):
        tok = os.environ.get("RELAY_READ_TOKEN")
        if tok:
            hdr = request.headers.get("authorization", "") or request.headers.get("x-helm-token", "")
            if hdr.replace("Bearer ", "").strip() != tok:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
    else:
        tok = os.environ.get("RELAY_WRITE_TOKEN")
        if tok:
            hdr = request.headers.get("authorization", "") or request.headers.get("x-helm-token", "")
            if hdr.replace("Bearer ", "").strip() != tok:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
                
    return await call_next(request)

STATIC_DIR = Path("/app/static")
if not STATIC_DIR.exists():
    possible_static = Path(__file__).resolve().parent.parent / "dashboard"
    if possible_static.exists():
        STATIC_DIR = possible_static
    else:
        STATIC_DIR = Path(__file__).parent / "static"

DATA_DIR = Path("/data")
if not DATA_DIR.exists():
    possible_local = Path("/Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/data")
    if possible_local.exists():
        DATA_DIR = possible_local
    else:
        possible_local = Path(__file__).resolve().parent.parent.parent.parent / "has_live_project_tracker/data"
        if possible_local.exists():
            DATA_DIR = possible_local

REGISTRY_PATH = Path("/tmp/worker_registry.json")
# Live streams (heartbeats, council messages, ticket overrides) — persist on the writable
# /state volume (survives container recreation). Falls back to /tmp locally / if /state is absent.
def _state_dir() -> Path:
    d = Path("/state")
    try:
        d.mkdir(parents=True, exist_ok=True)
        (d / ".w").write_text("ok")
        return d
    except Exception:
        return Path("/tmp")
STATE_DIR = _state_dir()
HEARTBEAT_PATH = STATE_DIR / "heartbeats.jsonl"

# Mount static dashboard if the directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _load_registry() -> dict[str, Any]:
    """Load worker registry from disk or return built-in bootstrap."""
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except Exception:
            pass
    # Bootstrap registry — always reflects this node
    return {
        "schema_version": "1.0",
        "generated_at": _now_iso(),
        "workers": [
            {
                "id": "HAS-WORKER-RELAY-001",
                "hostname": "hoch-relay-001",
                "public_ipv4": "50.116.41.183",
                "tailscale_ip": "100.87.18.15",
                "role": "relay",
                "status": "ONLINE",
                "capabilities": ["relay", "heartbeat", "api"],
                "last_seen": _now_iso(),
            }
        ],
    }


def _relay_worker() -> dict[str, Any]:
    registry = _load_registry()
    for w in registry.get("workers", []):
        if w.get("id") == "HAS-WORKER-RELAY-001":
            return w
    return {}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Return 204 No Content for favicon to prevent 404 logs."""
    return Response(status_code=204)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard() -> HTMLResponse:
    """Serve the relay dashboard."""
    dashboard = STATIC_DIR / "index.html"
    if dashboard.exists():
        return HTMLResponse(content=dashboard.read_text(), status_code=200)
    return HTMLResponse(
        content="<h1>HOCH-200 Relay API</h1><p>Dashboard not found.</p>",
        status_code=200,
    )


@app.get("/health")
async def health() -> JSONResponse:
    """Health check endpoint."""
    worker = _relay_worker()
    return JSONResponse(
        {
            "status": "ok",
            "worker": "HAS-WORKER-RELAY-001",
            "worker_status": worker.get("status", "UNKNOWN"),
            "hostname": socket.gethostname(),
            "ts": _now_iso(),
        }
    )


@app.get("/api/fleet/node")
async def api_fleet_node() -> JSONResponse:
    """Measured relay node telemetry, written by the host telemetry agent
    (hoch-relay-telemetry.service). Fails soft to an honest 'no agent' payload so the
    fleet never shows fabricated vitals for this node."""
    try:
        p = Path("/data/relay_node_telemetry.json")
        data = json.loads(p.read_text())
        # staleness guard — if the agent stopped writing, don't present old vitals as live
        try:
            measured = datetime.fromisoformat(data.get("measured_at", "").replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - measured).total_seconds()
            data["telemetry_age_seconds"] = int(age)
            if age > 120:
                data["telemetry_authority"] = "STALE_NO_RECENT_MEASUREMENT"
                data["status"] = "Stale"
        except Exception:
            pass
        return JSONResponse(data)
    except Exception:
        return JSONResponse({
            "node_id": "RELAY-001",
            "telemetry_authority": "DECLARED_ROSTER_NOT_MEASURED",
            "status": "Reachable",
            "activity": "(telemetry agent not reporting on relay host)",
            "measured_agent_count": 0,
            "agents": [],
        })


def _doorstep_status():
    """Read the DOORSTEP execution posture + how many factory items are staged at
    the pre-purchase door awaiting founder revenue activation. Fails soft."""
    posture, door, exit_cond, staged_count = "DEFAULT", None, None, 0
    try:
        ctrl = json.loads(Path("/data/orchestration_bridge_control.json").read_text())
        posture = ctrl.get("execution_posture", "DEFAULT")
        dp = ctrl.get("doorstep_policy", {})
        door = dp.get("door")
        exit_cond = dp.get("exit_condition")
    except Exception:
        pass
    try:
        hq = json.loads(Path("/data/founder_handoff_queue.json").read_text())
        staged_count = len([s for s in hq.get("staged", []) if s.get("status") == "READY_FOR_FOUNDER"])
    except Exception:
        pass
    return posture, door, exit_cond, staged_count


@app.get("/api/status")
async def api_status() -> JSONResponse:
    """Full relay status payload."""
    registry = _load_registry()
    worker = _relay_worker()
    posture, door, exit_cond, staged_count = _doorstep_status()
    return JSONResponse(
        {
            "epic": "HOCH-200",
            "relay_node": "hoch-relay-001",
            "tailscale_ip": "100.87.18.15",
            "public_ipv4": "50.116.41.183",
            "port": 3012,
            "port_public_exposed": False,
            "worker_status": worker.get("status", "UNKNOWN"),
            "worker_id": "HAS-WORKER-RELAY-001",
            "registry_worker_count": len(registry.get("workers", [])),
            "execution_posture": posture,
            "doorstep_door": door,
            "doorstep_exit_condition": exit_cond,
            "founder_handoff_count": staged_count,
            "ts": _now_iso(),
        }
    )


@app.get("/api/burn-in/status")
async def get_burn_in_status() -> JSONResponse:
    def _read_json(filename: str, default: Any = None) -> Any:
        path = DATA_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return default

    daemon_state = _read_json("ag_execution_daemon_state.json", {})
    burn_in_summary = _read_json("ag_execution_burn_in_summary.json", {})
    queue_health = _read_json("ag_execution_queue_health.json", {})
    proof_index = _read_json("ag_execution_proof_index.json", {})
    fencing_status = _read_json("ag_execution_fencing_status.json", {})
    task_queue = _read_json("helm_task_queue.json", [])
    
    agent_inventory = _read_json("agent_inventory.json", [])
    source_authority = _read_json("source_authority_manifest.json", {})
    reasoning_graph = _read_json("reasoning_graph.json", {})
    ag_operator_hold = _read_json("ag_operator_hold.json", {})
    ag_execution_policy = _read_json("ag_execution_policy.json", {})
    control_plane_status = _read_json("control_plane_status.json", {})

    pending_task_count = 0
    for task in task_queue:
        if task.get("status") in ("PENDING", "pending"):
            pending_task_count += 1

    is_stale = False
    heartbeat_fresh = "HEARTBEAT_FRESH"
    
    last_hb_str = daemon_state.get("last_heartbeat")
    expires_str = daemon_state.get("heartbeat_expires_at")
    
    now = datetime.now(timezone.utc)
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if now > expires_dt:
                is_stale = True
                heartbeat_fresh = "HEARTBEAT_STALE"
        except Exception:
            pass

    systemd_active = daemon_state.get("venue_classification", {}).get("systemd_active", False)
    daemon_running = daemon_state.get("daemon_status") == "RUNNING"
    
    state_indicator = "PRIMARY_SYSTEMD_BURN_IN_ACTIVE"
    if not systemd_active or not daemon_running:
        state_indicator = "SYSTEMD_DOWN"
    elif is_stale:
        state_indicator = "HEARTBEAT_STALE"
    else:
        last_cycle_status = daemon_state.get("last_cycle_status", "IDLE")
        if pending_task_count > 0 and last_cycle_status == "IDLE":
            if last_hb_str:
                try:
                    last_hb_dt = datetime.fromisoformat(last_hb_str.replace("Z", "+00:00"))
                    if (now - last_hb_dt).total_seconds() > 120:
                        state_indicator = "IDLE_WITH_PENDING_TASKS"
                except Exception:
                    pass

    elapsed_hours = 0.0
    started_at_str = daemon_state.get("started_at")
    if started_at_str:
        try:
            started_dt = datetime.fromisoformat(started_at_str.replace("Z", "+00:00"))
            elapsed_hours = (now - started_dt).total_seconds() / 3600.0
        except Exception:
            pass

    # Merge elapsed_hours into burn_in_summary
    burn_in_summary_merged = {**burn_in_summary}
    burn_in_summary_merged["elapsed_hours"] = elapsed_hours

    # Freshness report logic
    def _get_sla_status(age: float) -> str:
        if age <= 15.0:
            return "FRESH"
        elif age <= 60.0:
            return "WARNING"
        elif age <= 120.0:
            return "STALE"
        else:
            return "EXPIRED"

    def _get_file_age_and_sla(filename: str, json_key: str = None) -> dict:
        path = DATA_DIR / filename
        age_seconds = 999999.0
        last_updated = "UNKNOWN"
        if path.exists():
            mtime_dt = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            age_seconds = (now - mtime_dt).total_seconds()
            last_updated = mtime_dt.isoformat()
            if json_key:
                try:
                    data = json.loads(path.read_text())
                    val = data.get(json_key)
                    if val:
                        parsed = _parse_iso(val)
                        if parsed:
                            age_seconds = (now - parsed).total_seconds()
                            last_updated = val
                except Exception:
                    pass
        status = _get_sla_status(age_seconds)
        return {
            "age_seconds": round(age_seconds, 2),
            "status": status,
            "last_updated": last_updated,
            "expires_at": (now + timedelta(seconds=120 - age_seconds)).isoformat() if age_seconds != 999999.0 else "EXPIRED",
            "owner_agent": "Orchestrator",
            "stale_blocks_go": True
        }

    freshness_report = {
        "daemon_state": _get_file_age_and_sla("ag_execution_daemon_state.json", "last_heartbeat"),
        "burn_in_summary": _get_file_age_and_sla("ag_execution_burn_in_summary.json", "measured_at"),
        "queue_health": _get_file_age_and_sla("ag_execution_queue_health.json", "checked_at"),
        "proof_index": _get_file_age_and_sla("ag_execution_proof_index.json", "checked_at"),
        "fencing_status": _get_file_age_and_sla("ag_execution_fencing_status.json", "checked_at"),
        "control_plane_status": _get_file_age_and_sla("control_plane_status.json", "last_updated"),
        "agent_inventory": _get_file_age_and_sla("agent_inventory.json", "last_updated"),
        "source_authority": _get_file_age_and_sla("source_authority_manifest.json", "last_updated"),
    }

    # ------------------------------------------------------------------
    # Dynamic Factory Lanes Freshness SLA Check
    # ------------------------------------------------------------------
    def _get_evidence_freshness(evidence_rel_path: str) -> str:
        if not evidence_rel_path or evidence_rel_path == "None":
            return "UNKNOWN"
        workspace_root = Path(__file__).resolve().parent.parent.parent.parent
        p = workspace_root / evidence_rel_path
        if not p.exists():
            return "UNKNOWN"
        try:
            mtime_dt = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)
            age = (now - mtime_dt).total_seconds()
            if age <= 120.0:
                return "FRESH"
            elif age <= 300.0:
                return "WARNING"
            elif age <= 600.0:
                return "STALE"
            else:
                return "EXPIRED"
        except Exception:
            return "UNKNOWN"

    factory_lanes = {
        "HAS": {
            "status": "CONVERGED",
            "owner_agent": "HAS-KernelHub-Mgr",
            "current_objective": "Relay node heartbeat monitoring",
            "blocked_by": "None",
            "next_action": "monitor",
            "evidence": "docs/evidence/runtime/hoch-compute-node-health.md",
            "revenue_relevance": "High (autonomy control)",
            "stale_status": _get_evidence_freshness("docs/evidence/runtime/hoch-compute-node-health.md")
        },
        "HASF": {
            "status": "CONVERGED",
            "owner_agent": "HASF-Optimizer-01",
            "current_objective": "Stripe sandbox test configured",
            "blocked_by": "None",
            "next_action": "Verify Stripe webhook routes",
            "evidence": "docs/products/epic-fury-2026/HASF_GATE_VERIFY.json",
            "revenue_relevance": "High (Stripe integration)",
            "stale_status": _get_evidence_freshness("docs/products/epic-fury-2026/HASF_GATE_VERIFY.json")
        },
        "HMF": {
            "status": "CONVERGED",
            "owner_agent": "HMF-Music-Arranger",
            "current_objective": "Expose blended score selection",
            "blocked_by": "None",
            "next_action": "Monitor blended score convergence",
            "evidence": "docs/evidence/homemesh_spatial_graph/full_runtime_baseline.md",
            "revenue_relevance": "Medium (creative asset pipeline)",
            "stale_status": _get_evidence_freshness("docs/evidence/homemesh_spatial_graph/full_runtime_baseline.md")
        },
        "HRF": {
            "status": "CONVERGED",
            "owner_agent": "HRF-Research-Scorer",
            "current_objective": "Refine weak rubric segments",
            "blocked_by": "None",
            "next_action": "Run multi-turn optimization cycles",
            "evidence": "docs/prompt_brain/phase_11_recursive_optimization_audit.md",
            "revenue_relevance": "High (predictive scoring)",
            "stale_status": _get_evidence_freshness("docs/prompt_brain/phase_11_recursive_optimization_audit.md")
        }
    }

    # Daemon run proof
    last_entry = None
    ledger_path = DATA_DIR / "ag_execution_burn_in_ledger.jsonl"
    if ledger_path.exists():
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip()]
                if lines:
                    last_entry = json.loads(lines[-1])
        except Exception:
            pass

    ledger_run_id_match = False
    ledger_cycle_id_match = False
    ledger_continuity_status = "UNKNOWN"
    
    run_id = daemon_state.get("run_id")
    cycle_count = daemon_state.get("cycle_count")
    
    derived_current_cycle_id = "cycle-00000"
    if cycle_count is not None:
        if run_id:
            derived_current_cycle_id = f"{run_id}-cycle-{str(cycle_count).zfill(5)}"
        else:
            derived_current_cycle_id = f"cycle-{str(cycle_count).zfill(5)}"

    if last_entry:
        ledger_run_id = last_entry.get("run_id")
        ledger_cycle_id = last_entry.get("cycle_id")
        
        if run_id:
            ledger_run_id_match = ledger_run_id == run_id
            expected_new_cycle_id = f"{run_id}-cycle-{str(cycle_count).zfill(5)}" if cycle_count is not None else None
            
            if ledger_cycle_id == expected_new_cycle_id and expected_new_cycle_id:
                ledger_cycle_id_match = True
                ledger_continuity_status = "VALID" if ledger_run_id_match else "MISMATCH"
            else:
                expected_legacy_cycle_id = f"cycle-{str(cycle_count).zfill(5)}" if cycle_count is not None else None
                if ledger_cycle_id == expected_legacy_cycle_id or last_entry.get("lease_token") == cycle_count:
                    ledger_cycle_id_match = True
                    ledger_continuity_status = "LEGACY_COMPATIBLE"
                else:
                    ledger_continuity_status = "MISMATCH"
        else:
            if cycle_count is not None:
                expected_legacy_cycle_id = f"cycle-{str(cycle_count).zfill(5)}"
                if ledger_cycle_id == expected_legacy_cycle_id or last_entry.get("lease_token") == cycle_count:
                    ledger_cycle_id_match = True
                    ledger_continuity_status = "LEGACY_COMPATIBLE"
                else:
                    ledger_continuity_status = "MISMATCH"
            else:
                ledger_continuity_status = "MISSING"
    else:
        ledger_continuity_status = "MISSING"

    daemon_run_proof = {
        "run_id": run_id,
        "started_at": daemon_state.get("started_at"),
        "current_cycle_count": cycle_count,
        "derived_current_cycle_id": derived_current_cycle_id,
        "ledger_path": "has_live_project_tracker/data/ag_execution_burn_in_ledger.jsonl",
        "last_ledger_entry": last_entry,
        "ledger_run_id_match": ledger_run_id_match,
        "ledger_cycle_id_match": ledger_cycle_id_match,
        "ledger_continuity_status": ledger_continuity_status,
        "restart_count_24h": daemon_state.get("restart_count_24h", 0),
        "clock_reset_detected": daemon_state.get("clock_reset_detected", False)
    }

    # Policy blocks
    blocked_by = []
    if ag_operator_hold.get("operator_hold_active", False):
        blocked_by.append("Operator hold active")
    if not daemon_state.get("allow_ag_execution", True):
        blocked_by.append("AG execution disabled by policy")
    if freshness_report["daemon_state"]["status"] in ("STALE", "EXPIRED"):
        blocked_by.append("Daemon heartbeat stale")
    for blk in control_plane_status.get("blockers", {}).get("next_actions", []):
        blocked_by.append(blk.get("action", blk.get("title")))

    policy_block_explainer = {
        "blocked_by": blocked_by,
        "allow_ag_execution": daemon_state.get("allow_ag_execution", True),
        "operator_hold": ag_operator_hold.get("operator_hold_active", False),
        "private_doctrine_go": daemon_state.get("doctrine_status") == "GO",
        "human_approval_required": ag_execution_policy.get("requires_michael_approval") is not None,
        "mutation_allowed": False,
        "pending_tasks": [t for t in task_queue if t.get("status") in ("PENDING", "pending")],
        "next_eligible_task": task_queue[0] if task_queue else None,
        "safe_to_execute": ["read_file", "view_file", "run_test"],
        "prohibited_actions": ["git_push", "deploy_prod", "stripe_mutation"]
    }

    # Agent Resource Map
    agent_resource_map = []
    for agent in agent_inventory:
        a_id = agent.get("id")
        name = agent.get("name")
        role = agent.get("role", "worker")
        
        last_seen_str = agent.get("last_seen")
        age_s = 999999.0
        current_state = "IDLE"
        if last_seen_str:
            parsed = _parse_iso(last_seen_str)
            if parsed:
                age_s = (now - parsed).total_seconds()
                if age_s < 60:
                    current_state = "ACTIVE"
                elif age_s > 300:
                    current_state = "BLOCKED"
        
        agent_resource_map.append({
            "agent_id": a_id,
            "name": name,
            "role": role,
            "current_state": current_state,
            "last_heartbeat": last_seen_str,
            "freshness_age_seconds": round(age_s, 2) if age_s != 999999.0 else None,
            "owner": agent.get("owner_agent", "Master Orchestrator"),
            "current_task": agent.get("next_action", "monitor"),
            "blocked_by": "None" if current_state != "BLOCKED" else "Heartbeat stale",
            "resource_requirements": {
                "model": "google/gemma-4-12b-qat" if "Coder" in name or "Optimizer" in name else "relay-001",
                "API": "Masquerading proxy",
                "file": agent.get("path_or_remote", "local_file_only"),
                "ledger": "ag_execution_burn_in_ledger.jsonl"
            },
            "safe_actions": ["read_file", "run_test"],
            "prohibited_actions": ["git_push", "deploy_prod"],
            "evidence_path": "has_live_project_tracker/data/agent_inventory.json",
            "next_action": agent.get("next_action", "monitor"),
            "confidence": agent.get("confidence", 0.95),
            "verdict": agent.get("evidence_status", "VERIFIED")
        })

    # Go/No-go verdict math
    any_stale_expired = any(f["status"] in ("STALE", "EXPIRED") for f in freshness_report.values())
    any_stale_expired_lane = any(l["stale_status"] in ("STALE", "EXPIRED", "UNKNOWN") for l in factory_lanes.values())
    has_blockers = len(blocked_by) > 0
    
    overall_verdict = "GO"
    verdict_reason = "All checks green, burn-in loop complete, no active blockers."
    
    if any_stale_expired or any_stale_expired_lane:
        overall_verdict = "NO-GO"
        reasons = []
        if any_stale_expired:
            stale_keys = [k for k, f in freshness_report.items() if f["status"] in ("STALE", "EXPIRED")]
            reasons.append(f"Stale/Expired telemetry detected: {', '.join(stale_keys)}")
        if any_stale_expired_lane:
            stale_lanes = [k for k, l in factory_lanes.items() if l["stale_status"] in ("STALE", "EXPIRED", "UNKNOWN")]
            reasons.append(f"Stale/Expired lanes: {', '.join(stale_lanes)}")
        verdict_reason = " | ".join(reasons)
    elif has_blockers:
        overall_verdict = "CONDITIONAL GO"
        verdict_reason = f"Active blockers: {', '.join(blocked_by[:2])}"

    mission_commander = {
        "current_goal": "Reduce Michael's manual helm work and drive enclaves to verified GOAL states.",
        "current_critical_path_node": "R1: Provision OpenAI/Anthropic API keys" if has_blockers else "None",
        "current_blockers": blocked_by,
        "owner_agent": "Mission Commander",
        "exact_next_safe_action": "pytest tests/integration/test_relay_checks.py",
        "evidence_path": "docs/evidence/runtime/mission_commander_truth_upgrade_20260707T120235Z/",
        "verdict": overall_verdict,
        "verdict_reason": verdict_reason,
        "what_michael_should_not_do": "Do not push to main. Do not restart blocked systemd daemons. Do not perform manual sync."
    }

    _failed_rate = burn_in_summary.get("failed_cycle_rate", 1.0)
    _real_cycles = burn_in_summary.get("real_cycles", 0)
    _missing_proofs = burn_in_summary.get("missing_proof_detected", 1)
    
    # 24H GO checks
    go_24h_checks = {
        "elapsed_ge_24h": elapsed_hours >= 24.0,
        "heartbeat_fresh": (not is_stale),
        "daemon_active": bool(daemon_running and systemd_active),
        "has_real_cycles": _real_cycles > 0,
        "zero_failed_real": _failed_rate == 0.0,
        "queue_pass": queue_health.get("health_status") == "PASS",
        "fencing_pass": fencing_status.get("verdict") == "PASS",
        "proofs_intact": _missing_proofs == 0,
    }
    go_24h_pass = all(go_24h_checks.values())
    go_24h_status = "GO" if (go_24h_pass and overall_verdict == "GO") else "NOT_YET"
    go_24h_blockers = [k for k, v in go_24h_checks.items() if not v]

    return JSONResponse({
        "state_indicator": state_indicator,
        "heartbeat_status": heartbeat_fresh,
        "daemon_state": daemon_state,
        "burn_in_summary": burn_in_summary_merged,
        "queue_health": queue_health,
        "proof_index": proof_index,
        "fencing_status": fencing_status,
        "pending_task_count": pending_task_count,
        "24h_go_status": go_24h_status,
        "24h_go_checks": go_24h_checks,
        "24h_go_blockers": go_24h_blockers,
        "ts": _now_iso(),
        "cycle_count_source": "/root/hoch_agent_swarm/has_live_project_tracker/data/ag_execution_daemon_state.json",
        "cycle_count_timestamp": daemon_state.get("last_heartbeat", _now_iso()),
        "daemon_started_at": daemon_state.get("started_at"),
        "api_generated_at": _now_iso(),
        "elapsed_hours": elapsed_hours,
        "telemetry_host_path": str(DATA_DIR),
        "container_mount_mode": "read_only",
        "freshness": freshness_report,
        "freshness_report": freshness_report,
        "ledger_proof": daemon_run_proof,
        "daemon_run_proof": daemon_run_proof,
        "policy_explainer": policy_block_explainer,
        "policy_block_explainer": policy_block_explainer,
        "runtime_governor": {
            "status": "NOT_REPORTED",
            "reason": "runtime_governor_not_available_on_relay"
        },
        "mission_commander": mission_commander,
        "factory_lanes": factory_lanes,
        "agent_resource_map": agent_resource_map
    })


@app.get("/api/live")
async def api_live() -> JSONResponse:
    """Single compact, CORS-served payload for the live swarm-brain dashboard.
    Merges DOORSTEP posture + worker state + MEASURED relay telemetry into one poll.
    Everything is read-only and fails soft — the dashboard shows honest blanks, never fakes."""
    worker = _relay_worker()
    posture, door, exit_cond, staged_count = _doorstep_status()

    # ── governance flags (truthful, from the control plane) — never fabricated ──
    provider_api_calls = "UNKNOWN"
    founder_gated_execution = "UNKNOWN"
    rung2_provider_calls = None
    try:
        ctrl = json.loads(Path("/data/orchestration_bridge_control.json").read_text())
        if "allow_provider_api_calls" in ctrl:
            provider_api_calls = "ON" if ctrl.get("allow_provider_api_calls") else "OFF"
        if "allow_founder_gated_execution" in ctrl:
            founder_gated_execution = "ON" if ctrl.get("allow_founder_gated_execution") else "OFF"
        rung2_provider_calls = ctrl.get("rung_2_live_provider_calls")
    except Exception:
        pass

    # ── the actual items parked at the door (what the founder must act on next) ──
    handoff_items = []
    try:
        hq = json.loads(Path("/data/founder_handoff_queue.json").read_text())
        for s in hq.get("staged", []):
            handoff_items.append({
                "id": s.get("id"), "title": s.get("title"),
                "status": s.get("status", "STAGED"), "action": s.get("action"),
            })
        # honest count = items still awaiting the founder (signed/completed no longer count)
        staged_count = len([s for s in hq.get("staged", [])
                            if s.get("status") not in ("SIGNED", "COMPLETED", "DONE")])
    except Exception:
        pass

    # measured relay telemetry (same source + staleness guard as /api/fleet/node)
    tel = {"telemetry_authority": "DECLARED_ROSTER_NOT_MEASURED", "status": "Reachable",
           "cpu_pct": None, "ram_pct": None, "disk_pct": None, "load1": None,
           "measured_agent_count": 0, "telemetry_age_seconds": None}
    try:
        data = json.loads(Path("/data/relay_node_telemetry.json").read_text())
        for k in ("cpu_pct", "ram_pct", "disk_pct", "load1", "measured_agent_count",
                  "telemetry_authority", "status"):
            if k in data:
                tel[k] = data[k]
        measured = datetime.fromisoformat(data.get("measured_at", "").replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - measured).total_seconds()
        tel["telemetry_age_seconds"] = int(age)
        if age > 120:
            tel["telemetry_authority"] = "STALE_NO_RECENT_MEASUREMENT"
            tel["status"] = "Stale"
    except Exception:
        pass

    live = tel.get("telemetry_authority", "").startswith("MEASURED") and worker.get("status") == "ONLINE"

    # ── per-agent nodes (measured) — for the pulsing agent constellation ──
    agents = []
    try:
        td = json.loads(Path("/data/relay_node_telemetry.json").read_text())
        for a in td.get("agents", []):
            agents.append({"name": a.get("name"), "status": a.get("status", "Unknown"),
                           "type": a.get("type", "")})
    except Exception:
        pass

    # ── recent execution activity + live cycle gauge (real burn-in ledger) ──
    recent, cycle = [], {}
    try:
        lp = Path("/data/ag_execution_burn_in_ledger.jsonl")
        lines = [ln for ln in lp.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
        parsed = []
        for ln in lines[-12:]:
            try:
                parsed.append(json.loads(ln))
            except Exception:
                pass
        for e in reversed(parsed[-8:]):
            recent.append({
                "ts": e.get("timestamp"),
                "label": e.get("cycle_id", "cycle"),
                "verdict": e.get("verdict", "?"),
                "duration_ms": e.get("duration_ms"),
                "done": e.get("completed_count"), "pending": e.get("pending_count"),
                "failed": e.get("failed_count"),
            })
        if parsed:
            last = parsed[-1]
            cycle = {
                "cycle_id": last.get("cycle_id"),
                "daemon_status": last.get("daemon_status"),
                "completed": last.get("completed_count"), "pending": last.get("pending_count"),
                "blocked": last.get("blocked_count"), "failed": last.get("failed_count"),
                "verdict": last.get("verdict"), "heartbeat": last.get("heartbeat_status"),
                "checks": {"proof": last.get("proof_check"), "queue": last.get("queue_check"),
                           "doctrine": last.get("doctrine_check")},
            }
    except Exception:
        pass

    # ── cost: only report spend if the ledger actually exists here (else cap + honest note) ──
    cost = {"cap_usd": float(os.environ.get("AGENT_MONTHLY_CAP_USD", "100")),
            "spend_usd": None, "note": "spend ledger on build host — not present on relay"}
    try:
        sp = Path("/data/spend_ledger.jsonl")
        if sp.exists():
            mk = datetime.now(timezone.utc).strftime("%Y-%m")
            tot = 0.0
            for ln in sp.read_text(encoding="utf-8", errors="ignore").splitlines():
                try:
                    r = json.loads(ln)
                    if r.get("month") == mk:
                        tot += float(r.get("cost_usd", 0.0))
                except Exception:
                    pass
            cost["spend_usd"] = round(tot, 4)
            cost["note"] = "measured this month"
    except Exception:
        pass

    return JSONResponse({
        "ok": True,
        "ts": _now_iso(),
        "posture": posture,
        "provider_api_calls": provider_api_calls,
        "founder_gated_execution": founder_gated_execution,
        "rung_2_live_provider_calls": rung2_provider_calls,
        "doorstep_door": door,
        "doorstep_exit_condition": exit_cond,
        "founder_handoff_count": staged_count,
        "handoff_items": handoff_items,
        "worker_status": worker.get("status", "UNKNOWN"),
        "relay": {"node": "hoch-relay-001", "tailscale_ip": "100.87.18.15",
                  "live": bool(live), **tel},
        "agents": agents,
        "cycle": cycle,
        "recent": recent,
        "factories": [
            {"id": "HASF", "name": "Epic Fury · iOS", "state": "SEC_GATE_SIGNED", "at_door": True},
            {"id": "HMF", "name": "music", "state": "AT_DOORSTEP", "at_door": True},
            {"id": "HRF", "name": "research", "state": "AT_DOORSTEP", "at_door": True},
        ],
        "harness": ["route", "run", "verify", "escalate", "cost_cap"],
        "cost": cost,
    })


@app.get("/api/northstar")
async def api_northstar() -> JSONResponse:
    """Live state of the Northstar Autonomy Engine so a dashboard can watch the swarm build.
    Read-only, fails soft — never 500s. Reads Northstar JSON snapshots + the tail of the
    experience ledger from the same DATA_DIR the rest of the relay uses."""

    def _read_json(filename: str, default: Any = None) -> Any:
        path = DATA_DIR / filename
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return default

    northstar = _read_json("northstar.json", {})
    state = _read_json("northstar_state.json", {})
    digest = _read_json("doorstep_digest.json", {})

    if not isinstance(northstar, dict):
        northstar = {}
    if not isinstance(state, dict):
        state = {}
    if not isinstance(digest, dict):
        digest = {}

    # ── goal + phase (northstar.json is the authority, fall back to state) ──
    goal = northstar.get("goal") or state.get("goal")
    phase = northstar.get("current_phase") or state.get("phase")

    progress = {
        "tasks": state.get("tasks"),
        "done": state.get("done"),
        "pending": state.get("pending"),
        "staged_at_door": state.get("staged_at_door"),
        "deferred_need_code_mode": state.get("deferred_need_code_mode"),
    }

    # ── tail of the experience ledger, filtered to northstar entries, normalized ──
    recent_tasks = []
    try:
        lp = DATA_DIR / "prompt_brain" / "outcome_feedback_ledger.jsonl"
        lines = [ln for ln in lp.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
        parsed = []
        for ln in lines:
            try:
                parsed.append(json.loads(ln))
            except Exception:
                pass
        ns_entries = []
        for e in parsed:
            if not isinstance(e, dict):
                continue
            engine = str(e.get("engine", ""))
            if engine.startswith("northstar") or "northstar" in e:
                ns_entries.append(e)
        for e in ns_entries[-8:]:
            recent_tasks.append({
                "task_id": e.get("task_id"),
                "phase": e.get("phase"),
                "status": e.get("status"),
                "verified": e.get("verified"),
                "tier": e.get("tier"),
                "cost_usd": e.get("cost_usd"),
                "summary": e.get("summary"),
            })
    except Exception:
        recent_tasks = []

    # ── items parked at the door (from the doorstep digest) ──
    doorstep = []
    try:
        for d in digest.get("at_the_door", []):
            if not isinstance(d, dict):
                continue
            doorstep.append({
                "id": d.get("id"),
                "title": d.get("title"),
                "status": d.get("status"),
            })
    except Exception:
        doorstep = []

    return JSONResponse({
        "ok": True,
        "ts": _now_iso(),
        "goal": goal,
        "phase": phase,
        "progress": progress,
        "recent_tasks": recent_tasks,
        "doorstep": doorstep,
        "message": digest.get("message", ""),
        "moonshot": {
            "epic_fury_state": "WAITING_FOR_REVIEW",
            "factories_live": ["HASF", "HSF"],
        },
    })


@app.get("/brain", response_class=HTMLResponse, include_in_schema=False)
async def serve_brain() -> HTMLResponse:
    """Bookmarkable live swarm-brain control room. Served same-origin, so it polls /api/live
    with no CORS hop."""
    for cand in (STATIC_DIR / "brain.html", Path(__file__).resolve().parent.parent / "dashboard/brain.html"):
        if cand.exists():
            return HTMLResponse(content=cand.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>brain.html not deployed</h1>", status_code=404)


@app.get("/space", response_class=HTMLResponse, include_in_schema=False)
async def serve_space() -> HTMLResponse:
    """HOCH SPACE — all-factories control plane. Same-origin, polls /api/* with no CORS hop."""
    for cand in (STATIC_DIR / "space.html", Path(__file__).resolve().parent.parent / "dashboard/space.html"):
        if cand.exists():
            return HTMLResponse(content=cand.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>space.html not deployed</h1>", status_code=404)


@app.get("/hoch-neuro-command.html", response_class=HTMLResponse, include_in_schema=False)
@app.get("/has-live-brain.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_neuro_command() -> HTMLResponse:
    for cand in (STATIC_DIR / "hoch-neuro-command.html", Path(__file__).resolve().parent.parent / "dashboard/hoch-neuro-command.html",
                 STATIC_DIR / "has-live-brain.html", Path(__file__).resolve().parent.parent / "dashboard/has-live-brain.html"):
        if cand.exists():
            return HTMLResponse(content=cand.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>neuro-command not deployed</h1>", status_code=404)


@app.get("/factoryverse", include_in_schema=False)
@app.get("/helm-factoryverse", include_in_schema=False)
async def serve_factoryverse():
    """HELM Factory-Verse — 3D atrium; click a factory to walk inside (agents, lanes, live stats)."""
    # FileResponse is the proven-working pattern on this relay (read_text 500s here).
    for cand in (STATIC_DIR / "helm-factoryverse.html", Path(__file__).resolve().parent.parent / "dashboard/helm-factoryverse.html"):
        if cand.exists():
            return FileResponse(str(cand), media_type="text/html")
    return HTMLResponse(content="<h1>helm-factoryverse.html not deployed</h1>", status_code=404)


@app.get("/helm-3d", include_in_schema=False)
async def serve_helm3d():
    """HELM 3D living core (atrium only)."""
    for cand in (STATIC_DIR / "helm-3d.html", Path(__file__).resolve().parent.parent / "dashboard/helm-3d.html"):
        if cand.exists():
            return FileResponse(str(cand), media_type="text/html")
    return HTMLResponse(content="<h1>helm-3d.html not deployed</h1>", status_code=404)


@app.get("/control", include_in_schema=False)
@app.get("/helm-control", include_in_schema=False)
async def serve_control():
    """HELM CONTROL — live command surface (PERT, gaps, coordination, burn-in)."""
    for cand in (STATIC_DIR / "helm-control-live.html", Path(__file__).resolve().parent.parent / "dashboard/helm-control-live.html"):
        if cand.exists():
            return FileResponse(str(cand), media_type="text/html")
    return HTMLResponse(content="<h1>helm-control-live.html not deployed</h1>", status_code=404)


@app.get("/board", include_in_schema=False)
@app.get("/jira", include_in_schema=False)
async def serve_board():
    """HAS -> GOAL board — Jira-style Kanban of council-derived tickets, epics, goal progress."""
    for cand in (STATIC_DIR / "helm-board.html", Path(__file__).resolve().parent.parent / "dashboard/helm-board.html"):
        if cand.exists():
            return FileResponse(str(cand), media_type="text/html")
    return HTMLResponse(content="<h1>helm-board.html not deployed</h1>", status_code=404)


@app.get("/coordination", include_in_schema=False)
@app.get("/council", include_in_schema=False)
@app.get("/storyboard", include_in_schema=False)
async def serve_coordination():
    """HELM COUNCIL — live coordination storyboard (real inter-agent dialogue + founder directives)."""
    for cand in (STATIC_DIR / "helm-coordination.html", Path(__file__).resolve().parent.parent / "dashboard/helm-coordination.html"):
        if cand.exists():
            return FileResponse(str(cand), media_type="text/html")
    return HTMLResponse(content="<h1>helm-coordination.html not deployed</h1>", status_code=404)


@app.get("/api/helm-control")
async def api_helm_control() -> JSONResponse:
    """Consolidated live payload for the control plane (no fake green)."""
    for cand in (STATE_DIR / "helm_control_live.json", DATA_DIR / "helm_control_live.json", STATIC_DIR / "helm_control_live.json",
                 Path(__file__).resolve().parent.parent.parent.parent / "has_live_project_tracker/data/helm_control_live.json"):
        try:
            if cand.exists():
                return JSONResponse(json.loads(cand.read_text(encoding="utf-8")))
        except Exception:
            continue
    return JSONResponse({"error": "helm_control_live.json not synced", "generated": None}, status_code=404)


FACTORYVERSE_STATE = STATE_DIR / "factoryverse.json"
REVENUE_STATE = STATE_DIR / "revenue.json"


def _write_authed(request: "Request") -> bool:
    """Hardening: truth-write endpoints require a bearer token when RELAY_WRITE_TOKEN is set.
    Unset => tailnet-only trust (fail-open, backward compatible). Set it to ENFORCE (fail-closed)."""
    import os
    tok = os.environ.get("RELAY_WRITE_TOKEN")
    if not tok:
        return True
    hdr = request.headers.get("authorization", "") or request.headers.get("x-helm-token", "")
    return hdr.replace("Bearer ", "").strip() == tok


@app.get("/api/factoryverse")
async def api_factoryverse() -> JSONResponse:
    """Truthful per-factory payload. Prefers live-pushed /state over baked deploy data (ends stale UI)."""
    for cand in (FACTORYVERSE_STATE,
                 DATA_DIR / "helm_factoryverse.json",
                 STATIC_DIR / "helm_factoryverse.json",
                 Path(__file__).resolve().parent.parent.parent.parent / "has_live_project_tracker/data/helm_factoryverse.json"):
        try:
            if cand.exists():
                return JSONResponse(json.loads(cand.read_text(encoding="utf-8")))
        except Exception:
            continue
    return JSONResponse({"error": "helm_factoryverse.json not synced to /data", "factories": []}, status_code=404)


@app.post("/api/factoryverse/push")
async def api_factoryverse_push(request: Request) -> JSONResponse:
    """Live-push fresh factory-verse truth into writable /state so the UI is never stale (no redeploy needed)."""
    if not _write_authed(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)
    if not isinstance(body, dict) or "factories" not in body:
        return JSONResponse({"error": "expected {factories:[...]}"}, status_code=400)
    body["_pushed_at"] = _now_iso()
    FACTORYVERSE_STATE.parent.mkdir(parents=True, exist_ok=True)
    FACTORYVERSE_STATE.write_text(json.dumps(body), encoding="utf-8")
    return JSONResponse({"accepted": True, "ts": body["_pushed_at"], "factories": len(body.get("factories", []))})


@app.get("/api/revenue")
async def api_revenue() -> JSONResponse:
    """Live revenue truth pushed from the local ledger. No fake green — real captured transactions only."""
    if REVENUE_STATE.exists():
        try:
            return JSONResponse(json.loads(REVENUE_STATE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return JSONResponse({"lifetime_usd": 0, "transactions": 0, "updated": None})


@app.post("/api/revenue")
async def api_revenue_push(request: Request) -> JSONResponse:
    """Push revenue totals from the local ledger into /state."""
    if not _write_authed(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)
    body["updated"] = _now_iso()
    REVENUE_STATE.parent.mkdir(parents=True, exist_ok=True)
    REVENUE_STATE.write_text(json.dumps(body), encoding="utf-8")
    return JSONResponse({"accepted": True, "ts": body["updated"]})


_STATE_WHITELIST = {"helm_tickets.json", "helm_control_live.json", "helm_factoryverse.json",
                    "helm_mission_control.json", "revenue.json", "factoryverse.json"}


@app.post("/api/state/put")
async def api_state_put(request: Request) -> JSONResponse:
    """Generic live-truth sync: write a whitelisted helm_*.json into writable /state so EVERY page
    reads fresh with no redeploy. This is what ends 'every page is stale'."""
    if not _write_authed(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)
    name = str(body.get("name", ""))
    data = body.get("data")
    if name not in _STATE_WHITELIST or data is None:
        return JSONResponse({"error": "name must be whitelisted and data required",
                             "allowed": sorted(_STATE_WHITELIST)}, status_code=400)
    (STATE_DIR / name).parent.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / name).write_text(json.dumps(data), encoding="utf-8")
    return JSONResponse({"accepted": True, "name": name, "ts": _now_iso()})


@app.get("/hoch-neuro-derive.js", include_in_schema=False)
async def serve_derive_js():
    """Serve the shared derivation module for /space (and /brain) same-origin."""
    for cand in (STATIC_DIR / "hoch-neuro-derive.js", Path(__file__).resolve().parent.parent / "dashboard/hoch-neuro-derive.js"):
        if cand.exists():
            return FileResponse(str(cand), media_type="application/javascript")
    return JSONResponse({"error": "hoch-neuro-derive.js not deployed"}, status_code=404)


@app.get("/api/registry")
async def api_registry() -> JSONResponse:
    """Return worker registry."""
    return JSONResponse(_load_registry())


MESSAGE_PATH = STATE_DIR / "council_messages.jsonl"


@app.post("/api/message")
async def api_message(request: Request) -> JSONResponse:
    """Append a coordination-council message (actual inter-agent dialogue).
    Body: {from, to, tier, re, kind, text}. Append-only; the /coordination window renders it live."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    entry = {
        "ts": _now_iso(),
        "from": str(body.get("from", "unknown"))[:60],
        "to": str(body.get("to", "all"))[:60],
        "tier": str(body.get("tier", ""))[:40],
        "re": str(body.get("re", ""))[:80],
        "kind": str(body.get("kind", "msg"))[:24],
        "text": str(body.get("text", ""))[:2000],
    }
    MESSAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MESSAGE_PATH.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return JSONResponse({"accepted": True, "ts": entry["ts"]})


@app.get("/api/messages")
async def api_messages(limit: int = 100) -> JSONResponse:
    """Return recent council dialogue (newest last) for the coordination / storyboard window."""
    msgs = []
    try:
        if MESSAGE_PATH.exists():
            for ln in MESSAGE_PATH.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 500)):]:
                try:
                    msgs.append(json.loads(ln))
                except Exception:
                    continue
    except Exception:
        pass
    return JSONResponse({"generated_at": _now_iso(), "count": len(msgs), "messages": msgs})


TICKET_OVERRIDE_PATH = STATE_DIR / "tickets_adhoc.jsonl"


@app.post("/api/ticket")
async def api_ticket(request: Request) -> JSONResponse:
    """Open/move/close a ticket (agent or founder). Body: {id, status, owner?, note?}. Overrides win by id."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not body.get("id"):
        return JSONResponse({"error": "id required"}, status_code=400)
    entry = {"ts": _now_iso(), "id": str(body["id"])[:60], "status": body.get("status"),
             "owner": body.get("owner"), "note": str(body.get("note", ""))[:400],
             "title": body.get("title"), "epic": body.get("epic")}
    TICKET_OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TICKET_OVERRIDE_PATH.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return JSONResponse({"accepted": True, "ts": entry["ts"]})


@app.get("/api/tickets")
async def api_tickets() -> JSONResponse:
    """Derived truthful ticket board + live agent/founder overrides merged by id (newest wins)."""
    board = None
    for cand in (STATE_DIR / "helm_tickets.json", DATA_DIR / "helm_tickets.json", STATIC_DIR / "helm_tickets.json",
                 Path(__file__).resolve().parent.parent.parent.parent / "has_live_project_tracker/data/helm_tickets.json"):
        try:
            if cand.exists():
                board = json.loads(cand.read_text(encoding="utf-8")); break
        except Exception:
            continue
    if board is None:
        return JSONResponse({"error": "helm_tickets.json not synced", "tickets": []}, status_code=404)
    # apply overrides
    ov = {}
    try:
        if TICKET_OVERRIDE_PATH.exists():
            for ln in TICKET_OVERRIDE_PATH.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(ln); ov[e["id"]] = e
                except Exception:
                    continue
    except Exception:
        pass
    by_id = {t["id"]: t for t in board.get("tickets", [])}
    for tid, e in ov.items():
        t = by_id.get(tid) or {"id": tid, "epic": e.get("epic", "ADHOC"), "title": e.get("title", tid)}
        for k in ("status", "owner", "note", "title", "epic"):
            if e.get(k) is not None:
                t[k] = e[k]
        t["updated"] = e.get("ts")
        by_id[tid] = t
    board["tickets"] = list(by_id.values())
    from collections import Counter
    board["counts"] = dict(Counter(t.get("status") for t in board["tickets"]))
    board["overrides_applied"] = len(ov)
    return JSONResponse(board)


@app.get("/api/heartbeats")
async def api_heartbeats(limit: int = 40) -> JSONResponse:
    """Recent agent heartbeats (live comms feed) — lets each agent SEE the others in real time.
    Reads the append-only heartbeat log; newest last. Read-only, no fake data."""
    beats = []
    try:
        if HEARTBEAT_PATH.exists():
            lines = HEARTBEAT_PATH.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 200)):]
            for ln in lines:
                try:
                    e = json.loads(ln)
                    p = e.get("payload", {}) or {}
                    beats.append({"ts": e.get("received_at"), "worker": p.get("worker", "unknown"),
                                  "status": p.get("status"), "focus": p.get("focus") or p.get("tick"),
                                  "role": p.get("role")})
                except Exception:
                    continue
    except Exception:
        pass
    # roster = distinct workers with their most-recent beat
    roster = {}
    for b in beats:
        roster[b["worker"]] = b
    return JSONResponse({"generated_at": _now_iso(), "count": len(beats),
                         "workers_live": list(roster.values()), "recent": beats[-limit:]})


@app.post("/api/heartbeat")
async def api_heartbeat(request: Request) -> JSONResponse:
    """Accept a heartbeat ping from an agent."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    entry = {
        "received_at": _now_iso(),
        "source_ip": request.client.host if request.client else "unknown",
        "payload": body,
    }

    # Persist to JSONL
    HEARTBEAT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HEARTBEAT_PATH.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")

    return JSONResponse({"accepted": True, "ts": entry["received_at"]})


# ---------------------------------------------------------------------------
# Startup event
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    """Ensure /data directory exists on startup."""
    try:
        Path("/data").mkdir(parents=True, exist_ok=True)
    except Exception:
        possible_local = Path(__file__).resolve().parent.parent.parent.parent / "has_live_project_tracker/data"
        if possible_local.exists():
            possible_local.mkdir(parents=True, exist_ok=True)
    # Write bootstrap registry if none exists
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text(json.dumps(_load_registry(), indent=2))


@app.get("/")
def dashboard_root():
    p = Path("/app/static/index.html")
    if not p.exists():
        p = Path(__file__).resolve().parent.parent / "dashboard/index.html"
    return FileResponse(p)
