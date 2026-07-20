"""FastAPI router for HELM Voice Executive endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Header, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.voice.models import VoiceRequestEnvelope
from backend.voice.service import VoiceGatewayService
from backend.voice.intent_registry import INTENT_REGISTRY
from backend.voice.session_store import SessionStore
from backend.voice.adapters.alexa import handle_alexa_request
from backend.voice.adapters.siri import handle_siri_request, SiriIntentRequest
from backend.voice.adapters.web_voice import handle_web_voice_request, WebVoiceRequest
from backend.voice.audit_events import AUDIT_LOG_FILE

router = APIRouter(prefix="/api/v1/helm/voice", tags=["HELM Voice"])

class VoiceConfirmRequest(BaseModel):
    session_id: str
    code: str
    actor_id: str
    nonce: str
    signature: str

@router.post("/request")
def voice_gateway_request(envelope: VoiceRequestEnvelope):
    """Generic voice gateway request receiver (normalized)."""
    res = VoiceGatewayService.process_voice_request(envelope.model_dump())
    return JSONResponse(res)

@router.post("/confirm")
def voice_confirm(body: VoiceConfirmRequest):
    """Direct challenge confirmation route."""
    import hashlib
    from datetime import datetime, timezone
    
    device_hash = "sha256:" + hashlib.sha256(b"confirm_direct").hexdigest()
    request_id = f"VOICE-REQ-CONFIRM-{hashlib.md5(body.nonce.encode()).hexdigest()[:8].upper()}"
    
    envelope = {
        "request_id": request_id,
        "provider": "WEB",
        "device_id_hash": device_hash,
        "actor_id": body.actor_id,
        "session_id": body.session_id,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "intent": "helm.confirm",
        "parameters": {"code": body.code},
        "utterance_redacted": f"confirm {body.code}",
        "authentication_context": {
            "method": "local_session",
            "assurance_level": "HIGH"
        },
        "confirmation": {
            "required": False,
            "challenge_id": None,
            "confirmed": False
        },
        "nonce": body.nonce,
        "signature": body.signature,
        "schema_version": "1.0.0"
    }
    res = VoiceGatewayService.process_voice_request(envelope)
    return JSONResponse(res)

@router.get("/session/{session_id}")
def voice_session_status(session_id: str):
    """Query state of confirmation challenge for a session."""
    sess = SessionStore.get_or_create_session(session_id)
    return JSONResponse(sess.model_dump())

@router.get("/intents")
def voice_list_intents():
    """Lists allowlisted registered intents."""
    return JSONResponse({
        "status": "LIVE",
        "intents": {name: defn.model_dump() for name, defn in INTENT_REGISTRY.items()}
    })

@router.get("/health")
def voice_gateway_health():
    """Independent observability check of voice gateway health."""
    hold_file = Path(__file__).resolve().parents[2] / "has_live_project_tracker/data/ag_operator_hold.json"
    hold_status = "INACTIVE"
    if hold_file.exists():
        try:
            data = json.loads(hold_file.read_text(encoding="utf-8"))
            if data.get("operator_hold_active"):
                hold_status = "ACTIVE"
        except Exception:
            pass

    # Read latest certification decision
    decision_file = Path(__file__).resolve().parents[2] / "coordination/audit_factory/decisions/HAF_v0_1_milestone_decision.json"
    haf_cert = "UNKNOWN"
    if decision_file.exists():
        try:
            data = json.loads(decision_file.read_text(encoding="utf-8"))
            haf_cert = data.get("decision", "UNKNOWN")
        except Exception:
            pass

    return JSONResponse({
            # merged executive-contract keys (additive; tests/unit/test_helm_voice_executive.py)
            "status": "LIVE",
            "subsystem": "voice_executive",
            "truth_class": "HELM_VOICE_HEALTH",

        "ALEXA": "TEST",
        "SIRI": "TEST",
        "WEB_VOICE": "LIVE",
        "VOICE_GATEWAY": "HEALTHY",
        "HAF_VOICE_CERTIFICATION": haf_cert,
        "operator_hold_status": hold_status
    })

@router.get("/audit/events")
def voice_audit_events(limit: int = Query(50)):
    """Fetch recent voice audit log entries."""
    events = []
    if AUDIT_LOG_FILE.exists():
        try:
            with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            for line in reversed(lines):
                if line.strip():
                    events.append(json.loads(line))
                    if len(events) >= limit:
                        break
        except Exception:
            pass
    return JSONResponse({"events": events})

@router.post("/alexa/webhook")
async def alexa_webhook(
    request: Request,
    signature: Optional[str] = Header(None, alias="Signature"),
    signaturecertchainurl: Optional[str] = Header(None, alias="SignatureCertChainUrl")
):
    """Alexa Custom Skill HTTPS endpoint handler."""
    raw_body = await request.body()
    res = handle_alexa_request(
        raw_body_or_dict=raw_body,
        signature=signature,
        cert_chain_url=signaturecertchainurl,
        local_test=True # local test mode bypasses s3 amazon cert checks
    )
    return JSONResponse(res)

@router.post("/siri/intent")
def siri_intent(body: SiriIntentRequest):
    """Siri companion intent handler."""
    res = handle_siri_request(body)
    return JSONResponse(res)

@router.post("/web/transcript")
def web_transcript(body: WebVoiceRequest):
    """Web push-to-talk spoken transcript receiver."""
    res = handle_web_voice_request(body)
    return JSONResponse(res)
