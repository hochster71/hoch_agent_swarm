"""Redaction tests for the Apple Calendar adapter — run FULLY OFFLINE.

Assert:
  * ``redact_secret`` never emits the APPLE_CALDAV_PASSWORD value.
  * Event descriptions are hidden unless explicitly approved.

Pure stdlib + pytest; no fastapi/pydantic/caldav/network required.
"""

import importlib

import pytest

redaction = importlib.import_module("services.apple_calendar_adapter.redaction")

SECRET = "s3cr3t-app-specific-pw-1234"


@pytest.fixture(autouse=True)
def _set_secret(monkeypatch):
    monkeypatch.setenv("APPLE_CALDAV_PASSWORD", SECRET)


# ---------------------------------------------------------------------------
# redact_secret
# ---------------------------------------------------------------------------
def test_redact_secret_removes_password_anywhere():
    text = f"caldav failed: url=https://u:{SECRET}@caldav.icloud.com body {SECRET}"
    out = redaction.redact_secret(text)
    assert SECRET not in out
    assert out.count("***REDACTED***") >= 1


def test_redact_secret_handles_non_str():
    class Boom(Exception):
        pass

    exc = Boom(f"auth error {SECRET}")
    out = redaction.redact_secret(exc)
    assert SECRET not in out
    assert isinstance(out, str)


def test_redact_secret_no_secret_set_is_passthrough(monkeypatch):
    monkeypatch.delenv("APPLE_CALDAV_PASSWORD", raising=False)
    # Also clear defensive vars so nothing is scrubbed.
    for v in ("APPLE_APP_SPECIFIC_PASSWORD", "CALDAV_PASSWORD"):
        monkeypatch.delenv(v, raising=False)
    assert redaction.redact_secret("hello world") == "hello world"


def test_redact_secret_never_returns_the_value_even_partial():
    out = redaction.redact_secret(SECRET)
    assert out == "***REDACTED***"
    assert SECRET not in out


# ---------------------------------------------------------------------------
# redact_event
# ---------------------------------------------------------------------------
def _event():
    return {
        "title": "1:1 with Sam",
        "start": "2026-07-07T10:00:00",
        "end": "2026-07-07T10:30:00",
        "description": "Discuss confidential comp numbers",
    }


def test_description_hidden_by_default():
    out = redaction.redact_event(_event())
    assert "description" not in out
    assert out.get("description_redacted") is True
    # Title and times survive.
    assert out["title"] == "1:1 with Sam"
    assert out["start"] == "2026-07-07T10:00:00"


def test_description_revealed_when_approved():
    out = redaction.redact_event(_event(), approved=True)
    assert out["description"] == "Discuss confidential comp numbers"
    assert "description_redacted" not in out


def test_redact_event_scrubs_secret_leaked_into_field():
    ev = _event()
    ev["title"] = f"call {SECRET}"
    out = redaction.redact_event(ev)
    assert SECRET not in str(out)


def test_body_and_notes_also_hidden():
    ev = {"title": "T", "body": "secret body", "notes": "secret notes"}
    out = redaction.redact_event(ev)
    assert "body" not in out
    assert "notes" not in out
    assert out.get("description_redacted") is True


def test_redact_events_bulk_default_hides_all():
    evs = [_event(), _event()]
    out = redaction.redact_events(evs)
    assert all("description" not in e for e in out)
    assert all(e.get("description_redacted") is True for e in out)


def test_input_event_not_mutated():
    ev = _event()
    redaction.redact_event(ev)
    # Original still has its description — function returns a copy.
    assert ev["description"] == "Discuss confidential comp numbers"
