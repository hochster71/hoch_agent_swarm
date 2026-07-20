"""Adversarial tests for integration_state() — the delivery checker.

This function shipped two false-verdict bugs within an hour of being written:
an abbreviated SHA reported INTEGRATED for a commit nobody wrote, and a
branch-scoped miss reported LOCAL_VERIFIED for work already on a remote.

Both are now fixed. These tests exist so they cannot come back, and so the checker
is held to the same standard it imposes on everything else.

Tests run against real repository state and skip rather than assert when the
repository cannot supply a fixture — a skipped test is honest; a test that passes
because its precondition vanished is not.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.mission_envelope import (  # noqa: E402
    INTEGRATION_AMBIGUOUS, INTEGRATION_ELSEWHERE, INTEGRATION_INTEGRATED,
    INTEGRATION_LOCAL, INTEGRATION_UNKNOWN, integration_state,
)


def _git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _head_full() -> str:
    return _git("rev-parse", "HEAD")


def _current_remote_branch() -> str:
    """A remote branch containing HEAD, or '' if none."""
    out = _git("branch", "-r", "--contains", _head_full())
    for line in out.splitlines():
        line = line.strip()
        if line and "->" not in line:
            return line
    return ""


# --- defect 1: abbreviated SHA must never yield a verdict ---------------------

@pytest.mark.parametrize("abbrev", ["5877ffa1", "abc1234", "a9733b70", "", "HEAD", "main"])
def test_abbreviated_or_symbolic_ref_is_refused(abbrev):
    """Git resolves unique prefixes; a prefix verdict is not a commit verdict."""
    assert integration_state(abbrev)["state"] == INTEGRATION_AMBIGUOUS


def test_full_sha_of_head_is_not_ambiguous():
    """Green must stay reachable, or the guard is just a wall."""
    head = _head_full()
    if not head:
        pytest.skip("not a git repository")
    assert integration_state(head)["state"] != INTEGRATION_AMBIGUOUS


def test_abbreviated_allowed_only_with_explicit_optin():
    head = _head_full()
    if not head:
        pytest.skip("not a git repository")
    short = head[:8]
    assert integration_state(short)["state"] == INTEGRATION_AMBIGUOUS
    opted = integration_state(short, allow_abbreviated=True)
    assert opted["state"] != INTEGRATION_AMBIGUOUS


# --- defect 2: scope must not be confused with absence ------------------------

def test_commit_on_a_remote_but_not_target_is_elsewhere_not_local():
    """The bug that produced a wrong 'push your security fixes' instruction."""
    head = _head_full()
    if not head or not _current_remote_branch():
        pytest.skip("HEAD is not on any remote branch in this checkout")
    r = integration_state(head, "a-branch-name-that-does-not-exist")
    assert r["state"] == INTEGRATION_ELSEWHERE
    assert r["state"] != INTEGRATION_LOCAL
    assert r["remotes"], "must name where it actually lives"


def test_commit_on_target_branch_is_integrated():
    head = _head_full()
    branch = _current_remote_branch()
    if not branch:
        pytest.skip("HEAD is not on any remote branch in this checkout")
    # strip the remote prefix: 'github/foo' -> 'foo'
    target = branch.split("/", 1)[1] if "/" in branch else branch
    assert integration_state(head, target)["state"] == INTEGRATION_INTEGRATED


def test_unscoped_query_accepts_any_remote():
    head = _head_full()
    if not head or not _current_remote_branch():
        pytest.skip("HEAD is not on any remote branch in this checkout")
    assert integration_state(head)["state"] == INTEGRATION_INTEGRATED


# --- absence and failure ------------------------------------------------------

def test_nonexistent_full_sha_is_unknown_not_local():
    """A commit nobody wrote is UNKNOWN. It is not 'local work awaiting push'."""
    fake = "0" * 40
    assert integration_state(fake)["state"] == INTEGRATION_UNKNOWN


def test_the_two_phase_d_shas_do_not_share_a_verdict():
    """Founder-preserved discrepancy, 2026-07-20. Same 8-char prefix, different commits."""
    real = "5877ffa1c440a42ad6b5ca311312e8eb99b7e188"
    mistyped = "5877ffa11c97a55eaef9ceb970a2569de0c09199"
    assert real[:8] == mistyped[:8], "fixture invalid — the prefix collision is the point"
    a = integration_state(real)["state"]
    b = integration_state(mistyped)["state"]
    if a == INTEGRATION_UNKNOWN:
        pytest.skip("neither Phase D commit is present in this checkout")
    assert b == INTEGRATION_UNKNOWN
    assert a != b, "a real and a nonexistent commit must not report the same state"


def test_broken_repo_path_fails_toward_doubt(tmp_path):
    """No git repository must yield UNKNOWN, never a delivery claim."""
    r = integration_state("0" * 40, root=tmp_path)
    assert r["state"] == INTEGRATION_UNKNOWN


def test_state_never_silently_absent():
    """Every return path must carry a state and a human-readable detail."""
    for sha in ["short", "0" * 40, _head_full() or "0" * 40]:
        r = integration_state(sha)
        assert r.get("state"), f"no state for {sha!r}"
        assert r.get("detail"), f"no detail for {sha!r}"
