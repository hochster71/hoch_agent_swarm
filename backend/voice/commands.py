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
    "route_task": {
        "id": "route_task",
        "mode": "STAGE_ONLY",
        "description": "Stage a task route recommendation to a factory (does not execute)",
        "utterance_patterns": [
            r"route (this |the )?task to (?P<factory>.+)",
            r"send (this |the )?to (?P<factory>.+ factory)",
            r"launch (?P<factory>.+) (on|for) (?P<topic>.+)",
        ],
        "priority": 2,
        "args": ["factory", "topic"],
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

    # Prefer DOORSTEP matches first so dangerous phrasing cannot be reclassified
    ordered = sorted(
        COMMAND_REGISTRY.values(),
        key=lambda c: (0 if c["mode"] == "DOORSTEP" else 1, c.get("priority", 9)),
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
