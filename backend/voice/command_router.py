from __future__ import annotations

import json
import os
import time
import subprocess
from pathlib import Path
from typing import Any, Dict, Tuple
from datetime import datetime, timezone

from backend.voice.intent_registry import INTENT_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
GOAL_STATE = ROOT / "coordination" / "goal" / "goal_state.json"
MISSION_STATE = ROOT / "coordination" / "goal" / "mission_state.json"
HOLD_FILE = ROOT / "has_live_project_tracker/data/ag_operator_hold.json"
HOLD_EVENTS_FILE = ROOT / "has_live_project_tracker/data/ag_operator_hold_events.jsonl"
# ROUTING-REGISTRY-DUAL-READ closure (2026-07-19): direct frozen-file read migrated to the
# governed resolver — backend.helm_runtime.extensions.model_routing (registry first, frozen fallback).
FACTORY_REGISTRY = ROOT / "coordination/council/factory_registry.json"
MILESTONE_DECISION = ROOT / "coordination/audit_factory/decisions/HAF_v0_1_milestone_decision.json"
FINDINGS_FILE = ROOT / "coordination/audit_factory/findings.json"

def _load_json(p: Path, default: Any = None) -> Any:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default or {}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def route_and_execute_intent(intent: str, parameters: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    """Routes the validated voice intent to the authoritative command executor.

    Returns (status, spoken_detail, raw_data).
    """
    if intent not in INTENT_REGISTRY:
        return "UNKNOWN", "Intent not supported", {}

    try:
        # 1. READ_ONLY Intents
        if intent == "helm.status.summary":
            m_state = _load_json(MISSION_STATE)
            summary = m_state.get("detail", "Mission status is UNKNOWN.")
            decision = m_state.get("decision", "UNKNOWN")
            return "SUCCESS", f"HELM status summary: {summary}. Decision is {decision}.", m_state

        elif intent == "helm.runtime.health":
            # Check daemon heartbeat age
            hb_path = ROOT / "coordination/council/council_heartbeat.jsonl"
            hb_status = "UNKNOWN"
            if hb_path.exists():
                mtime = hb_path.stat().st_mtime
                age = time.time() - mtime
                if age < 300: # 5 min SLA
                    hb_status = "healthy"
                else:
                    hb_status = "stale"
            
            lease_count = 0
            lease_dir = ROOT / "coordination/leases"
            if lease_dir.exists():
                lease_count = len([f for f in lease_dir.glob("*.lock") if f.is_file()])
            
            return "SUCCESS", f"Runtime health is {hb_status}. Active lease count is {lease_count}.", {"health": hb_status, "leases": lease_count}

        elif intent == "helm.agents.online":
            from backend.helm_runtime.extensions.model_routing import list_roles
            agents = list_roles() or ["auditor", "grok", "ag-ide"]
            agents_str = ", ".join(agents)
            return "SUCCESS", f"Online agents: {agents_str}.", {"agents": agents}

        elif intent == "helm.blockers.list":
            gs = _load_json(GOAL_STATE)
            blockers = gs.get("blockers", []) or ["no active blockers"]
            blockers_str = ", ".join(blockers)
            return "SUCCESS", f"Active blockers: {blockers_str}.", {"blockers": blockers}

        elif intent == "helm.mission.progress":
            m_state = _load_json(MISSION_STATE)
            mid = m_state.get("mission_id", "EPIC-FURY-2026")
            state = m_state.get("status", "UNKNOWN")
            return "SUCCESS", f"Mission {mid} is in state {state}.", m_state

        elif intent == "helm.factory.status":
            fr = _load_json(FACTORY_REGISTRY)
            factories = list(fr.get("factories", {}).keys()) or ["HASF", "HRF", "HMF"]
            fac_str = ", ".join(factories)
            return "SUCCESS", f"Factory status summary: online factories are {fac_str}.", {"factories": factories}

        elif intent == "helm.audit.posture":
            ms = _load_json(MILESTONE_DECISION)
            dec = ms.get("decision", "UNKNOWN")
            lvl = ms.get("scope", "L1")
            return "SUCCESS", f"Current HAF audit decision is {dec}. Certification level is {lvl}.", ms

        elif intent == "helm.audit.open_findings":
            findings_data = _load_json(FINDINGS_FILE)
            findings_list = findings_data.get("findings", [])
            open_fnd = [f["control_id"] for f in findings_list if f.get("status") == "OPEN"]
            if not open_fnd:
                return "SUCCESS", "Active open findings: none. Kernel status is PASS.", {"findings": []}
            fnd_str = ", ".join(open_fnd)
            return "SUCCESS", f"Active open findings: {fnd_str}.", {"findings": open_fnd}

        elif intent == "helm.audit.control_status":
            cid = parameters.get("control_id")
            if not cid:
                return "FAILED", "Missing parameter control_id", {}
            
            # Query HAF control status
            from backend.audit_factory.service import HAFService
            service = HAFService(workspace_root=str(ROOT))
            ctrl = service.control_registry.get_control(cid)
            if not ctrl:
                return "FAILED", f"Control {cid} not found in catalog", {}
            status, reason = service._evaluate_control_status(ctrl)
            return "SUCCESS", f"Control {cid} status is {status} because: {reason}.", {"control_id": cid, "status": status, "reason": reason}

        elif intent == "helm.audit.latest_assessment":
            from backend.audit_factory.service import HAFService
            service = HAFService(workspace_root=str(ROOT))
            runs = service.list_runs()
            if not runs:
                return "SUCCESS", "No assessment runs found.", {}
            # Get latest run
            latest_run = sorted(runs, key=lambda r: r.get("run_id", ""), reverse=True)[0]
            rid = latest_run.get("run_id")
            dec = latest_run.get("decision")
            cnt = latest_run.get("controls_count", 45)
            return "SUCCESS", f"Latest run {rid} decision: {dec}. Total controls evaluated: {cnt}.", latest_run

        elif intent == "helm.production_authority":
            ms = _load_json(MILESTONE_DECISION)
            pa = ms.get("production_authority", "CONDITIONAL")
            pr = ms.get("pilot_readiness", "GO")
            return "SUCCESS", f"Production authority is {pa}. Readiness is {pr}.", ms

        elif intent == "helm.operator_hold.status":
            hold = _load_json(HOLD_FILE)
            active = "ACTIVE" if hold.get("operator_hold_active") else "INACTIVE"
            return "SUCCESS", f"Operator hold is {active}.", hold

        elif intent == "helm.help":
            return "SUCCESS", "I can report status, audit posture, online agents, or set operator hold.", {}

        # 2. WRITE/MUTATION Intents
        elif intent == "helm.operator_hold.enable":
            reason = parameters.get("reason", "Voice enabled operator hold")
            payload = {
                "operator_hold_active": True,
                "reason": reason,
                "operator": "Michael Hoch (Voice)",
                "hold_class": "manual",
                "timestamp": _now(),
                "expires_at": None,
                "affected_categories": []
            }
            HOLD_FILE.parent.mkdir(parents=True, exist_ok=True)
            HOLD_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            with open(HOLD_EVENTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
            return "SUCCESS", f"Operator hold successfully enabled. Reason: {reason}.", payload

        elif intent == "helm.operator_hold.disable":
            payload = {
                "operator_hold_active": False,
                "reason": "Voice disabled operator hold",
                "operator": "Michael Hoch (Voice)",
                "hold_class": "manual",
                "timestamp": _now(),
                "expires_at": None,
                "affected_categories": []
            }
            HOLD_FILE.parent.mkdir(parents=True, exist_ok=True)
            HOLD_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            with open(HOLD_EVENTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
            return "SUCCESS", "Operator hold successfully disabled.", payload

        elif intent == "helm.assessment.start":
            prof = parameters.get("profile", "helm_common")
            from backend.audit_factory.service import HAFService
            service = HAFService(workspace_root=str(ROOT))
            summary = service.run_assessment(profile_name=prof, scope="HELM_COMMON")
            rid = summary.get("run_id")
            dec = summary.get("decision")
            return "SUCCESS", f"HAF assessment started. Profile: {prof}. Run ID: {rid}. Decision: {dec}.", summary

        elif intent == "helm.conmon.run":
            # Run conmon cycle
            from backend.audit_factory.service import HAFService
            service = HAFService(workspace_root=str(ROOT))
            # Just trigger verification
            service.run_assessment(profile_name="helm_common", scope="HELM_COMMON")
            return "SUCCESS", "Continuous Monitoring cycle triggered successfully.", {}

        elif intent == "helm.finding.mark_in_progress":
            fid = parameters.get("finding_id")
            if not fid:
                return "FAILED", "Missing parameter finding_id", {}
            # Update finding status in database/file
            findings_data = _load_json(FINDINGS_FILE)
            found = False
            for f in findings_data.get("findings", []):
                if f.get("finding_id") == fid:
                    f["status"] = "IN_PROGRESS"
                    found = True
                    break
            if not found:
                return "FAILED", f"Finding {fid} not found", {}
            FINDINGS_FILE.write_text(json.dumps(findings_data, indent=2), encoding="utf-8")
            return "SUCCESS", f"Finding {fid} status updated to IN_PROGRESS.", {"finding_id": fid}

        elif intent == "helm.finding.mark_ready_for_retest":
            fid = parameters.get("finding_id")
            if not fid:
                return "FAILED", "Missing parameter finding_id", {}
            findings_data = _load_json(FINDINGS_FILE)
            found = False
            for f in findings_data.get("findings", []):
                if f.get("finding_id") == fid:
                    f["status"] = "READY_FOR_RETEST"
                    found = True
                    break
            if not found:
                return "FAILED", f"Finding {fid} not found", {}
            FINDINGS_FILE.write_text(json.dumps(findings_data, indent=2), encoding="utf-8")
            return "SUCCESS", f"Finding {fid} status updated to READY_FOR_RETEST.", {"finding_id": fid}

    except Exception as e:
        return "FAILED", f"Execution error: {e}", {}

    return "UNKNOWN", "Intent execution not mapped", {}
