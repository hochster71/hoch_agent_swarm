from __future__ import annotations

import time
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel
from backend.voice.service import VoiceGatewayService
from backend.voice.intent_parser import parse_intent

class WebVoiceRequest(BaseModel):
    transcript: str
    actor_id: str
    assurance_level: str  # LOW | MODERATE | HIGH
    session_id: str
    nonce: str
    signature: str

def handle_web_voice_request(req: WebVoiceRequest) -> Dict[str, Any]:
    """Processes speech transcript from Web console PTT, maps to intent, and invokes VoiceGateway."""
    # 1. Parse intent from utterance
    intent, params = parse_intent(req.transcript)
    
    if not intent:
        intent = "helm.help"

    # If it is a confirm utterance (e.g. "confirm 7 4 2"), match intent to helm.confirm
    confirm_match = re.search(r"\bconfirm\s*(\d\s*\d\s*\d)\b", req.transcript, re.IGNORECASE)
    if confirm_match:
        intent = "helm.confirm"
        params = {"code": confirm_match.group(1).replace(" ", "")}

    device_hash = "sha256:" + hashlib.sha256(b"web_console_session").hexdigest()
    
    # 2. Build canonical voice envelope
    request_id = f"VOICE-REQ-WEB-{hashlib.md5(f'{req.nonce}-{req.transcript}'.encode()).hexdigest()[:8].upper()}"
    
    envelope = {
        "request_id": request_id,
        "provider": "WEB",
        "device_id_hash": device_hash,
        "actor_id": req.actor_id,
        "session_id": req.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "intent": intent,
        "parameters": params,
        "utterance_redacted": req.transcript,
        "authentication_context": {
            "method": "local_session",
            "assurance_level": req.assurance_level
        },
        "confirmation": {
            "required": False,
            "challenge_id": None,
            "confirmed": False
        },
        "nonce": req.nonce,
        "signature": req.signature,
        "schema_version": "1.0.0"
    }

    # 3. Process request via Voice Gateway
    return VoiceGatewayService.process_voice_request(envelope)

import re
from datetime import datetime, timezone
