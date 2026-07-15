"""Tool schemas for Grok Voice Agents and external bridges."""

from __future__ import annotations

from typing import Any, Dict, List


def grok_voice_tools() -> List[Dict[str, Any]]:
    """OpenAI function-calling shaped tools bound to HELM Voice HTTP API."""
    return [
        {
            "type": "function",
            "function": {
                "name": "helm_executive_brief",
                "description": (
                    "Get HELM executive briefing from Runtime Truth. "
                    "Returns speech_text and per-field LIVE/STALE/UNKNOWN labels. "
                    "Never invent metrics if this tool fails — report UNKNOWN."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "x_helm_http": {"method": "GET", "path": "/api/v1/helm/voice/brief"},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "helm_voice_command",
                "description": (
                    "Execute a governed HELM voice command. "
                    "READ_ONLY observes truth; STAGE_ONLY stages artifacts; "
                    "DOORSTEP actions are blocked and must escalate to founder."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": (
                                "Command id: executive_brief, founder_approvals, "
                                "blocked_factories, highest_priority_mission, "
                                "runtime_health, security_posture, overnight_summary, "
                                "mission_status, evidence_gaps, idle_agents, "
                                "goal_status, repo_status, route_task, stage_mission"
                            ),
                        },
                        "utterance": {
                            "type": "string",
                            "description": "Free-text command if command id unknown",
                        },
                        "args": {
                            "type": "object",
                            "description": "Optional args (mission, factory, topic)",
                        },
                    },
                    "additionalProperties": False,
                },
                "x_helm_http": {"method": "POST", "path": "/api/v1/helm/voice/command"},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "helm_list_voice_commands",
                "description": "List available HELM voice commands and modes.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "x_helm_http": {"method": "GET", "path": "/api/v1/helm/voice/commands"},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "helm_voice_policy",
                "description": "Get HELM voice policy (DOORSTEP verbs, TTS defaults, doctrine).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "x_helm_http": {"method": "GET", "path": "/api/v1/helm/voice/policy"},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "helm_sanitize_speech",
                "description": "Sanitize text before speaking; redacts secrets and keys.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to sanitize for speech"}
                    },
                    "required": ["text"],
                    "additionalProperties": False,
                },
                "x_helm_http": {"method": "POST", "path": "/api/v1/helm/voice/sanitize"},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "helm_factory_brief",
                "description": (
                    "Per-factory voice brief. Registered: HASF, HMF, HRF. "
                    "Planned (not LIVE): HSF, HCF, HFF, HHF, HPF. Never invent metrics."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Factory code e.g. HASF, HMF, HRF, HSF",
                        }
                    },
                    "required": ["code"],
                    "additionalProperties": False,
                },
                "x_helm_http": {
                    "method": "GET",
                    "path": "/api/v1/helm/voice/factory/{code}",
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "helm_role_brief",
                "description": (
                    "Leadership role brief: founder, ops, ciso, cfo, qa. "
                    "Role-specific lens over Runtime Truth; DOORSTEP never auto-executed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role": {
                            "type": "string",
                            "enum": ["founder", "ops", "ciso", "cfo", "qa"],
                        }
                    },
                    "required": ["role"],
                    "additionalProperties": False,
                },
                "x_helm_http": {
                    "method": "GET",
                    "path": "/api/v1/helm/voice/role/{role}",
                },
            },
        },
    ]
