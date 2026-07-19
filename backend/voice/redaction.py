from __future__ import annotations

import re

# Redaction patterns from voice policy defaults
REDACT_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{10,}", re.IGNORECASE),
    re.compile(r"pk_[A-Za-z0-9]{10,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"/Users/[A-Za-z0-9_\-\.]+"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----(?:.|\n)*?-----END [A-Z ]+PRIVATE KEY-----", re.IGNORECASE)
]

def redact_sensitive_data(text: str) -> str:
    """Redacts secrets, key signatures, bearer tokens, and paths from text."""
    if not text:
        return ""
    
    redacted = text
    for pattern in REDACT_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
        
    return redacted
