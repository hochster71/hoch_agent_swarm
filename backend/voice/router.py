"""FastAPI router for HELM Voice Executive endpoints."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.voice.briefing import build_executive_brief, execute_voice_command
from backend.voice.commands import list_commands_public
from backend.voice.policy import get_policy_public, reload_voice_policy
from backend.voice.sanitizer import sanitize_for_speech

router = APIRouter(prefix="/api/v1/helm/voice", tags=["HELM Voice"])


class VoiceCommandRequest(BaseModel):
    command: Optional[str] = Field(None, description="Command id, e.g. executive_brief")
    utterance: Optional[str] = Field(None, description="Free-text voice command")
    args: Optional[Dict[str, Any]] = Field(default=None, description="Optional structured args")


class SanitizeRequest(BaseModel):
    text: str


@router.get("/policy")
def voice_policy():
    """Public voice policy for UI clients and external voice agents."""
    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_POLICY",
            "status": "LIVE",
            "policy": get_policy_public(),
        }
    )


@router.post("/policy/reload")
def voice_policy_reload():
    """Reload policy YAML from disk (local ops)."""
    p = reload_voice_policy()
    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_POLICY",
            "status": "LIVE",
            "policy_version": p.get("policy_version"),
            "reloaded": True,
        }
    )


@router.get("/commands")
def voice_commands():
    """Command registry for discovery (Grok tools / UI)."""
    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_COMMANDS",
            "status": "LIVE",
            "commands": list_commands_public(),
            "doctrine": "READ_ONLY and STAGE_ONLY allowed; DOORSTEP never auto-executed",
        }
    )


@router.get("/brief")
def voice_brief():
    """Executive briefing assembled from Runtime Truth. Fail-closed labels."""
    brief = build_executive_brief()
    return JSONResponse(brief)


@router.post("/command")
def voice_command(body: VoiceCommandRequest):
    """Execute a governed voice command (read-only or stage-only)."""
    result = execute_voice_command(
        command_id=body.command,
        utterance=body.utterance,
        args=body.args,
    )
    return JSONResponse(result)


@router.get("/command")
def voice_command_get(
    command: Optional[str] = Query(None),
    utterance: Optional[str] = Query(None),
):
    """GET convenience for simple voice tool bridges."""
    result = execute_voice_command(command_id=command, utterance=utterance)
    return JSONResponse(result)


@router.post("/sanitize")
def voice_sanitize(body: SanitizeRequest):
    """Sanitize text before speech (secrets redacted)."""
    cleaned = sanitize_for_speech(body.text)
    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_SANITIZE",
            "status": "LIVE",
            "original_len": len(body.text or ""),
            "speech_text": cleaned,
            "redacted": cleaned != (body.text or ""),
        }
    )


@router.get("/tools")
def voice_tools_schema():
    """OpenAI-style tool definitions for Grok Voice Agents / external bridges."""
    from backend.voice.tools_schema import grok_voice_tools

    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_TOOLS",
            "status": "LIVE",
            "tools": grok_voice_tools(),
            "base_paths": {
                "policy": "/api/v1/helm/voice/policy",
                "commands": "/api/v1/helm/voice/commands",
                "brief": "/api/v1/helm/voice/brief",
                "command": "/api/v1/helm/voice/command",
                "sanitize": "/api/v1/helm/voice/sanitize",
            },
            "doctrine": [
                "Call tools for LIVE claims; never invent metrics",
                "DOORSTEP commands return blocked — escalate to founder",
                "UNKNOWN is a valid and preferred answer over fabrication",
            ],
        }
    )


@router.get("/health")
def voice_health():
    """Voice subsystem health — does not claim swarm LIVE."""
    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_HEALTH",
            "status": "LIVE",
            "subsystem": "voice_executive",
            "note": "Voice API is up. Swarm state requires /brief or /command.",
            "persona": get_policy_public().get("persona"),
        }
    )
