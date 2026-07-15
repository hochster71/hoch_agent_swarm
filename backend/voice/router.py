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
                "factory": "/api/v1/helm/voice/factory/{code}",
                "factories": "/api/v1/helm/voice/factories",
                "role": "/api/v1/helm/voice/role/{role}",
                "roles": "/api/v1/helm/voice/roles",
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
            "v1": {
                "factory": "/api/v1/helm/voice/factory/{code}",
                "factories": "/api/v1/helm/voice/factories",
                "role": "/api/v1/helm/voice/role/{role}",
                "roles": "/api/v1/helm/voice/roles",
            },
        }
    )


@router.get("/factories")
def voice_factories_roster():
    """Roster: registered factories (AVAILABLE) + planned (PLANNED, not LIVE)."""
    from backend.voice.factory_agents import list_factory_voice_roster, observe_all_registered_factories

    all_reg = observe_all_registered_factories()
    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_FACTORY_ROSTER",
            "status": all_reg.get("status"),
            "observed_at": all_reg.get("observed_at"),
            "roster": list_factory_voice_roster(),
            "registered_briefs": all_reg.get("factories"),
            "speech_text": all_reg.get("speech_text"),
        }
    )


@router.get("/factory/{code}")
def voice_factory_brief(code: str):
    """Per-factory voice brief. Registered = observe BRAIN; planned = PLANNED not LIVE."""
    from backend.voice.factory_agents import observe_factory

    return JSONResponse(observe_factory(code))


@router.get("/roles")
def voice_roles_list():
    """Leadership role agents catalog."""
    from backend.voice.role_agents import list_roles

    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_ROLES",
            "status": "LIVE",
            "roles": list_roles(),
        }
    )


@router.get("/role/{role}")
def voice_role_brief(role: str):
    """Leadership role brief (founder, ops, ciso, cfo, qa)."""
    from backend.voice.role_agents import observe_role

    return JSONResponse(observe_role(role))


@router.get("/revenue")
def voice_revenue():
    """Verified settled revenue from HochLedger only (fail-closed)."""
    from backend.voice.revenue import observe_revenue

    return JSONResponse(observe_revenue())


@router.get("/security/events")
def voice_security_events(mark_spoken: bool = False):
    """HIGH security findings for speech; rate-limited. mark_spoken advances cursor."""
    from backend.voice.security_events import security_events_for_speech

    return JSONResponse(security_events_for_speech(mark_spoken=mark_spoken))


@router.post("/security/events/ack")
def voice_security_events_ack():
    """Mark currently pending HIGH events as spoken (rate-limit cursor)."""
    from backend.voice.security_events import security_events_for_speech

    return JSONResponse(security_events_for_speech(mark_spoken=True))


@router.get("/grok-pack")
def voice_grok_pack(base_url: str = "https://YOUR-HELM-ORIGIN", format: str = "json"):
    """Founder Grok Voice tool pack — JSON or markdown for paste."""
    from fastapi.responses import PlainTextResponse

    from backend.voice.grok_pack import build_grok_tool_pack, render_grok_pack_markdown

    pack = build_grok_tool_pack(base_url=base_url)
    if (format or "json").lower() in ("md", "markdown", "text"):
        return PlainTextResponse(
            render_grok_pack_markdown(pack),
            media_type="text/markdown; charset=utf-8",
        )
    return JSONResponse(pack)


class TtsSpeakRequest(BaseModel):
    text: str = Field(..., description="Text to speak (will be sanitized)")
    voice_id: Optional[str] = Field(None, description="Optional ElevenLabs voice id")
    format: str = Field(
        "audio",
        description="audio = raw mpeg stream; json = base64 payload for tool agents",
    )


@router.get("/tts/status")
def voice_tts_status():
    """TTS provider status: local_tts always available; ElevenLabs fail-closed until configured."""
    from backend.voice.elevenlabs_tts import elevenlabs_config_status

    el = elevenlabs_config_status()
    return JSONResponse(
        {
            "truth_class": "HELM_VOICE_TTS",
            "status": "LIVE",
            "providers": {
                "local_tts": {
                    "status": "AVAILABLE",
                    "cost_usd": 0,
                    "note": "Browser SpeechSynthesis on /voice desk",
                },
                "elevenlabs": el,
                "grok_builtin": {
                    "status": "EXTERNAL",
                    "note": (
                        "If Grok Voice Agents has built-in voices, use them. "
                        "If not, call POST /api/v1/helm/voice/tts/speak (ElevenLabs) "
                        "or use local_tts on the HELM desk."
                    ),
                },
            },
            "recommended": (
                "elevenlabs"
                if el.get("ready")
                else "grok_builtin_or_local_tts"
            ),
        }
    )


@router.post("/tts/speak")
def voice_tts_speak(body: TtsSpeakRequest):
    """Synthesize speech via ElevenLabs when READY; otherwise JSON BLOCKED + local_tts fallback.

    - format=audio → audio/mpeg bytes (for browser Audio)
    - format=json  → base64 audio for Grok/tool agents without built-in TTS
    """
    from fastapi.responses import Response

    from backend.voice.elevenlabs_tts import synthesize_speech

    want_json = (body.format or "audio").lower() in ("json", "base64", "data")
    ok, meta, audio = synthesize_speech(
        body.text,
        voice_id=body.voice_id,
        as_base64=want_json,
    )
    if not ok:
        return JSONResponse(
            {
                "truth_class": "HELM_VOICE_TTS_SPEAK",
                "status": meta.get("status") or "BLOCKED",
                "fallback": "local_tts",
                **meta,
            },
            status_code=503 if meta.get("status") == "BLOCKED" else 502,
        )
    if want_json:
        return JSONResponse(
            {
                "truth_class": "HELM_VOICE_TTS_SPEAK",
                "status": "LIVE",
                "provider": "elevenlabs",
                **meta,
            }
        )
    return Response(
        content=audio,
        media_type=meta.get("content_type") or "audio/mpeg",
        headers={
            "X-HELM-TTS-Provider": "elevenlabs",
            "X-HELM-TTS-Bytes": str(meta.get("bytes") or 0),
            "Cache-Control": "no-store",
        },
    )
