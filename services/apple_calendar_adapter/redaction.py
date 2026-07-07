"""Redaction helpers for the Apple Calendar adapter.

Pure functions only. No third-party imports, no network, no side effects.
These MUST be importable and testable without ``caldav``, ``fastapi``,
``pydantic`` or network access.

Security invariants enforced here:
  * The Apple app-specific password (env ``APPLE_CALDAV_PASSWORD``) must never
    appear in any string that leaves this process (responses, logs, exceptions,
    the ledger). ``redact_secret`` scrubs it.
  * Event descriptions / bodies are considered sensitive and are hidden by
    default. Only titles and times are exposed unless the caller has been
    explicitly approved (``approved=True``).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Mapping, Optional

# The literal placeholder we substitute for any redacted secret value.
REDACTION_PLACEHOLDER = "***REDACTED***"

# Environment variable names whose *values* must always be scrubbed from any
# outgoing text. APPLE_CALDAV_PASSWORD is the app-specific password; the others
# are defensive (some deployments export a combined URL containing the secret).
_SECRET_ENV_VARS = (
    "APPLE_CALDAV_PASSWORD",
    "APPLE_APP_SPECIFIC_PASSWORD",
    "CALDAV_PASSWORD",
)


def _collect_secret_values(extra_secrets: Optional[Iterable[str]] = None) -> list[str]:
    """Gather the concrete secret strings we must scrub.

    We read them from the environment at call time so the secret is never
    stored as a module-level constant. Empty / unset values are ignored.
    """
    values: list[str] = []
    for name in _SECRET_ENV_VARS:
        val = os.environ.get(name)
        if val:
            values.append(val)
    if extra_secrets:
        for s in extra_secrets:
            if s:
                values.append(s)
    # Longest first so overlapping secrets are fully removed.
    return sorted(set(values), key=len, reverse=True)


def redact_secret(text: Any, extra_secrets: Optional[Iterable[str]] = None) -> str:
    """Return ``text`` with every known secret value replaced by a placeholder.

    Accepts any type (exceptions, ints, etc.) and coerces to ``str`` first, so
    it is safe to wrap exception messages: ``redact_secret(str(exc))``.

    If no secret is currently set in the environment, the text is returned
    unchanged (coerced to str). This function NEVER raises on missing config —
    it fails safe by simply having nothing to scrub.
    """
    s = "" if text is None else str(text)
    for secret in _collect_secret_values(extra_secrets):
        if secret and secret in s:
            s = s.replace(secret, REDACTION_PLACEHOLDER)
    return s


def redact_event(
    event: Mapping[str, Any],
    approved: bool = False,
) -> Dict[str, Any]:
    """Return a copy of ``event`` safe to emit.

    Always drops the raw ``description``/``body`` fields unless ``approved`` is
    truthy. When hidden, a boolean ``description_redacted`` flag is set so
    callers can see that content exists without seeing it. Also scrubs any
    secret that may have leaked into a string value.

    ``event`` is treated as read-only; a new dict is returned.
    """
    safe: Dict[str, Any] = {}
    hidden = False
    for key, value in dict(event).items():
        lkey = str(key).lower()
        if lkey in ("description", "body", "notes", "summary_body"):
            if approved:
                safe[key] = redact_secret(value) if isinstance(value, str) else value
            else:
                hidden = True
                # Do not carry the raw field forward at all.
                continue
        elif isinstance(value, str):
            safe[key] = redact_secret(value)
        else:
            safe[key] = value

    if hidden:
        safe["description_redacted"] = True
    return safe


def redact_events(
    events: Iterable[Mapping[str, Any]],
    approved: bool = False,
) -> list[Dict[str, Any]]:
    """Vectorised :func:`redact_event` over an iterable of events."""
    return [redact_event(e, approved=approved) for e in events]
