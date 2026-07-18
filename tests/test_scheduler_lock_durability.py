"""Durability regression: the executive loop must NOT die on 'database is locked'.

On 2026-07-15 the council daemon's cycle 506 crashed with `sqlite3.OperationalError:
database is locked` and the loop stopped — HELM was "not operational" by the founder's
definition (a core runtime that fails under normal concurrent workload). The fix is the
retry-on-locked layer in persistent_scheduler.py (`_with_locked_retry`). These tests
prove the property that regression would break, and run fast (no 30s waits).

Manual heavy proof (a real 33s lock hold vs. the live busy_timeout) lives in the PR
notes; here we cover the retry LOGIC deterministically plus one short integration.
"""
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

import pytest

from backend.mission_control.persistent_scheduler import _sqlite_connect, _with_locked_retry


def test_retry_helper_retries_then_succeeds():
    """A transient 'database is locked' is retried, not surfaced as a failure."""
    calls = {"n": 0}

    def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise sqlite3.OperationalError("database is locked")
        return "committed"

    assert _with_locked_retry(op, what="unit", attempts=5, base=0.001) == "committed"
    assert calls["n"] == 3  # failed twice, succeeded on the third


def test_retry_helper_does_not_hide_real_errors():
    """A NON-lock OperationalError (e.g. a real schema bug) must surface immediately."""
    def op():
        raise sqlite3.OperationalError("no such table: mission_control_tasks")

    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        _with_locked_retry(op, what="unit", attempts=5, base=0.001)


def test_retry_helper_is_bounded():
    """A persistent lock (genuine deadlock) must eventually re-raise, never hang forever."""
    def op():
        raise sqlite3.OperationalError("database is locked")

    with pytest.raises(sqlite3.OperationalError, match="locked"):
        _with_locked_retry(op, what="unit", attempts=3, base=0.001)


def test_wrapped_write_survives_a_held_lock():
    """Integration: with a peer holding the write lock briefly, the retry-wrapped write
    still lands. A bare connection is NOT tested for failure here (that needs a >30s hold
    to beat busy_timeout); this proves the wrapped path completes under real contention."""
    db = Path(tempfile.mkdtemp()) / "dur.db"
    c = _sqlite_connect(db)
    c.execute("CREATE TABLE mission_control_tasks(task_id TEXT PRIMARY KEY, status TEXT)")
    c.execute("INSERT INTO mission_control_tasks VALUES('T1','PENDING')")
    c.commit()
    c.close()

    def peer_holds_lock():
        conn = sqlite3.connect(str(db), timeout=30)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO mission_control_tasks VALUES('PEER','X')")
        time.sleep(1.5)
        conn.commit()
        conn.close()

    holder = threading.Thread(target=peer_holds_lock)
    holder.start()
    time.sleep(0.2)  # ensure the peer owns the lock first

    def _persist():
        conn = _sqlite_connect(db)
        try:
            conn.execute("UPDATE mission_control_tasks SET status='COMPLETED' WHERE task_id='T1'")
            conn.commit()
        finally:
            conn.close()

    _with_locked_retry(_persist, what="integration")
    holder.join()

    verify = _sqlite_connect(db)
    row = verify.execute("SELECT status FROM mission_control_tasks WHERE task_id='T1'").fetchone()
    verify.close()
    assert row[0] == "COMPLETED"
