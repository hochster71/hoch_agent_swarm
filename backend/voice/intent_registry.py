from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]

class IntentDefinition(BaseModel):
    name: str
    description: str
    classification: str  # READ_ONLY | WRITE
    required_role: str   # FOUNDER | OPERATOR | ANY
    required_assurance: str  # LOW | MODERATE | HIGH
    confirmation_required: bool
    allowed_parameters: Dict[str, str] = {}  # param_name -> type
    spoken_template: str

# Dict to hold registered intent executors
_EXECUTORS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

# Allowlisted intents
INTENT_REGISTRY: Dict[str, IntentDefinition] = {
    "helm.status.summary": IntentDefinition(
        name="helm.status.summary",
        description="Summarize overall HELM mission status",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="HELM status summary: {summary}. Decision is {decision}."
    ),
    "helm.runtime.health": IntentDefinition(
        name="helm.runtime.health",
        description="Check active runtime health, leases and concurrency",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Runtime health is {health_status}. Active lease count is {lease_count}."
    ),
    "helm.agents.online": IntentDefinition(
        name="helm.agents.online",
        description="List online swarm agents",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Online agents: {agents}."
    ),
    "helm.blockers.list": IntentDefinition(
        name="helm.blockers.list",
        description="List active blockers",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Active blockers: {blockers}."
    ),
    "helm.mission.progress": IntentDefinition(
        name="helm.mission.progress",
        description="Detail progress of the highest priority mission",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Mission {mission_id} is in state {state}."
    ),
    "helm.factory.status": IntentDefinition(
        name="helm.factory.status",
        description="Report active status of all factories",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="MODERATE",
        confirmation_required=False,
        spoken_template="Factory status summary: {status_summary}."
    ),
    "helm.audit.posture": IntentDefinition(
        name="helm.audit.posture",
        description="Get HAF audit decision and posture",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Current HAF audit decision is {decision}. Certification level is {level}."
    ),
    "helm.audit.open_findings": IntentDefinition(
        name="helm.audit.open_findings",
        description="List open HAF findings and POA&Ms",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Active open findings: {findings}."
    ),
    "helm.audit.control_status": IntentDefinition(
        name="helm.audit.control_status",
        description="Check status of a specific control ID",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="MODERATE",
        confirmation_required=False,
        allowed_parameters={"control_id": "string"},
        spoken_template="Control {control_id} status is {status}."
    ),
    "helm.audit.latest_assessment": IntentDefinition(
        name="helm.audit.latest_assessment",
        description="Display latest HAF assessment stats",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Latest run {run_id} decision: {decision}. Total controls evaluated: {controls_count}."
    ),
    "helm.production_authority": IntentDefinition(
        name="helm.production_authority",
        description="Query production authority status",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Production authority: {production_authority}. Readiness: {pilot_readiness}."
    ),
    "helm.operator_hold.status": IntentDefinition(
        name="helm.operator_hold.status",
        description="Query if operator hold is currently active",
        classification="READ_ONLY",
        required_role="OPERATOR",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="Operator hold is {hold_status}."
    ),
    "helm.help": IntentDefinition(
        name="helm.help",
        description="Lists supported voice intents",
        classification="READ_ONLY",
        required_role="ANY",
        required_assurance="LOW",
        confirmation_required=False,
        spoken_template="I can report status, audit posture, online agents, or set operator hold."
    ),
    
    # Controlled-Write Intents (Require confirmation + High Assurance + Founder)
    "helm.operator_hold.enable": IntentDefinition(
        name="helm.operator_hold.enable",
        description="Enable system-wide operator hold",
        classification="WRITE",
        required_role="FOUNDER",
        required_assurance="HIGH",
        confirmation_required=True,
        spoken_template="Operator hold successfully enabled. Reason: {reason}."
    ),
    "helm.operator_hold.disable": IntentDefinition(
        name="helm.operator_hold.disable",
        description="Disable system-wide operator hold",
        classification="WRITE",
        required_role="FOUNDER",
        required_assurance="HIGH",
        confirmation_required=True,
        spoken_template="Operator hold successfully disabled."
    ),
    "helm.assessment.start": IntentDefinition(
        name="helm.assessment.start",
        description="Trigger HAF assessment profile run",
        classification="WRITE",
        required_role="FOUNDER",
        required_assurance="HIGH",
        confirmation_required=True,
        allowed_parameters={"profile": "string"},
        spoken_template="HAF assessment started. Profile: {profile}. Run ID: {run_id}."
    ),
    "helm.conmon.run": IntentDefinition(
        name="helm.conmon.run",
        description="Force-run ConMon health cycle",
        classification="WRITE",
        required_role="FOUNDER",
        required_assurance="HIGH",
        confirmation_required=True,
        spoken_template="Continuous Monitoring cycle triggered successfully."
    ),
    "helm.finding.mark_in_progress": IntentDefinition(
        name="helm.finding.mark_in_progress",
        description="Transition a finding to IN_PROGRESS status",
        classification="WRITE",
        required_role="FOUNDER",
        required_assurance="HIGH",
        confirmation_required=True,
        allowed_parameters={"finding_id": "string"},
        spoken_template="Finding {finding_id} status updated to IN_PROGRESS."
    ),
    "helm.finding.mark_ready_for_retest": IntentDefinition(
        name="helm.finding.mark_ready_for_retest",
        description="Transition a finding to READY_FOR_RETEST",
        classification="WRITE",
        required_role="FOUNDER",
        required_assurance="HIGH",
        confirmation_required=True,
        allowed_parameters={"finding_id": "string"},
        spoken_template="Finding {finding_id} status updated to READY_FOR_RETEST."
    )
}

def register_executor(intent_name: str, func: Callable[[Dict[str, Any]], Dict[str, Any]]):
    _EXECUTORS[intent_name] = func

def get_executor(intent_name: str) -> Optional[Callable[[Dict[str, Any]], Dict[str, Any]]]:
    return _EXECUTORS.get(intent_name)
