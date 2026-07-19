from __future__ import annotations

import secrets
import time
from typing import Any, Dict, Tuple
from backend.voice.session_store import SessionStore, SessionState

CONFIRMATION_TTL_SECONDS = 30
MAX_ATTEMPTS = 3

def generate_confirmation_challenge(
    session_id: str,
    intent_name: str,
    parameters: Dict[str, Any],
    actor_id: str = None,
    provider: str = None,
    device_id_hash: str = None
) -> Tuple[str, str]:
    """Generate a random 3-digit confirmation challenge code (e.g. 742).

    Saves challenge details in the session state. Returns (challenge_id, challenge_code).
    """
    # 3-digit random code
    code_num = 100 + secrets.randbelow(900)
    code_str = str(code_num)
    
    challenge_id = f"CHG-{secrets.token_hex(4).upper()}"
    now = time.time()
    
    session = SessionStore.get_or_create_session(session_id)
    session.active_challenge_id = challenge_id
    session.active_challenge_code = code_str
    session.challenge_intent = intent_name
    session.challenge_params = parameters
    session.challenge_expires_at = now + CONFIRMATION_TTL_SECONDS
    session.attempts = 0
    session.actor_id = actor_id
    session.provider = provider
    session.device_id_hash = device_id_hash
    
    SessionStore.update_session(session)
    return challenge_id, code_str

def verify_confirmation_challenge(session_id: str, presented_code: str) -> Tuple[bool, str, Optional[str], Dict[str, Any]]:
    """Verifies and consumes the active challenge.

    Returns (is_valid, reason, intent_name, params).
    """
    session = SessionStore.get_or_create_session(session_id)
    
    if not session.active_challenge_code:
        return False, "No active confirmation challenge found for this session", None, {}

    # Check expiry
    if time.time() > session.challenge_expires_at:
        from backend.voice.audit_events import log_voice_audit_event
        log_voice_audit_event(
            request_id=f"CONFIRM-EXP-{session.active_challenge_id}",
            provider=session.provider or "UNKNOWN",
            actor_id=session.actor_id or "UNKNOWN",
            device_id_hash=session.device_id_hash or "UNKNOWN",
            intent=session.challenge_intent or "UNKNOWN",
            classification="WRITE",
            auth_result="ALLOW",
            confirmation_result="EXPIRED",
            exec_result="NOT_EXECUTED",
            target_resource="VOICE",
            response_status="CONFIRM_EXPIRED"
        )
        SessionStore.clear_challenge(session_id)
        return False, "Confirmation challenge has expired", None, {}

    # Check maximum attempts
    if session.attempts >= MAX_ATTEMPTS:
        SessionStore.clear_challenge(session_id)
        return False, "Maximum confirmation attempts exceeded", None, {}

    # Clean code: extract digits from spoken string if any
    cleaned_code = "".join(re.findall(r"\d", presented_code))
    
    if cleaned_code == session.active_challenge_code:
        intent = session.challenge_intent
        params = session.challenge_params
        # Consume challenge
        SessionStore.clear_challenge(session_id)
        return True, "Challenge verified", intent, params
    else:
        session.attempts += 1
        SessionStore.update_session(session)
        
        from backend.voice.audit_events import log_voice_audit_event
        # Log failed confirmation attempt
        log_voice_audit_event(
            request_id=f"CONFIRM-FAIL-{session.active_challenge_id}",
            provider=session.provider or "UNKNOWN",
            actor_id=session.actor_id or "UNKNOWN",
            device_id_hash=session.device_id_hash or "UNKNOWN",
            intent=session.challenge_intent or "UNKNOWN",
            classification="WRITE",
            auth_result="ALLOW",
            confirmation_result=f"FAIL_ATTEMPT_{session.attempts}",
            exec_result="NOT_EXECUTED",
            target_resource="VOICE",
            response_status="CONFIRM_FAILED"
        )
        
        if session.attempts >= MAX_ATTEMPTS:
            SessionStore.clear_challenge(session_id)
            return False, "Maximum confirmation attempts exceeded (challenge invalidated)", None, {}
            
        return False, f"Incorrect confirmation code (attempt {session.attempts}/{MAX_ATTEMPTS})", None, {}

import re
