from __future__ import annotations

import re
from typing import Any, Dict

def render_voice_speech(status: str, detail: str = "", data: Dict[str, Any] = None) -> str:
    """Format safe and concise spoken responses, redacting raw hashes, paths, and tokens.

    Ensures that UNKNOWN, STALE, HOLD, and FAIL states are honestly reported.
    """
    data = data or {}
    
    # Lead with status-specific templates
    if status in ("UNKNOWN", "FAILED"):
        return "I cannot verify the current runtime state. " + (detail or "Telemetry is unavailable.")
        
    if status == "STALE":
        return "The last heartbeat is stale. I cannot report the daemon as online."
        
    if status == "HOLD":
        return "The audit decision is on hold because required evidence is missing. " + (detail or "")
        
    if status == "FAIL":
        return "The latest assessment failed one mandatory control. " + (detail or "")

    if status == "DENIED":
        return "Request denied. " + (detail or "Authentication is required.")

    # Success messages (lead with result)
    if detail:
        # Simplify common raw text elements:
        # 1. Redact full paths
        detail = re.sub(r"/[a-zA-Z0-9_\-\./]+", "[path]", detail)
        # 2. Redact long hex hashes (e.g. SHA-256)
        detail = re.sub(r"\b[a-fA-F0-9]{32,64}\b", "[hash]", detail)
        
        return detail

    return "Command executed successfully."
