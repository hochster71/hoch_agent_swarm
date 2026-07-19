"""Voice command registry — intents map to governed execution modes."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# mode:
#   READ_ONLY  — observe only
#   STAGE_ONLY — stage reversible artifacts
#   DOORSTEP   — founder only; never executed by voice

COMMAND_REGISTRY: Dict[str, Dict[str, Any]] = {
    "executive_brief": {
        "id": "executive_brief",
        "mode": "READ_ONLY",
        "description": "Generate today's executive briefing from Runtime Truth",
        "utterance_patterns": [
            r"executive brief",
            r"brief me",
            r"morning brief",
            r"status of (the )?swarm",
            r"what('?s| is) (my |the )?status",
            r"generate (today'?s )?executive briefing",
        ],
        "priority": 0,
    },
    "highest_priority_mission": {
        "id": "highest_priority_mission",
        "mode": "READ_ONLY",
        "description": "Report highest priority / critical-path mission",
        "utterance_patterns": [
            r"highest priority",
            r"critical path",
            r"what should i (work on|do) (first|next)",
            r"priority mission",
        ],
        "priority": 1,
    },
    "founder_approvals": {
        "id": "founder_approvals",
        "mode": "READ_ONLY",
        "description": "List pending founder approvals / DOORSTEP items",
        "utterance_patterns": [
            r"founder approval",
            r"approvals? (waiting|pending)",
            r"what needs (my|founder) (approval|decision)",
            r"doorstep",
        ],
        "priority": 1,
    },
    "blocked_factories": {
        "id": "blocked_factories",
        "mode": "READ_ONLY",
        "description": "Report blocked or non-live factories",
        "utterance_patterns": [
            r"blocked factor",
            r"which factor(y|ies).*(block|stuck)",
            r"show blocked",
            r"factory status",
        ],
        "priority": 1,
    },
    "runtime_health": {
        "id": "runtime_health",
        "mode": "READ_ONLY",
        "description": "Runtime, leases, concurrency health",
        "utterance_patterns": [
            r"runtime (health|truth|status)",
            r"is (helm|the system) (up|live|healthy)",
            r"leases?",
            r"concurrency",
        ],
        "priority": 1,
    },
    "security_posture": {
        "id": "security_posture",
        "mode": "READ_ONLY",
        "description": "Security / integrity posture summary",
        "utterance_patterns": [
            r"security (posture|status|advisory)",
            r"integrity",
            r"nist",
            r"rmf readiness",
        ],
        "priority": 2,
    },
    "overnight_summary": {
        "id": "overnight_summary",
        "mode": "READ_ONLY",
        "description": "Summarize recent observed execution events",
        "utterance_patterns": [
            r"overnight",
            r"what happened (last night|overnight|while i was away)",
            r"summarize (recent|overnight) (execution|activity)",
        ],
        "priority": 1,
    },
    "mission_status": {
        "id": "mission_status",
        "mode": "READ_ONLY",
        "description": "Brief status for a named mission (e.g. Epic Fury)",
        "utterance_patterns": [
            r"brief me on (?P<mission>.+)",
            r"status of (?P<mission>.+)",
            r"why is (?P<mission>.+) blocked",
            r"explain (?P<mission>.+)",
        ],
        "priority": 1,
        "args": ["mission"],
    },
    "evidence_gaps": {
        "id": "evidence_gaps",
        "mode": "READ_ONLY",
        "description": "What evidence is missing before release",
        "utterance_patterns": [
            r"evidence (missing|gap)",
            r"before release",
            r"what('?s| is) missing",
            r"final verifier",
        ],
        "priority": 1,
    },
    "idle_agents": {
        "id": "idle_agents",
        "mode": "READ_ONLY",
        "description": "Identify idle capacity / agent accountability view",
        "utterance_patterns": [
            r"idle agent",
            r"reassign",
            r"agent (utilization|activity|accountability)",
        ],
        "priority": 2,
    },
    "goal_status": {
        "id": "goal_status",
        "mode": "READ_ONLY",
        "description": "North star / critical path from goal_state.json validators",
        "utterance_patterns": [
            r"goal status",
            r"north star",
            r"critical path blocker",
            r"how (close|far).*(goal|north star)",
            r"champion product",
        ],
        "priority": 1,
    },
    "repo_status": {
        "id": "repo_status",
        "mode": "READ_ONLY",
        "description": "Local git branch/dirty state (GitHub remote remains UNKNOWN unless observed)",
        "utterance_patterns": [
            r"github status",
            r"repo status",
            r"git status",
            r"what branch",
            r"is the (repo|tree) (clean|dirty)",
        ],
        "priority": 1,
    },
    "route_task": {
        "id": "route_task",
        "mode": "STAGE_ONLY",
        "description": "Stage a task route recommendation to a factory (does not execute)",
        "utterance_patterns": [
            r"\broute\b.+\bto\b",
            r"route (this |the )?task to (?P<factory>.+)",
            r"send (this |the )?to (?P<factory>.+ factory)",
            r"launch (?P<factory>.+) (on|for) (?P<topic>.+)",
        ],
        "priority": 1,
        "args": ["factory", "topic"],
    },
    "factory_brief": {
        "id": "factory_brief",
        "mode": "READ_ONLY",
        "description": "Per-factory brief (HASF/HMF/HRF registered; HSF/HCF/HFF/HHF/HPF planned)",
        "utterance_patterns": [
            r"brief (me on )?(the )?(?P<factory>hasf|hmf|hrf|hsf|hcf|hff|hhf|hpf)\b",
            r"\b(?P<factory>hasf|hmf|hrf|hsf|hcf|hff|hhf|hpf) (factory|status|brief)\b",
            r"\b(?P<factory>software|music|research) factory\b",
            r"^factory (?P<factory>hasf|hmf|hrf|hsf|hcf|hff|hhf|hpf)\b",
        ],
        "priority": 2,
        "args": ["factory"],
    },
    "role_brief": {
        "id": "role_brief",
        "mode": "READ_ONLY",
        "description": "Leadership role brief: founder, ops, ciso, cfo, qa",
        "utterance_patterns": [
            r"(?P<role>ciso|cfo) (officer|brief|status|lens)",
            r"founder (brief|status|lens|executive)",
            r"(?P<role>qa|ops) (brief|status|lens)",
            r"security (officer|brief|status)",
            r"finance (officer|brief|status)",
            r"mission control",
            r"final verifier",
        ],
        "priority": 2,
        "args": ["role"],
    },
    "calendar_agenda": {
        "id": "calendar_agenda",
        "mode": "READ_ONLY",
        "description": "Read real Apple Calendar events + Reminders for today/tomorrow",
        "utterance_patterns": [
            r"\bcalendar\b",
            r"\bschedule\b",
            r"\bagenda\b",
            r"\breminders?\b",
            r"what('?s| is) (on |in )?(my )?(calendar|schedule|agenda)",
            r"what (do i|have i) (have )?(on |going on )?(today|tomorrow|this week)",
            r"what('?s| is) (happening|going on) (today|tomorrow)",
            r"my day",
            r"anything (today|tomorrow)",
        ],
        "priority": 1,
        "args": ["scope"],
    },
    "revenue_status": {
        "id": "revenue_status",
        "mode": "READ_ONLY",
        "description": "Verified settled revenue from HochLedger only",
        "utterance_patterns": [
            r"\brevenue\b",
            r"how much (did we|have we) (make|made|earn)",
            r"are we earning",
            r"settled (dollars|revenue|sales)",
            r"north.?star metric",
        ],
        "priority": 1,
    },
    "security_alerts": {
        "id": "security_alerts",
        "mode": "READ_ONLY",
        "description": "HIGH security findings for speech (rate-limited)",
        "utterance_patterns": [
            r"security (alert|alerts|findings|high)",
            r"high findings",
            r"any security (issues|incidents)",
            r"speak security",
        ],
        "priority": 1,
    },
    "mission_ops": {
        "id": "mission_ops",
        "mode": "READ_ONLY",
        "description": "Executive mission state dashboard (operational status of the mission)",
        "utterance_patterns": [
            r"mission status",
            r"mission state",
            r"operational state",
            r"executive dashboard",
            r"where is (the )?mission",
            r"overall mission",
            r"are we ready to (ship|release)",
        ],
        "priority": 0,
    },
    "stage_mission": {
        "id": "stage_mission",
        "mode": "STAGE_ONLY",
        "description": "Stage a mission intake draft for founder/HELM review",
        "utterance_patterns": [
            r"create (a )?mission",
            r"new mission",
            r"intake (this|goal)",
        ],
        "priority": 2,
    },
    # Explicit DOORSTEP — always blocked for voice execution
    "deploy": {
        "id": "deploy",
        "mode": "DOORSTEP",
        "description": "Deploy / production ship — founder only",
        "utterance_patterns": [r"\bdeploy\b", r"ship to (prod|production)", r"go live"],
        "priority": 0,
    },
    "spend": {
        "id": "spend",
        "mode": "DOORSTEP",
        "description": "Spend / paid providers / move money — founder only",
        "utterance_patterns": [r"\bspend\b", r"buy ", r"charge card", r"move money"],
        "priority": 0,
    },
    "provision_keys": {
        "id": "provision_keys",
        "mode": "DOORSTEP",
        "description": "Provision or rotate secrets — founder only",
        "utterance_patterns": [r"provision (api )?keys?", r"rotate (the )?keys?", r"api key"],
        "priority": 0,
    },
    # Explicit DOORSTEP verbs that previously fell through to READ_ONLY routes
    # (audit GOV-03: "sign the release" → runtime_health was imprecise).
    "sign_release": {
        "id": "sign_release",
        "mode": "DOORSTEP",
        "description": "Sign / approve a release — founder only",
        "utterance_patterns": [
            r"\bsign\b.*\brelease\b",
            r"\bsign the release\b",
            r"\bapprove (the )?release\b",
            r"\brelease signature\b",
        ],
        "priority": 0,
    },
    "submit_store": {
        "id": "submit_store",
        "mode": "DOORSTEP",
        "description": "Submit to App Store / TestFlight — founder only",
        "utterance_patterns": [
            r"\bsubmit\b.*(app store|testflight|asc)\b",
            r"\bsubmit (to )?(the )?(app store|testflight)\b",
            r"\bpush to (testflight|app store)\b",
        ],
        "priority": 0,
    },
    "clear_apple_gate": {
        "id": "clear_apple_gate",
        "mode": "DOORSTEP",
        "description": "Clear Apple / TestFlight / ASC gates — founder only",
        "utterance_patterns": [
            r"\bclear (the )?apple\b",
            r"\bclear (testflight|asc|app store)\b",
            r"\bmark (apple|testflight) (cleared|done|pass)\b",
        ],
        "priority": 0,
    },
    "mark_revenue": {
        "id": "mark_revenue",
        "mode": "DOORSTEP",
        "description": "Mark revenue earned / settled — founder only (ledger is source of truth)",
        "utterance_patterns": [
            r"\bmark\b.{0,40}\b(earned|settled)\b",
            r"\bmark (the )?(revenue|dollar|sale)s?\b",
            r"\bwe (made|earned) (money|revenue|a dollar)\b",
            r"\bset (settled )?revenue\b",
        ],
        "priority": 0,
    },
}


def list_commands_public() -> List[Dict[str, Any]]:
    out = []
    for c in COMMAND_REGISTRY.values():
        out.append(
            {
                "id": c["id"],
                "mode": c["mode"],
                "description": c["description"],
                "examples": [p.replace("(?P<", "<").replace(">.+)", ">") for p in c["utterance_patterns"][:3]],
            }
        )
    return sorted(out, key=lambda x: (0 if x["mode"] == "READ_ONLY" else 1 if x["mode"] == "STAGE_ONLY" else 2, x["id"]))


def resolve_command(
    command_id: Optional[str] = None,
    utterance: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, str]]:
    """Resolve a command by id or free-text utterance. Returns (cmd, args)."""
    args: Dict[str, str] = {}
    if command_id:
        cid = command_id.strip().lower().replace("-", "_").replace(" ", "_")
        cmd = COMMAND_REGISTRY.get(cid)
        return cmd, args

    text = (utterance or "").strip().lower()
    if not text:
        return None, args

    # Prefer DOORSTEP, then STAGE_ONLY (mutations), then lower priority numbers
    _mode_rank = {"DOORSTEP": 0, "STAGE_ONLY": 1, "READ_ONLY": 2}
    ordered = sorted(
        COMMAND_REGISTRY.values(),
        key=lambda c: (_mode_rank.get(c["mode"], 9), c.get("priority", 9)),
    )
    for cmd in ordered:
        for pat in cmd.get("utterance_patterns") or []:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                if m.groupdict():
                    for k, v in m.groupdict().items():
                        if v:
                            args[k] = v.strip(" .?!,;:\"'")
                return cmd, args
    return None, args
