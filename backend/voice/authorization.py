from __future__ import annotations

import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from backend.voice.models import VoiceRequestEnvelope
from backend.voice.intent_registry import INTENT_REGISTRY
from backend.voice.session_store import SessionStore
from backend.runtime_truth.operator_hold import is_effectively_active

ROOT = Path(__file__).resolve().parents[2]
HOLD_FILE = ROOT / "has_live_project_tracker/data/ag_operator_hold.json"

def check_timestamp_freshness(timestamp_str: str, max_age_s: float = 30.0) -> bool:
    """Returns True if the timestamp is within max_age_s of current server time."""
    try:
        # Parse timestamp (e.g. 2026-07-19T12:00:00Z)
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = abs((now - dt).total_seconds())
        return age <= max_age_s
    except Exception:
        return False

def authorize_voice_request(envelope: VoiceRequestEnvelope) -> Tuple[str, str]:
    """Evaluates authorization policy for the request envelope.

    Returns Tuple (decision, reason) where decision is:
      - ALLOW
      - DENY
      - CONFIRMATION_REQUIRED
    """
    intent_name = envelope.intent
    
    # 1. Enforce intent allowlist
    if intent_name not in INTENT_REGISTRY:
        return "DENY", f"Intent '{intent_name}' is not in the allowlist"

    defn = INTENT_REGISTRY[intent_name]

    # 2. Replay & freshness checks
    if not check_timestamp_freshness(envelope.timestamp):
        return "DENY", "Request timestamp has expired (outside 30s window)"

    if not SessionStore.register_request(envelope.request_id, envelope.nonce):
        return "DENY", "Duplicate request_id or nonce detected (replay attack)"

    # 3. Check for authenticated linked identity
    if not envelope.actor_id or envelope.actor_id.lower() == "anonymous":
        return "DENY", "Missing authenticated linked identity"

    # 4. Role binding check
    if defn.required_role == "FOUNDER" and envelope.actor_id.lower() != "founder":
        return "DENY", f"Actor '{envelope.actor_id}' is not authorized for founder-only commands"

    # 5. Assurance level check
    req_level = defn.required_assurance
    act_level = envelope.authentication_context.assurance_level
    
    level_hierarchy = {"LOW": 1, "MODERATE": 2, "HIGH": 3}
    if level_hierarchy.get(act_level, 0) < level_hierarchy.get(req_level, 0):
        return "DENY", f"Insufficient assurance level (required {req_level}, got {act_level})"

    # 6. Operator hold block check for mutations (WRITE commands)
    if defn.classification == "WRITE":
        # Load live operator hold state
        hold_active = False
        if HOLD_FILE.exists():
            try:
                hold_data = json.loads(HOLD_FILE.read_text(encoding="utf-8"))
                hold_active = is_effectively_active(hold_data)
            except Exception:
                pass
        
        # If hold is active, only hold management commands are allowed (i.e. disable)
        if hold_active and intent_name != "helm.operator_hold.disable":
            return "DENY", "System is under operator hold. Non-release write commands are blocked."

        # 7. Check if confirmation is required
        if defn.confirmation_required and not envelope.confirmation.confirmed:
            return "CONFIRMATION_REQUIRED", "Write operation requires confirmation challenge"

    return "ALLOW", "Authorized successfully"
