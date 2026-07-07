"""Apple Calendar CalDAV adapter — FastAPI app, local-only, security-first.

Bind: 127.0.0.1:8011 ONLY (never 0.0.0.0).
Mode: read_only by default. Writes require mode==read_write AND approval.

Design for testability WITHOUT network / caldav / fastapi:
  * The security-gate logic (:func:`resolve_mode`, :func:`get_credentials`,
    :func:`evaluate_write_gate`, :func:`build_ics`) is plain Python and is
    imported by the offline test suite.
  * ``fastapi`` and ``caldav`` are imported lazily / guarded so this module can
    be ``py_compile``-d and partially imported without those packages present.

HARD RULES enforced here:
  * The app-specific password is never returned, logged, or embedded. All
    error text is passed through ``redact_secret``.
  * Missing/ambiguous credentials, calendar, or approval => FAIL CLOSED.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

try:  # package-relative imports (normal case)
    from .redaction import redact_secret, redact_event, redact_events
    from . import ledger as ledger_mod
except ImportError:  # pragma: no cover - flat import fallback
    from redaction import redact_secret, redact_event, redact_events  # type: ignore
    import ledger as ledger_mod  # type: ignore

# ---------------------------------------------------------------------------
# Constants — binding is hard-coded to loopback.
# ---------------------------------------------------------------------------
BIND_HOST = "127.0.0.1"
BIND_PORT = 8011
DEFAULT_CALDAV_HOST = "https://caldav.icloud.com"
KEYCHAIN_ACCOUNT = "hochster_71@mac.com"
KEYCHAIN_SERVICE = "hoch-agent-swarm-apple-caldav"

MODE_READ_ONLY = "read_only"
MODE_READ_WRITE = "read_write"


class SecurityError(Exception):
    """Raised for fail-closed security conditions. Message is pre-redacted."""


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str  # never logged / returned
    host: str

    def redacted(self) -> dict:
        """Safe representation — NEVER includes the password."""
        return {"username": self.username, "host": self.host,
                "password": "***REDACTED***"}


# ---------------------------------------------------------------------------
# Mode resolution — fail closed to read_only on anything ambiguous.
# ---------------------------------------------------------------------------
def resolve_mode(env: Optional[dict] = None) -> str:
    """Return the effective mode. Anything not exactly 'read_write' => read_only."""
    e = os.environ if env is None else env
    raw = (e.get("APPLE_CALENDAR_MODE") or MODE_READ_ONLY).strip().lower()
    return MODE_READ_WRITE if raw == MODE_READ_WRITE else MODE_READ_ONLY


# ---------------------------------------------------------------------------
# Credentials — Keychain first, env fallback. Never store or log the value.
# ---------------------------------------------------------------------------
def _keychain_password(account: str, service: str) -> Optional[str]:
    """Read a password from the macOS Keychain, or None if unavailable.

    Uses `security find-generic-password -w`. Any failure (non-macOS, not found,
    permission) returns None so we can fall back to env. Errors are swallowed
    but their text is never surfaced with the secret.
    """
    try:
        result = subprocess.run(
            ["security", "find-generic-password",
             "-a", account, "-s", service, "-w"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    pw = (result.stdout or "").strip()
    return pw or None


def get_credentials(env: Optional[dict] = None) -> Credentials:
    """Resolve CalDAV credentials. FAIL CLOSED if password is missing.

    Order:
      1. macOS Keychain (service=hoch-agent-swarm-apple-caldav).
      2. Environment (APPLE_CALDAV_USERNAME / APPLE_CALDAV_PASSWORD / HOST).

    Raises :class:`SecurityError` (pre-redacted) if no password can be found.
    """
    e = os.environ if env is None else env
    username = (e.get("APPLE_CALDAV_USERNAME") or KEYCHAIN_ACCOUNT).strip()
    host = (e.get("APPLE_CALDAV_HOST") or DEFAULT_CALDAV_HOST).strip()

    password = _keychain_password(username or KEYCHAIN_ACCOUNT, KEYCHAIN_SERVICE)
    if not password:
        password = e.get("APPLE_CALDAV_PASSWORD") or ""

    if not password:
        # Fail closed. Do NOT echo any partial value.
        raise SecurityError(
            "Apple CalDAV credentials unavailable: no password in Keychain "
            "(service='hoch-agent-swarm-apple-caldav') or APPLE_CALDAV_PASSWORD."
        )
    if not username:
        raise SecurityError("Apple CalDAV username is missing; refusing to proceed.")

    return Credentials(username=username, password=password, host=host)


# ---------------------------------------------------------------------------
# Write gate — the single decision point for all mutations.
# ---------------------------------------------------------------------------
def evaluate_write_gate(
    *,
    mode: str,
    approval_token: Optional[str] = None,
    approved: bool = False,
) -> Tuple[bool, str]:
    """Decide whether a write may proceed. FAIL CLOSED.

    Returns ``(allowed, reason)``. A write is allowed ONLY when:
      * ``mode == 'read_write'`` AND
      * an approval token is present OR ``approved is True``.
    Any other combination is denied with a reason string safe to return.
    """
    if mode != MODE_READ_WRITE:
        return False, (
            "write rejected: adapter is in read_only mode "
            "(set APPLE_CALENDAR_MODE=read_write to enable writes)"
        )
    has_approval = bool(approval_token) or bool(approved)
    if not has_approval:
        return False, "write rejected: approval missing (approval_token or approved=true required)"
    return True, "write permitted: read_write mode with approval present"


# ---------------------------------------------------------------------------
# ICS builder — used by dry-run and (post-approval) create. Pure function.
# ---------------------------------------------------------------------------
def _ics_escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def _to_ics_dt(value: str) -> str:
    """Normalise an ISO-8601 string to an ICS UTC timestamp (fail closed)."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(
    *,
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None,
    uid: Optional[str] = None,
) -> str:
    """Produce a minimal VEVENT ICS payload. Does NOT touch the network."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev_uid = uid or f"{stamp}-{abs(hash((title, start, end))) & 0xFFFFFFFF}@hoch-agent-swarm"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Hoch Agent Swarm//Apple Calendar Adapter//EN",
        "BEGIN:VEVENT",
        f"UID:{ev_uid}",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{_to_ics_dt(start)}",
        f"DTEND:{_to_ics_dt(end)}",
        f"SUMMARY:{_ics_escape(title)}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{_ics_escape(description)}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------------------
# CalDAV client — imported LAZILY so this module works without the lib.
# ---------------------------------------------------------------------------
def _get_dav_client(creds: Credentials):
    """Construct a caldav client. Imports caldav lazily; redacts errors."""
    try:
        import caldav  # noqa: WPS433  (lazy on purpose)
    except ImportError as exc:  # pragma: no cover - depends on env
        raise SecurityError(
            "caldav library is not installed; cannot reach iCloud. "
            f"({redact_secret(str(exc))})"
        ) from None
    try:
        return caldav.DAVClient(
            url=creds.host, username=creds.username, password=creds.password
        )
    except Exception as exc:  # noqa: BLE001 - redact then re-raise clean
        raise SecurityError(
            f"failed to construct CalDAV client: {redact_secret(str(exc))}"
        ) from None


def discover_calendars(creds: Credentials) -> list[dict]:
    """List calendars (names/urls only). Redacts any secret in errors."""
    client = _get_dav_client(creds)
    try:
        principal = client.principal()
        cals = principal.calendars()
    except Exception as exc:  # noqa: BLE001
        raise SecurityError(
            f"calendar discovery failed: {redact_secret(str(exc))}"
        ) from None
    out = []
    for c in cals:
        name = getattr(c, "name", None) or str(getattr(c, "url", ""))
        out.append({"name": redact_secret(name), "url": redact_secret(str(getattr(c, "url", "")))})
    return out


def _find_calendar(creds: Credentials, calendar_name: Optional[str]):
    client = _get_dav_client(creds)
    principal = client.principal()
    cals = principal.calendars()
    if not cals:
        raise SecurityError("no calendars found for this iCloud account.")
    if calendar_name:
        for c in cals:
            if (getattr(c, "name", "") or "") == calendar_name:
                return c
        raise SecurityError(
            f"calendar '{redact_secret(calendar_name)}' not found; refusing to guess."
        )
    return cals[0]


def read_events(
    creds: Credentials,
    start: str,
    end: str,
    calendar_name: Optional[str] = None,
    approved: bool = False,
) -> list[dict]:
    """Read events in a window. Descriptions redacted unless ``approved``."""
    cal = _find_calendar(creds, calendar_name)
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as exc:
        raise SecurityError(f"invalid ISO datetime: {redact_secret(str(exc))}") from None
    try:
        results = cal.date_search(start=start_dt, end=end_dt, expand=True)
    except Exception as exc:  # noqa: BLE001
        raise SecurityError(f"event read failed: {redact_secret(str(exc))}") from None

    events = []
    for r in results:
        comp = getattr(r, "icalendar_component", None)
        if comp is None:
            continue
        events.append({
            "title": str(comp.get("summary", "")),
            "start": str(comp.get("dtstart").dt) if comp.get("dtstart") else None,
            "end": str(comp.get("dtend").dt) if comp.get("dtend") else None,
            "description": str(comp.get("description", "")) or None,
        })
    return redact_events(events, approved=approved)


# ---------------------------------------------------------------------------
# FastAPI wiring — guarded so import without fastapi still exposes the logic.
# ---------------------------------------------------------------------------
def create_app():
    """Construct and return the FastAPI application.

    Imported lazily inside this function so ``import app`` (and py_compile)
    succeed even when fastapi/pydantic are not installed. Call this from
    uvicorn: ``uvicorn services.apple_calendar_adapter.app:app``.
    """
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import JSONResponse

    from .models import EventCreateApproved, EventCreateRequest, DryRunResponse

    api = FastAPI(
        title="Hoch Agent Swarm — Apple Calendar Adapter",
        description="Local-only, read-only-by-default CalDAV adapter (127.0.0.1:8011).",
        version="0.1.0",
    )

    ledger_mod.init_ledger()

    def _safe_http(status: int, detail: str) -> HTTPException:
        return HTTPException(status_code=status, detail=redact_secret(detail))

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/apple/calendars")
    def calendars():
        try:
            creds = get_credentials()
            return {"calendars": discover_calendars(creds)}
        except SecurityError as exc:
            raise _safe_http(503, str(exc)) from None

    @api.get("/apple/events")
    def events(
        start: str = Query(..., description="ISO-8601 start"),
        end: str = Query(..., description="ISO-8601 end"),
        calendar_name: Optional[str] = Query(None),
        approved: bool = Query(False, description="Reveal descriptions (requires approval upstream)"),
    ):
        try:
            creds = get_credentials()
            evs = read_events(creds, start, end, calendar_name, approved=approved)
            return {"events": evs, "descriptions_included": bool(approved)}
        except SecurityError as exc:
            raise _safe_http(503, str(exc)) from None

    @api.post("/apple/events/dry-run", response_model=DryRunResponse)
    def dry_run(req: EventCreateRequest):
        # NEVER writes. Produces the proposed ICS only.
        ics = build_ics(
            title=req.title, start=req.start, end=req.end,
            description=req.description,
        )
        return DryRunResponse(calendar_name=req.calendar_name, ics=redact_secret(ics))

    @api.post("/apple/events")
    def create_event(req: EventCreateApproved):
        mode = resolve_mode()
        allowed, reason = evaluate_write_gate(
            mode=mode, approval_token=req.approval_token, approved=req.approved,
        )
        if not allowed:
            # Fail closed: record the denied attempt for audit, then 403.
            ledger_mod.record_attempt(
                action_type="create", approval_state=f"denied:{reason}",
                calendar_name=req.calendar_name, title=req.title,
                start_time=req.start, end_time=req.end,
                requested_by=req.requested_by,
            )
            raise _safe_http(403, reason)

        # Write to the ledger BEFORE execution.
        lid = ledger_mod.record_attempt(
            action_type="create", approval_state="approved",
            calendar_name=req.calendar_name, title=req.title,
            start_time=req.start, end_time=req.end,
            requested_by=req.requested_by,
        )
        try:
            creds = get_credentials()
            cal = _find_calendar(creds, req.calendar_name)
            ics = build_ics(
                title=req.title, start=req.start, end=req.end,
                description=req.description,
            )
            cal.save_event(ics)
            ledger_mod.update_result(lid, executed=True, result_payload=ics)
            return JSONResponse(
                {"created": True, "calendar_name": req.calendar_name,
                 "ledger_id": lid},
            )
        except SecurityError as exc:
            ledger_mod.update_result(lid, executed=False, error_summary=str(exc))
            raise _safe_http(503, str(exc)) from None
        except Exception as exc:  # noqa: BLE001
            ledger_mod.update_result(
                lid, executed=False, error_summary=redact_secret(str(exc)),
            )
            raise _safe_http(500, "event creation failed") from None

    # PATCH / DELETE are scaffolded but DISABLED (fail closed with 403).
    @api.patch("/apple/events/{event_id}")
    def update_event(event_id: str):
        raise _safe_http(403, "write disabled: update is not enabled in this build")

    @api.delete("/apple/events/{event_id}")
    def delete_event(event_id: str):
        raise _safe_http(403, "write disabled: delete is not enabled in this build")

    return api


# Lazy module-level app: only build when fastapi is importable. This lets
# uvicorn import `app` while keeping the module import-clean offline.
try:  # pragma: no cover - depends on environment
    import fastapi as _fastapi  # noqa: F401
    app = create_app()
except Exception:  # noqa: BLE001 - offline / no fastapi: expose logic only
    app = None


def main() -> None:  # pragma: no cover - runtime entrypoint
    import uvicorn
    uvicorn.run(
        "services.apple_calendar_adapter.app:app",
        host=BIND_HOST, port=BIND_PORT, reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
