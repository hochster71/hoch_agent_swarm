"""Regression: the runtime-truth collector must not hold the swarm_ledger.db write lock
across its slow collection work.

Root cause (2026-07-18): collect_and_store_all() opened ONE implicit write transaction at
its first INSERT and did not commit until ~940 lines later, holding the write lock across
a `git status` subprocess + a model-health network scan + socket probes. A `git status`
with no timeout could hang and pin the lock INDEFINITELY, so every other writer (the
executive loop, the seeder) got 'database is locked'. Fix: autocommit connection
(isolation_level=None) so each write is its own short transaction, plus a bounded git
subprocess. These tests prove the properties the fix restores, fast and deterministically.
"""
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

import pytest


def _make_db():
    db = Path(tempfile.mkdtemp()) / "wl.db"
    c = sqlite3.connect(str(db))
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT)")
    c.commit()
    c.close()
    return db


def test_deferred_transaction_holds_lock_but_autocommit_does_not():
    """The heart of the defect and its fix, side by side on one temp DB.

    A writer that does an INSERT under the DEFAULT isolation level and then does slow work
    WITHOUT committing holds the write lock (a concurrent writer times out). The SAME
    pattern with isolation_level=None (the fix) releases the lock immediately, so the
    concurrent writer succeeds."""
    db = _make_db()

    # OLD behavior: default isolation_level -> INSERT opens a txn held across slow work.
    holder = sqlite3.connect(str(db), timeout=1)
    holder.execute("INSERT INTO t(v) VALUES('holder')")  # opens implicit write txn, NOT committed
    other = sqlite3.connect(str(db), timeout=1)
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        other.execute("INSERT INTO t(v) VALUES('other')")  # blocked by the held txn
    other.close()
    holder.rollback()
    holder.close()

    # FIXED behavior: autocommit -> the write is committed immediately, lock released.
    holder2 = sqlite3.connect(str(db), timeout=1, isolation_level=None)
    holder2.execute("INSERT INTO t(v) VALUES('holder2')")  # auto-committed, no lingering txn
    other2 = sqlite3.connect(str(db), timeout=2, isolation_level=None)
    other2.execute("INSERT INTO t(v) VALUES('other2')")     # SUCCEEDS — lock was released
    other2.commit()
    n = other2.execute("SELECT count(*) FROM t").fetchone()[0]
    other2.close()
    holder2.close()
    # holder (block 1) was rolled back; only holder2 + other2 committed under autocommit.
    assert n == 2


def test_autocommit_writer_does_not_block_during_slow_work():
    """Simulates the collector: an autocommit writer that does a slow (blocking) step
    between writes must NOT hold the lock during that step — a concurrent writer gets in."""
    db = _make_db()
    result = {}

    def collector_like():
        conn = sqlite3.connect(str(db), timeout=5, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("INSERT INTO t(v) VALUES('signal-1')")  # committed immediately
        time.sleep(2.0)                                       # slow collection (git/network)
        conn.execute("INSERT INTO t(v) VALUES('signal-2')")
        conn.close()

    def concurrent_writer():
        time.sleep(0.5)  # land in the middle of the collector's slow step
        t0 = time.time()
        conn = sqlite3.connect(str(db), timeout=3, isolation_level=None)
        conn.execute("INSERT INTO t(v) VALUES('concurrent')")
        conn.close()
        result["waited"] = time.time() - t0

    c = threading.Thread(target=collector_like)
    w = threading.Thread(target=concurrent_writer)
    c.start(); w.start(); c.join(); w.join()

    # The concurrent write must have completed quickly (lock was free during the sleep),
    # NOT waited the full ~1.5s remaining slow step.
    assert "waited" in result, "concurrent writer never completed"
    assert result["waited"] < 1.0, f"writer waited {result['waited']:.2f}s — lock was held during slow work"


def test_collect_git_status_uses_a_timeout():
    """The `git status` subprocess must be bounded so it cannot hang the collector."""
    import backend.runtime_truth.collector as collector

    captured = {}
    real_run = collector.subprocess.run

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        class R:  # minimal stand-in
            stdout = ""
        return R()

    collector.subprocess.run = fake_run
    try:
        collector.collect_git_status()
    finally:
        collector.subprocess.run = real_run

    assert "timeout" in captured, "collect_git_status must pass a timeout to subprocess.run"
    assert captured["timeout"] and captured["timeout"] <= 30
