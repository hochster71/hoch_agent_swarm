"""Security tests for the Apple Calendar adapter — run FULLY OFFLINE.

These assert the fail-closed security posture without requiring fastapi,
pydantic, caldav, or any network. They import only the pure security-gate
functions from ``app`` and the ``redaction``/``ledger`` modules.

Asserted:
  * Missing credentials fail closed (SecurityError, no secret leaked).
  * The write gate rejects when mode != read_write OR approval is missing.
  * No security-facing surface returns the credential value.
"""

import importlib
import os

import pytest

app = importlib.import_module("services.apple_calendar_adapter.app")
SecurityError = app.SecurityError

FAKE_SECRET = "abcd-efgh-ijkl-mnop"  # not a real password


# ---------------------------------------------------------------------------
# Credentials fail closed
# ---------------------------------------------------------------------------
def test_missing_credentials_fail_closed(monkeypatch):
    """No Keychain hit + no env password => SecurityError (fail closed)."""
    # Force the Keychain lookup to miss so the test is deterministic offline.
    monkeypatch.setattr(app, "_keychain_password", lambda *a, **k: None)
    for var in ("APPLE_CALDAV_PASSWORD", "APPLE_CALDAV_USERNAME", "APPLE_CALDAV_HOST"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(SecurityError) as exc:
        app.get_credentials(env={})
    # The error must not contain any secret material.
    assert FAKE_SECRET not in str(exc.value)


def test_credentials_never_expose_password(monkeypatch):
    """When creds resolve, the redacted view must mask the password."""
    monkeypatch.setattr(app, "_keychain_password", lambda *a, **k: None)
    env = {
        "APPLE_CALDAV_USERNAME": "hochster_71@mac.com",
        "APPLE_CALDAV_PASSWORD": FAKE_SECRET,
        "APPLE_CALDAV_HOST": "https://caldav.icloud.com",
    }
    creds = app.get_credentials(env=env)
    redacted = creds.redacted()
    assert redacted["password"] == "***REDACTED***"
    assert FAKE_SECRET not in str(redacted)
    # The username/host are fine to expose; the secret is not.
    assert redacted["username"] == "hochster_71@mac.com"


# ---------------------------------------------------------------------------
# Write gate — fail closed on mode and approval
# ---------------------------------------------------------------------------
def test_write_rejected_in_read_only_mode():
    allowed, reason = app.evaluate_write_gate(
        mode="read_only", approval_token="tok", approved=True
    )
    assert allowed is False
    assert "read_only" in reason


def test_write_rejected_when_approval_missing():
    allowed, reason = app.evaluate_write_gate(
        mode="read_write", approval_token=None, approved=False
    )
    assert allowed is False
    assert "approval" in reason.lower()


def test_write_allowed_only_with_mode_and_approval():
    allowed_token, _ = app.evaluate_write_gate(
        mode="read_write", approval_token="tok", approved=False
    )
    allowed_flag, _ = app.evaluate_write_gate(
        mode="read_write", approval_token=None, approved=True
    )
    assert allowed_token is True
    assert allowed_flag is True


def test_ambiguous_mode_defaults_to_read_only():
    for raw in ("", "  ", "readwrite", "RW", "yes", "true", None):
        env = {} if raw is None else {"APPLE_CALENDAR_MODE": raw}
        assert app.resolve_mode(env=env) == "read_only"
    assert app.resolve_mode(env={"APPLE_CALENDAR_MODE": "read_write"}) == "read_write"
    # Case-insensitive match for the exact intended value.
    assert app.resolve_mode(env={"APPLE_CALENDAR_MODE": "READ_WRITE"}) == "read_write"


# ---------------------------------------------------------------------------
# No endpoint / logic path returns the secret
# ---------------------------------------------------------------------------
def test_binding_is_loopback_only():
    assert app.BIND_HOST == "127.0.0.1"
    assert app.BIND_HOST != "0.0.0.0"
    assert app.BIND_PORT == 8011


def test_disabled_write_gate_records_denied_attempt(tmp_path):
    """A denied write must be auditable and must not leak the secret."""
    ledger = importlib.import_module("services.apple_calendar_adapter.ledger")
    db = str(tmp_path / "ledger.sqlite3")
    lid = ledger.record_attempt(
        action_type="create",
        approval_state="denied:read_only",
        calendar_name="Home",
        title="Test",
        start_time="2026-07-07T10:00:00",
        end_time="2026-07-07T11:00:00",
        db_path=db,
    )
    entry = ledger.get_entry(lid, db_path=db)
    assert entry is not None
    assert entry["executed"] == 0
    assert FAKE_SECRET not in str(entry)


def test_error_summary_scrubs_secret(tmp_path, monkeypatch):
    """Even if a secret sneaks into an error, the ledger scrubs it."""
    ledger = importlib.import_module("services.apple_calendar_adapter.ledger")
    monkeypatch.setenv("APPLE_CALDAV_PASSWORD", FAKE_SECRET)
    db = str(tmp_path / "ledger.sqlite3")
    lid = ledger.record_attempt(
        action_type="create", approval_state="approved",
        title="X", db_path=db,
    )
    ledger.update_result(
        lid, executed=False,
        error_summary=f"connection failed with password {FAKE_SECRET}",
        db_path=db,
    )
    entry = ledger.get_entry(lid, db_path=db)
    assert FAKE_SECRET not in str(entry["error_summary"])
    assert "***REDACTED***" in entry["error_summary"]
