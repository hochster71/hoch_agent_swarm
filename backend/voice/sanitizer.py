"""Speech sanitizer — secrets, paths, and dumps never leave the mouth."""

from __future__ import annotations

import re
from typing import Optional

from backend.voice.policy import compiled_redact_patterns, load_voice_policy

_JSONISH = re.compile(r"\{[^{}]{40,}\}")
_LONG_HEX = re.compile(r"\b[0-9a-fA-F]{32,}\b")
_WS = re.compile(r"\s+")


def sanitize_for_speech(text: str, *, max_chars: Optional[int] = None) -> str:
    """Redact secrets and shrink text for calm executive speech."""
    if text is None:
        return ""
    p = load_voice_policy()
    if p.get("speak_secrets"):
        # Still never speak private key blocks even if misconfigured
        s = re.sub(
            r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----",
            "[REDACTED]",
            str(text),
        )
    else:
        s = str(text)
        for pat in compiled_redact_patterns():
            s = pat.sub("[REDACTED]", s)
        s = _JSONISH.sub("[REDACTED_JSON]", s)
        s = _LONG_HEX.sub("[REDACTED]", s)

    s = _WS.sub(" ", s).strip()
    limit = int(max_chars if max_chars is not None else p.get("max_speech_chars") or 1200)
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    return s
