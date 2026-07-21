"""authority_gate — transition-predicate tests (PROTO-EXP-002).

The property under test is that the gate CANNOT resume on anything less than positive
observation. The dangerous failure is not a wrong answer; it is the three-valued verdict
silently collapsing to Boolean under a later refactor, at which point "we could not look"
becomes either "absent" (stalls forever on a network blip) or "present" (resumes on
ignorance). Both are worse than blocking.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.authority_gate as ag  # noqa: E402


def _stub(bp_state, cs_state, monkeypatch):
    monkeypatch.setattr(ag, "observe_branch_protection",
                        lambda *a, **k: {"control": "RC23-BRANCH-PROTECTION", "state": bp_state})
    monkeypatch.setattr(ag, "observe_commit_signing",
                        lambda *a, **k: {"control": "COMMIT-SIGNING", "state": cs_state})


# --- the three-valued verdict --------------------------------------------------

def test_both_present_is_the_ONLY_path_to_resume(monkeypatch):
    _stub("OBSERVED_PRESENT", "OBSERVED_PRESENT", monkeypatch)
    assert ag.resume_eligible()["verdict"] == "RESUME_ELIGIBLE"


@pytest.mark.parametrize("bp,cs", [
    ("OBSERVED_ABSENT", "OBSERVED_ABSENT"),
    ("OBSERVED_PRESENT", "OBSERVED_ABSENT"),
    ("OBSERVED_ABSENT", "OBSERVED_PRESENT"),
])
def test_any_absent_control_blocks(bp, cs, monkeypatch):
    """Partial authority is not authority. One enabled control does not open the gate."""
    _stub(bp, cs, monkeypatch)
    assert ag.resume_eligible()["verdict"] == "BLOCKED_AWAITING_AUTHORITY"


@pytest.mark.parametrize("bp,cs", [
    ("UNOBSERVED", "OBSERVED_PRESENT"),
    ("OBSERVED_PRESENT", "UNOBSERVED"),
    ("UNOBSERVED", "UNOBSERVED"),
    ("UNOBSERVED", "OBSERVED_ABSENT"),
])
def test_UNOBSERVED_yields_UNKNOWN_never_BLOCKED_never_ELIGIBLE(bp, cs, monkeypatch):
    """THE guard. 'We could not look' is neither 'absent' nor 'present'.

    Collapsing UNOBSERVED into BLOCKED makes the gate stall forever after a transient
    auth or network failure. Collapsing it into PRESENT resumes the protocol on ignorance,
    which would make the authority boundary the one unverified link in the chain.
    """
    _stub(bp, cs, monkeypatch)
    v = ag.resume_eligible()["verdict"]
    assert v == "UNKNOWN"
    assert v not in ("RESUME_ELIGIBLE", "BLOCKED_AWAITING_AUTHORITY")


def test_unobserved_dominates_even_when_the_other_control_is_present(monkeypatch):
    """An UNKNOWN cannot be outvoted by a positive observation elsewhere."""
    _stub("OBSERVED_PRESENT", "UNOBSERVED", monkeypatch)
    assert ag.resume_eligible()["verdict"] == "UNKNOWN"


def test_exactly_three_verdicts_exist(monkeypatch):
    seen = set()
    for bp, cs in [("OBSERVED_PRESENT", "OBSERVED_PRESENT"),
                   ("OBSERVED_ABSENT", "OBSERVED_ABSENT"),
                   ("UNOBSERVED", "UNOBSERVED")]:
        _stub(bp, cs, monkeypatch)
        seen.add(ag.resume_eligible()["verdict"])
    assert seen == {"RESUME_ELIGIBLE", "BLOCKED_AWAITING_AUTHORITY", "UNKNOWN"}


# --- unreachable API must not be read as absence -------------------------------

def test_api_failure_is_UNOBSERVED_not_OBSERVED_ABSENT(monkeypatch):
    """A non-404 failure means we did not reach an authoritative answer."""
    monkeypatch.setattr(ag, "_gh", lambda p: (False, "connection refused"))
    assert ag.observe_branch_protection()["state"] == "UNOBSERVED"


def test_explicit_404_IS_authoritative_absence(monkeypatch):
    """GitHub answering 'not protected' is a real observation, not a failure to observe."""
    monkeypatch.setattr(ag, "_gh", lambda p: (True, None))
    assert ag.observe_branch_protection()["state"] == "OBSERVED_ABSENT"


def test_git_failure_is_UNOBSERVED(monkeypatch):
    class R:
        returncode, stdout, stderr = 128, "", "not a git repository"
    monkeypatch.setattr(ag.subprocess, "run", lambda *a, **k: R())
    assert ag.observe_commit_signing()["state"] == "UNOBSERVED"


def test_untrusted_signature_still_counts_as_present(monkeypatch):
    """%G? U = signed by an untrusted key. Signing IS configured; whether the key is
    authorized is GOV-007's question, not this gate's."""
    class R:
        returncode, stdout, stderr = 0, "U\nU\nN\n", ""
    monkeypatch.setattr(ag.subprocess, "run", lambda *a, **k: R())
    r = ag.observe_commit_signing()
    assert r["state"] == "OBSERVED_PRESENT" and r["verifiable_signatures"] == 2


# --- structural guarantees ------------------------------------------------------

def test_gate_reports_detection_not_assumption(monkeypatch):
    _stub("OBSERVED_ABSENT", "OBSERVED_ABSENT", monkeypatch)
    r = ag.resume_eligible()
    assert r["detected_not_assumed"] is True
    assert r["observations"], "a verdict with no observations is an assumption"


def test_gate_names_the_stages_it_sits_between(monkeypatch):
    """It is a TRANSITION, not a stage. If it ever became stage 8 the protocol would have
    changed shape, which is precisely what PROTO-EXP-002 is testing for."""
    _stub("OBSERVED_ABSENT", "OBSERVED_ABSENT", monkeypatch)
    r = ag.resume_eligible()
    assert r["protocol_stage"] == 3 and r["next_stage"] == 4
    assert "eighth stage" in r["note"]


def test_no_time_based_or_declared_resume_path():
    """The gate must not offer a way to resume without observation.

    NOTE this test was first written as a substring scan and failed on the identifier
    `detected_not_assumed` — the very field asserting that nothing was assumed. Text
    matching cannot distinguish a banned BEHAVIOUR from a word describing its absence.
    Broadening the ban list or renaming the field to satisfy the scan would both have been
    wrong: the test was checking at the wrong level, so it now inspects the AST for actual
    calls. (Same class of error as the ANSI canonicalisation test — see test_hrf_runtime.)
    """
    import ast
    tree = ast.parse((ROOT / "scripts" / "authority_gate.py").read_text())
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            called.add(getattr(f, "id", None) or getattr(f, "attr", None))
    for banned in ("sleep", "input", "getpass"):
        assert banned not in called, (
            f"resume must be observation-driven; gate calls {banned}()")
