"""ElevenLabs TTS provider for HELM Voice — optional, fail-closed paid path.

Used when:
  - Grok Voice Agents has no suitable built-in voice, OR
  - HELM /voice desk wants premium TTS instead of browser SpeechSynthesis

Doctrine:
  - Default OFF (no key, no paid flag, no accidental spend)
  - Secrets never logged or spoken
  - Text always sanitized before send
  - Network only to api.elevenlabs.io
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from backend.voice.policy import load_voice_policy
from backend.voice.sanitizer import sanitize_for_speech

ELEVEN_API = "https://api.elevenlabs.io/v1"
# Public default voice id (Rachel) — overridable via ELEVENLABS_VOICE_ID
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_MODEL = "eleven_multilingual_v2"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _api_key() -> str:
    return (os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_LABS_API_KEY") or "").strip()


def _voice_id() -> str:
    return (os.environ.get("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE_ID).strip()


def _model_id() -> str:
    p = load_voice_policy()
    return (
        os.environ.get("ELEVENLABS_MODEL_ID")
        or str(p.get("elevenlabs_model_id") or DEFAULT_MODEL)
    ).strip()


def elevenlabs_config_status() -> Dict[str, Any]:
    """Public status — never includes API key material."""
    p = load_voice_policy()
    key = _api_key()
    paid = bool(p.get("paid_providers_allowed"))
    # Explicit enable: policy flag OR env HELM_ELEVENLABS_TTS=1
    env_on = os.environ.get("HELM_ELEVENLABS_TTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    policy_on = bool(p.get("elevenlabs_enabled"))
    mode = str(p.get("voice_mode") or "local_tts")
    key_present = bool(key) and len(key) > 8
    # Ready only if key + (paid allowed) + (enabled via policy/env/mode)
    enabled_request = policy_on or env_on or mode == "elevenlabs"
    ready = bool(key_present and paid and enabled_request)
    blocked_reasons = []
    if not key_present:
        blocked_reasons.append("ELEVENLABS_API_KEY not set")
    if not paid:
        blocked_reasons.append("paid_providers_allowed=false in voice policy")
    if not enabled_request:
        blocked_reasons.append(
            "elevenlabs not enabled (set elevenlabs_enabled=true or HELM_ELEVENLABS_TTS=1 or voice_mode=elevenlabs)"
        )

    return {
        "truth_class": "HELM_VOICE_TTS_STATUS",
        "provider": "elevenlabs",
        "status": "READY" if ready else "BLOCKED",
        "ready": ready,
        "key_present": key_present,
        "paid_providers_allowed": paid,
        "elevenlabs_enabled_request": enabled_request,
        "voice_mode": mode,
        "voice_id": _voice_id() if ready else None,
        "model_id": _model_id() if ready else None,
        "blocked_reasons": blocked_reasons,
        "fallback": "local_tts",
        "observed_at": _now(),
        "note": (
            "Grok Voice Agents may include built-in voices; ElevenLabs is the HELM "
            "premium TTS path when Grok has none or you want a fixed founder voice."
        ),
    }


def synthesize_speech(
    text: str,
    *,
    voice_id: Optional[str] = None,
    as_base64: bool = False,
) -> Tuple[bool, Dict[str, Any], Optional[bytes]]:
    """Call ElevenLabs TTS. Returns (ok, meta, audio_bytes)."""
    status = elevenlabs_config_status()
    if not status["ready"]:
        return (
            False,
            {
                "status": "BLOCKED",
                "reason": "; ".join(status["blocked_reasons"]) or "not ready",
                "fallback": "local_tts",
                "tts": status,
            },
            None,
        )

    clean = sanitize_for_speech(text)
    if not clean or clean == "[REDACTED]":
        return False, {"status": "BLOCKED", "reason": "empty or fully redacted text"}, None

    vid = (voice_id or _voice_id()).strip()
    model = _model_id()
    url = f"{ELEVEN_API}/text-to-speech/{vid}"
    body = json.dumps(
        {
            "text": clean,
            "model_id": model,
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.75,
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": _api_key(),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            audio = resp.read()
            content_type = resp.headers.get("Content-Type") or "audio/mpeg"
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return (
            False,
            {
                "status": "ERROR",
                "reason": f"ElevenLabs HTTP {e.code}",
                "detail": err_body,
                "fallback": "local_tts",
            },
            None,
        )
    except Exception as e:
        return (
            False,
            {
                "status": "ERROR",
                "reason": f"ElevenLabs request failed: {e}",
                "fallback": "local_tts",
            },
            None,
        )

    if not audio or len(audio) < 100:
        return False, {"status": "ERROR", "reason": "empty audio response", "fallback": "local_tts"}, None

    meta: Dict[str, Any] = {
        "status": "LIVE",
        "provider": "elevenlabs",
        "voice_id": vid,
        "model_id": model,
        "bytes": len(audio),
        "content_type": content_type,
        "text_chars": len(clean),
        "speech_text": clean,
        "observed_at": _now(),
    }
    if as_base64:
        meta["audio_base64"] = base64.b64encode(audio).decode("ascii")
        meta["audio_data_url"] = f"data:audio/mpeg;base64,{meta['audio_base64']}"
    return True, meta, audio
