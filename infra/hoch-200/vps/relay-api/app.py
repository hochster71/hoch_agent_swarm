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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse,  HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HOCH-200 Relay API",
    version="1.0.0",
    docs_url=None,   # disable swagger in prod
    redoc_url=None,
)

STATIC_DIR = Path(__file__).parent / "static"
REGISTRY_PATH = Path("/tmp/worker_registry.json")
HEARTBEAT_PATH = Path("/tmp/heartbeats.jsonl")

# Mount static dashboard if the directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    daemon_state = {}
    daemon_state_path = Path("/data/ag_execution_daemon_state.json")
    if daemon_state_path.exists():
        try:
            daemon_state = json.loads(daemon_state_path.read_text())
        except Exception:
            pass

    burn_in_summary = {}
    burn_in_summary_path = Path("/data/ag_execution_burn_in_summary.json")
    if burn_in_summary_path.exists():
        try:
            burn_in_summary = json.loads(burn_in_summary_path.read_text())
        except Exception:
            pass

    queue_health = {}
    queue_health_path = Path("/data/ag_execution_queue_health.json")
    if queue_health_path.exists():
        try:
            queue_health = json.loads(queue_health_path.read_text())
        except Exception:
            pass

    proof_index = {}
    proof_index_path = Path("/data/ag_execution_proof_index.json")
    if proof_index_path.exists():
        try:
            proof_index = json.loads(proof_index_path.read_text())
        except Exception:
            pass

    fencing_status = {}
    fencing_status_path = Path("/data/ag_execution_fencing_status.json")
    if fencing_status_path.exists():
        try:
            fencing_status = json.loads(fencing_status_path.read_text())
        except Exception:
            pass

    task_queue = []
    task_queue_path = Path("/data/helm_task_queue.json")
    if task_queue_path.exists():
        try:
            task_queue = json.loads(task_queue_path.read_text())
        except Exception:
            pass

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

    # ------------------------------------------------------------------
    # 24H GO gate — COMPUTED from live evidence.
    # Previously this was a hardcoded "NOT_YET" string literal disconnected
    # from every signal, so it could never flip regardless of the run.
    # This mirrors the canonical Phase-E gate in
    # scripts/verify_ag_execution_burn_in.py (no violations + enough real
    # cycles + heartbeat fresh + elapsed >= 24h) and additionally requires
    # the same integrity checks the dashboard renders (queue / fencing /
    # proof). Fails CLOSED to NOT_YET on any missing or failing signal —
    # this is evidence-gated, not a green stamp.
    # ------------------------------------------------------------------
    _failed_rate = burn_in_summary.get("failed_cycle_rate", 1.0)
    _real_cycles = burn_in_summary.get("real_cycles", 0)
    _missing_proofs = burn_in_summary.get("missing_proof_detected", 1)
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
    go_24h_status = "GO" if go_24h_pass else "NOT_YET"
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
        "telemetry_host_path": "/root/hoch_agent_swarm/has_live_project_tracker/data",
        "container_mount_mode": "read_only"
    })


@app.get("/api/registry")
async def api_registry() -> JSONResponse:
    """Return worker registry."""
    return JSONResponse(_load_registry())


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
    Path("/data").mkdir(parents=True, exist_ok=True)
    # Write bootstrap registry if none exists
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text(json.dumps(_load_registry(), indent=2))


@app.get("/")
def dashboard_root():
    return FileResponse("/app/static/index.html")
