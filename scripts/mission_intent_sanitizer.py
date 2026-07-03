#!/usr/bin/env python3
import re

BLOCKED_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"reveal\s+secrets",
    r"print\s+env",
    r"bypass\s+policy",
    r"force\s+push",
    r"release\s+product",
    r"deploy\s+production",
    r"monetize",
    r"exfiltrate",
    r"show\s+api\s+key",
    r"disable\s+gate",
    r"overwrite\s+evidence",
    r"skip\s+verification"
]

def sanitize_intent(intent: str) -> tuple[str, str]:
    # Check for prompt injection patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, intent, re.IGNORECASE):
            return "FAIL", intent
            
    # Wrap text as data rather than instructions
    clean_intent = f"Data envelope: {intent}"
    return "PASS", clean_intent
