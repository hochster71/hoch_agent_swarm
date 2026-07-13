#!/usr/bin/env python3
"""redact_evidence.py — sanitize a raw evidence log before it enters a HELM package.

    command > raw-proof.log 2>&1
    python scripts/evidence/redact_evidence.py raw-proof.log > proof.sanitized.log

DOCTRINE (ratified by the founder)
----------------------------------
"Paste the raw output" is unsafe: commands touching credentials, JWTs, cookies, headers,
env vars or API responses leak secrets into chat, terminal history, model context, logs,
screenshots, and committed evidence. So:

    raw evidence      -> local restricted storage (chmod 600), NEVER committed
    sanitized evidence -> HELM package
    hash of raw evidence -> HELM package (proves the sanitized derives from a real raw)

This script does the middle step: read raw, emit sanitized. It fails CLOSED — an
unrecognised-but-secret-shaped token is redacted rather than risked. A redactor that lets
one secret through is worse than none, because it is trusted.
"""
from __future__ import annotations

import re
import sys

# Each pattern replaces the SECRET portion with a typed marker, keeping enough prefix to
# stay debuggable ("which kind of key", not "which key").
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("stripe_secret",   re.compile(r"sk_(live|test)_[A-Za-z0-9]{10,}"),        r"sk_\1_[REDACTED]"),
    ("stripe_restricted", re.compile(r"rk_(live|test)_[A-Za-z0-9]{10,}"),      r"rk_\1_[REDACTED]"),
    ("stripe_webhook",  re.compile(r"whsec_[A-Za-z0-9]{10,}"),                 "whsec_[REDACTED]"),
    ("supabase_sb_secret", re.compile(r"sb_secret_[A-Za-z0-9_-]{10,}"),        "sb_secret_[REDACTED]"),
    ("jwt",             re.compile(r"eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}"), "eyJ[REDACTED_JWT]"),
    ("bearer",          re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"),    r"\1[REDACTED]"),
    ("apikey_header",   re.compile(r"(?i)(apikey:\s*)\S+"),                    r"\1[REDACTED]"),
    ("set_cookie",      re.compile(r"(?i)(set-cookie:\s*[^=]+=)[^;\s]+"),      r"\1[REDACTED]"),
    ("auth_cookie",     re.compile(r"(sb-[a-z0-9]+-auth-token[^=]*=)[^;\s]+"), r"\1[REDACTED]"),
    ("aws_key",         re.compile(r"AKIA[0-9A-Z]{16}"),                       "AKIA[REDACTED]"),
    ("github_pat",      re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),            "ghX_[REDACTED]"),
    ("openai",          re.compile(r"sk-[A-Za-z0-9]{20,}"),                    "sk-[REDACTED]"),
    ("private_key",     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
    # generic: KEY=... / TOKEN=... / SECRET=... / PASSWORD=... assignments
    ("env_secret",      re.compile(r"(?i)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|PWD)[A-Z0-9_]*\s*[=:]\s*)(\S+)"), r"\1[REDACTED]"),
]

# A last-resort net: long high-entropy base64-ish blobs that matched nothing above.
_ENTROPY = re.compile(r"\b[A-Za-z0-9+/_-]{40,}\b")


def redact(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for name, pat, repl in PATTERNS:
        text, n = pat.subn(repl, text)
        if n:
            counts[name] = counts.get(name, 0) + n
    # entropy sweep — redact any surviving long token that isn't an obvious hash label
    def _e(m: re.Match[str]) -> str:
        counts["entropy_blob"] = counts.get("entropy_blob", 0) + 1
        return "[REDACTED_HIGH_ENTROPY]"
    text = _ENTROPY.sub(_e, text)
    return text, counts


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: redact_evidence.py <raw-log> [> sanitized]", file=sys.stderr)
        return 2
    with open(argv[1], "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    clean, counts = redact(raw)
    sys.stdout.write(clean)
    if counts:
        print(f"\n# [redact_evidence] redactions: {counts}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
