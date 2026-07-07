"""Append-only SQLite ledger for the Apple Calendar adapter.

Every mutating attempt (create/update/delete) is recorded BEFORE it is executed
so that a crash mid-write still leaves an auditable trace. The result is then
updated in place once the attempt resolves.

Pure stdlib (``sqlite3``). Importable and usable without ``caldav`` / ``fastapi``.

Security note: the ledger stores only titles + times + coarse metadata. It must
NEVER contain the app-specific password or raw event descriptions. Callers are
responsible for passing redacted values; as defence in depth we scrub secrets
from ``error_summary`` via :func:`redaction.redact_secret`.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

try:  # pragma: no cover - trivial import shim
    from .redaction import redact_secret
except ImportError:  # allow flat-module import in some test harnesses
    from redaction import redact_secret  # type: ignore

# Ledger lives alongside this module so it is self-contained per the spec.
_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "apple_calendar_ledger.sqlite3",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS apple_calendar_ledger (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc  TEXT    NOT NULL,
    action_type    TEXT    NOT NULL,
    calendar_name  TEXT,
    title          TEXT,
    start_time     TEXT,
    end_time       TEXT,
    requested_by   TEXT,
    approval_state TEXT    NOT NULL,
    executed       INTEGER NOT NULL DEFAULT 0,
    result_hash    TEXT,
    error_summary  TEXT
);
"""

_lock = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_ledger(db_path: Optional[str] = None) -> str:
    """Ensure the ledger DB + schema exist. Returns the resolved path."""
    path = db_path or _DEFAULT_DB_PATH
    with _lock:
        conn = _connect(path)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()
    return path


def record_attempt(
    *,
    action_type: str,
    approval_state: str,
    calendar_name: Optional[str] = None,
    title: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    requested_by: Optional[str] = None,
    db_path: Optional[str] = None,
) -> int:
    """Insert a pending (executed=0) ledger row BEFORE execution.

    Returns the new row id, used later by :func:`update_result`.
    """
    path = init_ledger(db_path)
    with _lock:
        conn = _connect(path)
        try:
            cur = conn.execute(
                """
                INSERT INTO apple_calendar_ledger
                    (timestamp_utc, action_type, calendar_name, title,
                     start_time, end_time, requested_by, approval_state,
                     executed, result_hash, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)
                """,
                (
                    _utc_now_iso(),
                    action_type,
                    calendar_name,
                    title,
                    start_time,
                    end_time,
                    requested_by,
                    approval_state,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()


def update_result(
    ledger_id: int,
    *,
    executed: bool,
    result_payload: Optional[str] = None,
    error_summary: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Update a ledger row after execution resolves.

    ``result_payload`` is hashed (never stored raw) so the ledger records that
    *something specific* happened without persisting event bodies. Any error
    summary is scrubbed of secrets before storage.
    """
    path = init_ledger(db_path)
    result_hash = None
    if result_payload is not None:
        result_hash = hashlib.sha256(result_payload.encode("utf-8")).hexdigest()
    safe_error = redact_secret(error_summary) if error_summary is not None else None
    with _lock:
        conn = _connect(path)
        try:
            conn.execute(
                """
                UPDATE apple_calendar_ledger
                   SET executed = ?, result_hash = ?, error_summary = ?
                 WHERE id = ?
                """,
                (1 if executed else 0, result_hash, safe_error, ledger_id),
            )
            conn.commit()
        finally:
            conn.close()


def get_entry(ledger_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    """Fetch a single ledger row as a dict (for tests / audit)."""
    path = init_ledger(db_path)
    with _lock:
        conn = _connect(path)
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM apple_calendar_ledger WHERE id = ?",
                (ledger_id,),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()
