from __future__ import annotations

import uuid
import hashlib
from typing import Any, Dict, Tuple

from backend.voice.models import VoiceRequestEnvelope, AuthenticationContext, ConfirmationContext
from backend.voice.intent_parser import parse_intent
from backend.voice.authorization import authorize_voice_request
from backend.voice.confirmation import generate_confirmation_challenge, verify_confirmation_challenge
from backend.voice.command_router import route_and_execute_intent
from backend.voice.response_renderer import render_voice_speech
from backend.voice.audit_events import log_voice_audit_event
from backend.voice.redaction import redact_sensitive_data
from backend.voice.rate_limiter import VoiceRateLimiter

class VoiceGatewayService:
    @classmethod
    def process_voice_request(cls, raw_envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Core coordinator of the provider-neutral voice gateway.

        Normalizes, validates, rate-limits, authorizes, confirms, executes, and audits.
        """
        # 1. Schema Validation
        try:
            envelope = VoiceRequestEnvelope.model_validate(raw_envelope)
        except Exception as e:
            # Audit failure-to-parse
            log_voice_audit_event(
                request_id=raw_envelope.get("request_id", f"VOICE-REQ-ERR-{uuid.uuid4().hex[:8].upper()}"),
                provider=raw_envelope.get("provider", "UNKNOWN"),
                actor_id=raw_envelope.get("actor_id", "anonymous"),
                device_id_hash=raw_envelope.get("device_id_hash", "sha256:" + "0"*64),
                intent=raw_envelope.get("intent", "unknown"),
                classification="UNKNOWN",
                auth_result="DENY",
                confirmation_result="NOT_REQUIRED",
                exec_result="FAILED",
                target_resource="VOICE_GATEWAY",
                response_status="UNKNOWN",
                correlation_id=raw_envelope.get("nonce", "")
            )
            return {
                "status": "ERROR",
                "speech_text": "Invalid request envelope structure.",
                "detail": str(e)
            }

        # Redact the input utterance in the stored representation
        envelope.utterance_redacted = redact_sensitive_data(envelope.utterance_redacted)

        # 2. Rate Limiting Check
        if not VoiceRateLimiter.check_rate_limit(envelope.device_id_hash):
            log_voice_audit_event(
                request_id=envelope.request_id,
                provider=envelope.provider,
                actor_id=envelope.actor_id,
                device_id_hash=envelope.device_id_hash,
                intent=envelope.intent,
                classification="UNKNOWN",
                auth_result="DENY",
                confirmation_result="NOT_REQUIRED",
                exec_result="FAILED",
                target_resource="RATE_LIMITER",
                response_status="THROTTLED",
                correlation_id=envelope.nonce
            )
            return {
                "status": "THROTTLED",
                "speech_text": "Request throttled. Too many voice requests.",
                "detail": "Rate limit exceeded"
            }

        # 3. Check if this is a confirmation challenge submission
        if envelope.intent == "helm.confirm":
            code = envelope.parameters.get("code", "")
            is_ok, reason, target_intent, target_params = verify_confirmation_challenge(
                envelope.session_id, code
            )
            if not is_ok:
                log_voice_audit_event(
                    request_id=envelope.request_id,
                    provider=envelope.provider,
                    actor_id=envelope.actor_id,
                    device_id_hash=envelope.device_id_hash,
                    intent=envelope.intent,
                    classification="WRITE",
                    auth_result="DENY",
                    confirmation_result="INCORRECT_CODE",
                    exec_result="FAILED",
                    target_resource="CONFIRMATION_GATE",
                    response_status="DENIED",
                    correlation_id=envelope.nonce
                )
                return {
                    "status": "DENIED",
                    "speech_text": f"Confirmation failed: {reason}.",
                    "detail": reason
                }
            
            # If code is correct, overwrite intent and parameters with the cached ones and proceed
            envelope.intent = target_intent
            envelope.parameters = target_params
            envelope.confirmation.confirmed = True

        # 4. Authorization Decision
        auth_decision, auth_reason = authorize_voice_request(envelope)
        
        classification = "WRITE" if envelope.intent.startswith("helm.operator_hold.") or envelope.intent.startswith("helm.assessment.") or envelope.intent.startswith("helm.finding.") else "READ_ONLY"

        if auth_decision == "DENY":
            log_voice_audit_event(
                request_id=envelope.request_id,
                provider=envelope.provider,
                actor_id=envelope.actor_id,
                device_id_hash=envelope.device_id_hash,
                intent=envelope.intent,
                classification=classification,
                auth_result="DENY",
                confirmation_result="NOT_REQUIRED" if not envelope.confirmation.confirmed else "CONFIRMED",
                exec_result="FAILED",
                target_resource="AUTHORIZATION_GATE",
                response_status="DENIED",
                correlation_id=envelope.nonce
            )
            return {
                "status": "DENIED",
                "speech_text": render_voice_speech("DENIED", auth_reason),
                "detail": auth_reason
            }

        if auth_decision == "CONFIRMATION_REQUIRED":
            # Generate challenge
            chg_id, chg_code = generate_confirmation_challenge(
                envelope.session_id,
                envelope.intent,
                envelope.parameters,
                actor_id=envelope.actor_id,
                provider=envelope.provider,
                device_id_hash=envelope.device_id_hash
            )
            spaced_code = " ".join(list(chg_code))
            speech = f"To execute this command, say: confirm {spaced_code} within 30 seconds."
            
            log_voice_audit_event(
                request_id=envelope.request_id,
                provider=envelope.provider,
                actor_id=envelope.actor_id,
                device_id_hash=envelope.device_id_hash,
                intent=envelope.intent,
                classification=classification,
                auth_result="CONFIRMATION_REQUIRED",
                confirmation_result="PENDING",
                exec_result="SUCCESS",
                target_resource="CONFIRMATION_GATE",
                response_status="CONFIRMATION_REQUIRED",
                correlation_id=envelope.nonce
            )
            
            return {
                "status": "CONFIRMATION_REQUIRED",
                "challenge_id": chg_id,
                "speech_text": speech,
                "detail": "Action requires confirmation code"
            }

        # 5. Execution (ALLOW)
        exec_status, detail, raw_data = route_and_execute_intent(envelope.intent, envelope.parameters)
        
        # Redact secrets in raw_data/detail representation
        detail = redact_sensitive_data(detail)
        
        log_voice_audit_event(
            request_id=envelope.request_id,
            provider=envelope.provider,
            actor_id=envelope.actor_id,
            device_id_hash=envelope.device_id_hash,
            intent=envelope.intent,
            classification=classification,
            auth_result="ALLOW",
            confirmation_result="CONFIRMED" if envelope.confirmation.confirmed else "NOT_REQUIRED",
            exec_result="SUCCESS" if exec_status == "SUCCESS" else "FAILED",
            target_resource="EXECUTION_ROUTER",
            response_status=exec_status,
            correlation_id=envelope.nonce
        )

        return {
            "status": exec_status,
            "speech_text": render_voice_speech(exec_status, detail, raw_data),
            "detail": detail,
            "data": raw_data
        }
