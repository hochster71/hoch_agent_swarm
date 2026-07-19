from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional, Set
from pydantic import BaseModel

class SessionState(BaseModel):
    session_id: str
    active_challenge_id: Optional[str] = None
    active_challenge_code: Optional[str] = None
    challenge_intent: Optional[str] = None
    challenge_params: Dict[str, Any] = {}
    challenge_expires_at: float = 0.0
    attempts: int = 0
    actor_id: Optional[str] = None
    provider: Optional[str] = None
    device_id_hash: Optional[str] = None

class SessionStore:
    _lock = threading.Lock()
    _nonces: Set[str] = set()
    _request_ids: Set[str] = set()
    _sessions: Dict[str, SessionState] = {}
    
    # Nonce and request ID expiration limits (timestamp checks will also fail earlier)
    _recorded_times: Dict[str, float] = {}

    @classmethod
    def register_request(cls, request_id: str, nonce: str) -> bool:
        """Register request_id and nonce. Returns False if duplicate detected."""
        with cls._lock:
            # Clean up old records (older than 10 mins)
            now = time.time()
            expired = [k for k, t in cls._recorded_times.items() if now - t > 600]
            for k in expired:
                cls._nonces.discard(k)
                cls._request_ids.discard(k)
                cls._recorded_times.pop(k, None)

            if request_id in cls._request_ids or nonce in cls._nonces:
                return False

            cls._request_ids.add(request_id)
            cls._nonces.add(nonce)
            cls._recorded_times[request_id] = now
            cls._recorded_times[nonce] = now
            return True

    @classmethod
    def get_or_create_session(cls, session_id: str) -> SessionState:
        with cls._lock:
            if session_id not in cls._sessions:
                cls._sessions[session_id] = SessionState(session_id=session_id)
            return cls._sessions[session_id]

    @classmethod
    def update_session(cls, session: SessionState):
        with cls._lock:
            cls._sessions[session.session_id] = session

    @classmethod
    def clear_challenge(cls, session_id: str):
        with cls._lock:
            if session_id in cls._sessions:
                sess = cls._sessions[session_id]
                sess.active_challenge_id = None
                sess.active_challenge_code = None
                sess.challenge_intent = None
                sess.challenge_params = {}
                sess.challenge_expires_at = 0.0
                sess.attempts = 0
                sess.actor_id = None
                sess.provider = None
                sess.device_id_hash = None
