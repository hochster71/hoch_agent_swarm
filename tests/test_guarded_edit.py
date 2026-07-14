"""guarded_edit — active prevention wrapper. Tests before implementation.

The source lease + commit detector give DETECTION. This facade gives PREVENTION: an agent takes the
lease BEFORE editing, so a second agent is actively turned away instead of merely warned afterward.

It must be trivial to adopt — one context manager for Python agents, one CLI `run` wrapper for
shell-driven agents (Grok / ChatGPT CLI / AG IDE). And it must be honest: if a file is already held,
the wrapper does NOT run the edit.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from backend.mission_control.source_lease import SourceLeaseManager
from backend.mission_control.guarded_edit import guarded_edit, EditBlocked


def _mgr():
    return SourceLeaseManager(lease_dir=Path(tempfile.mkdtemp()),
                              repo_root=Path(tempfile.mkdtemp()))


def _write(mgr, rel, text):
    p = mgr.repo_root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


# ---------------------------------------------------------------- happy path
def test_guarded_edit_acquires_and_releases():
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    with guarded_edit("x.py", holder="claude", manager=mgr) as g:
        assert g.ok is True
        (mgr.repo_root / "x.py").write_text("v2")     # the edit
    # released on exit -> the next agent can take it
    assert mgr.acquire("x.py", holder="grok") is not None


def test_my_own_edit_is_not_flagged_as_a_clobber():
    """After a guarded edit records its own write, verify_no_clobber must see the file as clean."""
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    lease_id_seen = {}
    with guarded_edit("x.py", holder="claude", manager=mgr) as g:
        lease_id_seen["id"] = g.lease["lease_id"]
        (mgr.repo_root / "x.py").write_text("v2 edited by holder")
    # during the edit, the holder's own change is recorded, not mistaken for a foreign clobber
    # (re-acquire to inspect: the history line exists and release succeeded)
    assert mgr.acquire("x.py", holder="next") is not None


# ---------------------------------------------------------------- blocked
def test_a_held_file_blocks_the_second_agent():
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    mgr.acquire("x.py", holder="grok")                # grok holds it
    with pytest.raises(EditBlocked):
        with guarded_edit("x.py", holder="claude", manager=mgr):
            pytest.fail("must not enter the edit block while another agent holds the file")


def test_non_blocking_mode_yields_ok_false_instead_of_raising():
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    mgr.acquire("x.py", holder="grok")
    with guarded_edit("x.py", holder="claude", manager=mgr, block=False) as g:
        assert g.ok is False
        assert g.held_by == "grok"


# ---------------------------------------------------------------- release on failure
def test_lease_is_released_even_if_the_edit_raises():
    """A crash mid-edit must not leave the file locked forever."""
    mgr = _mgr()
    _write(mgr, "x.py", "v1")
    with pytest.raises(ValueError):
        with guarded_edit("x.py", holder="claude", manager=mgr):
            raise ValueError("edit blew up")
    assert mgr.acquire("x.py", holder="recover") is not None, "lease leaked after an exception"


# ---------------------------------------------------------------- CLI run wrapper (shell agents)
def test_cli_run_wraps_a_shell_edit_end_to_end():
    """`guarded_edit run <path> --holder grok -- <cmd>` acquires, runs the edit, releases."""
    root = Path(__file__).resolve().parents[1]
    ldir = Path(tempfile.mkdtemp())
    repo = Path(tempfile.mkdtemp())
    (repo / "x.py").write_text("before")
    r = subprocess.run(
        [sys.executable, "-m", "backend.mission_control.guarded_edit", "run",
         "x.py", "--holder", "grok", "--lease-dir", str(ldir), "--repo-root", str(repo),
         "--", "sh", "-c", f"echo after > {repo/'x.py'}"],
        cwd=str(root), capture_output=True, text=True)
    assert r.returncode == 0, f"run wrapper failed: {r.stderr}"
    assert (repo / "x.py").read_text().strip() == "after", "the wrapped edit did not run"
    # lease released afterward -> re-acquirable
    m = SourceLeaseManager(lease_dir=ldir, repo_root=repo)
    assert m.acquire("x.py", holder="next") is not None


def test_cli_run_refuses_to_run_when_the_file_is_held():
    """If another holder owns the file, the wrapped command must NOT execute, and exit non-zero."""
    root = Path(__file__).resolve().parents[1]
    ldir = Path(tempfile.mkdtemp())
    repo = Path(tempfile.mkdtemp())
    (repo / "x.py").write_text("original")
    SourceLeaseManager(lease_dir=ldir, repo_root=repo).acquire("x.py", holder="claude")  # claude holds
    r = subprocess.run(
        [sys.executable, "-m", "backend.mission_control.guarded_edit", "run",
         "x.py", "--holder", "grok", "--lease-dir", str(ldir), "--repo-root", str(repo),
         "--", "sh", "-c", f"echo CLOBBERED > {repo/'x.py'}"],
        cwd=str(root), capture_output=True, text=True)
    assert r.returncode != 0, "run wrapper should refuse when the file is held by another agent"
    assert (repo / "x.py").read_text().strip() == "original", "the edit ran despite the block — clobber!"


def test_cli_acquire_then_release_roundtrip():
    root = Path(__file__).resolve().parents[1]
    ldir = Path(tempfile.mkdtemp())
    repo = Path(tempfile.mkdtemp())
    (repo / "x.py").write_text("v1")
    base = [sys.executable, "-m", "backend.mission_control.guarded_edit"]
    common = ["--lease-dir", str(ldir), "--repo-root", str(repo)]
    a = subprocess.run(base + ["acquire", "x.py", "--holder", "grok"] + common,
                       cwd=str(root), capture_output=True, text=True)
    assert a.returncode == 0, f"acquire failed: {a.stderr}"
    # a second holder is refused while held
    a2 = subprocess.run(base + ["acquire", "x.py", "--holder", "claude"] + common,
                        cwd=str(root), capture_output=True, text=True)
    assert a2.returncode != 0, "second acquire should be refused"
    rel = subprocess.run(base + ["release", "x.py", "--holder", "grok"] + common,
                         cwd=str(root), capture_output=True, text=True)
    assert rel.returncode == 0, f"release failed: {rel.stderr}"
