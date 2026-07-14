"""Source-tree coordination guard — the test comes BEFORE the implementation.

WHY THIS EXISTS
---------------
On 2026-07-14 two agents (a Claude agent and a Grok agent) edited the SAME source files
(backend/helm_live_api.py, frontend_live/command.html) at the same time, with no mutual exclusion.
It happened to merge cleanly — but nothing prevented a lost write or a corrupted mid-write, and
nothing recorded that two writers had touched the same file. That is the SAME class of defect as the
split-brain scheduler: the AU-9 chain enforces a single writer on the EVIDENCE plane, but there was
no equivalent guard on the SOURCE tree.

TWO LAYERS, HONESTLY SCOPED
---------------------------
1. A file lease gives mutual exclusion to agents that ACQUIRE it. It cannot stop a non-participating
   editor from writing — claiming otherwise would be theatre.
2. A fail-closed detector at the commit boundary (the one gate every agent passes through) catches a
   write to a file held by ANOTHER holder, even if that writer never took a lease. Detectable-but-not-
   always-prevented is exactly what AU-9 is: it does not stop tampering, it makes it impossible to hide.

These tests fail until both layers exist. They are the definition of done.
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.mission_control.source_lease import SourceLeaseManager        # does not exist yet
from backend.mission_control.detect_source_conflicts import (              # does not exist yet
    check_paths_against_leases,
)


def _mgr():
    return SourceLeaseManager(lease_dir=Path(tempfile.mkdtemp()),
                              repo_root=Path(tempfile.mkdtemp()))


def _write(mgr, rel, text):
    p = mgr.repo_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


# ---------------------------------------------------------------- mutual exclusion
def test_a_second_agent_cannot_acquire_a_held_file():
    """THE CLOBBER. Agent A holds command.html; agent B must be told NO, not silently proceed."""
    mgr = _mgr()
    _write(mgr, "frontend_live/command.html", "<html>v1</html>")
    a = mgr.acquire("frontend_live/command.html", holder="claude")
    assert a is not None
    b = mgr.acquire("frontend_live/command.html", holder="grok")
    assert b is None, "two agents hold the same source file — this is the clobber the guard must stop"


def test_unrelated_files_never_contend():
    """The whole point of per-FILE (not global) leasing: two agents edit two files in parallel."""
    mgr = _mgr()
    _write(mgr, "a.py", "a"); _write(mgr, "b.py", "b")
    assert mgr.acquire("a.py", holder="claude") is not None
    assert mgr.acquire("b.py", holder="grok") is not None, "distinct files must not block each other"


def test_release_lets_the_next_agent_in():
    mgr = _mgr()
    _write(mgr, "x.py", "x")
    a = mgr.acquire("x.py", holder="claude")
    assert mgr.release("x.py", a["lease_id"]) is True
    assert mgr.acquire("x.py", holder="grok") is not None, "released file must be re-acquirable"


def test_release_is_honest_on_mismatch():
    """A release that did not remove the lock must return False — never report a success it did not do."""
    mgr = _mgr()
    _write(mgr, "x.py", "x")
    mgr.acquire("x.py", holder="claude")
    assert mgr.release("x.py", "not-the-real-lease-id") is False


# ---------------------------------------------------------------- injective paths
def test_distinct_paths_get_distinct_locks_even_when_sanitized_alike():
    """'a/b.py' and 'ab.py' must NOT collide onto one lock (the GROK-F3 defect, source edition)."""
    mgr = _mgr()
    _write(mgr, "a/b.py", "1"); _write(mgr, "ab.py", "2")
    assert mgr.acquire("a/b.py", holder="claude") is not None
    assert mgr.acquire("ab.py", holder="grok") is not None, "path sanitization collided two files"


# ---------------------------------------------------------------- TTL reclaim
def _expire(mgr, rel, minutes_ago=30):
    p = mgr._path(rel)
    rec = json.loads(p.read_text())
    past = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    rec["acquired_at"] = past.isoformat()
    rec["expires_at"] = (past + timedelta(minutes=10)).isoformat()
    p.write_text(json.dumps(rec))


def test_a_dead_agents_file_lease_is_reclaimed():
    """A crashed agent must not lock a file forever. TTL must be ENFORCED, not decorative."""
    mgr = _mgr()
    _write(mgr, "x.py", "x")
    mgr.acquire("x.py", holder="dead-agent")
    _expire(mgr, "x.py", minutes_ago=45)
    out = mgr.reclaim_expired()
    assert any(r.get("status") == "TIMED_OUT" for r in out)
    assert mgr.acquire("x.py", holder="new-agent") is not None, "expired lease was never freed"


def test_a_live_file_lease_is_never_reclaimed():
    mgr = _mgr()
    _write(mgr, "x.py", "x")
    mgr.acquire("x.py", holder="working")
    assert mgr.reclaim_expired() == []


# ---------------------------------------------------------------- fencing
def test_stale_writer_is_fenced_out():
    """A reclaimed-then-reacquired file mints a strictly greater token; the old token is rejected."""
    mgr = _mgr()
    _write(mgr, "x.py", "x")
    old = mgr.acquire("x.py", holder="a")
    _expire(mgr, "x.py", minutes_ago=45)
    mgr.reclaim_expired()
    new = mgr.acquire("x.py", holder="b")
    assert new["fencing_token"] > old["fencing_token"]
    assert mgr.validate_fence("x.py", old["fencing_token"]) is False, "stale token still validates"
    assert mgr.validate_fence("x.py", new["fencing_token"]) is True


# ---------------------------------------------------------------- corrupt lock
def test_corrupt_lock_is_quarantined_not_fatal():
    mgr = _mgr()
    _write(mgr, "x.py", "x")
    mgr._path("x.py").write_text("not json {{{")
    out = mgr.reclaim_expired()                     # must not raise
    assert any(r.get("status") == "CORRUPT_QUARANTINED" for r in out)
    assert mgr.acquire("x.py", holder="recover") is not None, "corrupt lock left file unacquirable"


# ---------------------------------------------------------------- clobber detection (content hash)
def test_clobber_by_a_non_holder_is_detected():
    """Agent A holds the lease; someone edits the file anyway. verify_no_clobber must catch it."""
    mgr = _mgr()
    p = _write(mgr, "x.py", "original")
    a = mgr.acquire("x.py", holder="claude")
    ok, _ = mgr.verify_no_clobber("x.py", a["lease_id"])
    assert ok is True, "no edit happened yet — must be clean"
    p.write_text("SOMEONE ELSE OVERWROTE THIS")      # a non-holder clobbers the file
    ok, reason = mgr.verify_no_clobber("x.py", a["lease_id"])
    assert ok is False and "clobber" in reason.lower(), "content changed under the holder, undetected"


# ---------------------------------------------------------------- commit-boundary detector (fail closed)
def test_commit_of_a_file_held_by_another_holder_is_flagged():
    """The enforcement teeth: at `git commit`, a staged file under ANOTHER holder's active lease is a
    CONFLICT. This works even if the committing agent never took a lease — because everyone commits."""
    mgr = _mgr()
    _write(mgr, "frontend_live/command.html", "v1")
    mgr.acquire("frontend_live/command.html", holder="grok")     # Grok holds it
    # Claude tries to commit a change to the same file
    conflicts = check_paths_against_leases(
        ["frontend_live/command.html"], committer="claude", manager=mgr)
    assert conflicts, "committing over another holder's active lease was not flagged"
    assert conflicts[0]["held_by"] == "grok"
    assert conflicts[0]["path"] == "frontend_live/command.html"


def test_committer_may_commit_a_file_it_holds_itself():
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    mgr.acquire("x.py", holder="claude")
    conflicts = check_paths_against_leases(["x.py"], committer="claude", manager=mgr)
    assert conflicts == [], "an agent was blocked from committing a file it legitimately holds"


def test_unheld_file_commits_freely():
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    conflicts = check_paths_against_leases(["x.py"], committer="claude", manager=mgr)
    assert conflicts == [], "a file under no lease must commit without friction"


def test_expired_lease_does_not_block_a_commit():
    """A dead agent's expired lease must not wedge the whole team's ability to commit."""
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    mgr.acquire("x.py", holder="dead")
    _expire(mgr, "x.py", minutes_ago=45)
    conflicts = check_paths_against_leases(["x.py"], committer="claude", manager=mgr)
    assert conflicts == [], "an EXPIRED lease should not block commits (it is reclaimable)"


# ---------------------------------------------------------------- standalone invocation (regression)
def test_detector_runs_as_a_standalone_script_without_import_error():
    """REGRESSION: run as a git hook (`python3 backend/mission_control/detect_source_conflicts.py`) the
    package root is not on sys.path, so `import backend...` raised ModuleNotFoundError and the hook
    crashed with exit 1 — which in warn mode would BLOCK every commit on the guard's own bug. The unit
    tests missed it because pytest adds the root. This runs the real entrypoint in a clean subprocess."""
    import subprocess
    import sys as _sys
    root = Path(__file__).resolve().parents[1]
    script = root / "backend" / "mission_control" / "detect_source_conflicts.py"
    # empty index (no staged paths) -> must exit 0 cleanly, and must NOT emit an import traceback
    r = subprocess.run([_sys.executable, str(script)], cwd=str(root),
                       capture_output=True, text=True)
    assert "ModuleNotFoundError" not in r.stderr, f"standalone import regressed:\n{r.stderr}"
    assert r.returncode in (0, 1), f"unexpected crash exit {r.returncode}:\n{r.stderr}"


def test_internal_error_fails_open_in_warn_mode(monkeypatch, tmp_path):
    """A bug inside the guard must not block commits in warn mode (false-red). It blocks only in strict."""
    import backend.mission_control.detect_source_conflicts as det
    monkeypatch.setattr(det, "_staged_paths", lambda: ["x.py"])
    monkeypatch.setattr(det, "check_paths_against_leases",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.delenv("HELM_SOURCE_LEASE_STRICT", raising=False)
    assert det.main() == 0, "warn mode must fail OPEN on an internal guard error"
    monkeypatch.setenv("HELM_SOURCE_LEASE_STRICT", "1")
    assert det.main() == 1, "strict mode must fail CLOSED on an internal guard error"
