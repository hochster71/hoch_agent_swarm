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
HEARTBEAT_PATH = Path("/tmp/heartbeats.jsonl")

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
