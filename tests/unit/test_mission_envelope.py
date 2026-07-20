"""Adversarial tests for the Mission Envelope.

These are not happy-path tests. Each one is an attempt to make a mixed-truth mission
render green — the failure mode the founder identified on 2026-07-20. If any of these
passes, the telemetry layer is decorative.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.mission_contract import Truth  # noqa: E402
from backend.helm_runtime.mission_envelope import (  # noqa: E402
    STATUS_DEGRADED, STATUS_FAILED, STATUS_PARTIAL, STATUS_PENDING_EVIDENCE,
    STATUS_RUNNING, STATUS_VERIFIED, EnvelopeError, MissionEnvelope,
)


def _env(**kw):
    return MissionEnvelope("M-TEST-1", "family_ops", agent="test", **kw)


# --- the core invariant ------------------------------------------------------

def test_agent_cannot_declare_status_at_construction():
    with pytest.raises(EnvelopeError):
        MissionEnvelope("M-TEST-1", "family_ops", agent="test", status=STATUS_VERIFIED)


def test_status_has_no_setter():
    e = _env()
    with pytest.raises(AttributeError):
        e.status = STATUS_VERIFIED  # type: ignore[misc]


def test_unknown_source_cannot_be_green_even_with_output():
    """The family-brief case: 5 calendars fine, 1 timed out, note still written."""
    e = _env()
    for c in ("michael", "caroline", "claire", "school", "home_ops"):
        e.source(c, Truth.OBSERVED, evidence=f"logs/{c}.json")
    e.unknown("alison_calendar", "query timed out", attempted=3)
    e.mutate("Apple Notes/Family Brief", "created", undo="backup/")
    e.prove("notes/family_brief.json")
    e.close()
    assert e.status == STATUS_PARTIAL
    assert not e.is_green


def test_error_forces_degraded_regardless_of_success():
    e = _env()
    e.source("a", Truth.OBSERVED, evidence="x.json")
    e.prove("out.md")
    e.error("connector", "unreachable")
    e.close()
    assert e.status == STATUS_DEGRADED


def test_asserted_source_cannot_reach_verified():
    """A web result read once, with no artifact, is not evidence."""
    e = _env()
    e.source("web", Truth.ASSERTED, detail="no cached artifact")
    e.prove("digest.md")
    e.close()
    assert e.status == STATUS_PARTIAL


def test_source_without_evidence_is_pending_not_verified():
    e = _env()
    e.source("cal", Truth.OBSERVED)  # observed, but nothing re-readable
    e.prove("out.md")
    e.close()
    assert e.status == STATUS_PENDING_EVIDENCE


def test_clean_run_with_full_evidence_is_verified():
    """Green must remain reachable, or the scale is useless."""
    e = _env()
    e.source("cal", Truth.OBSERVED, evidence="logs/cal.json")
    e.mutate("note", "created", undo="backup/")
    e.prove("out.md")
    e.close()
    assert e.status == STATUS_VERIFIED
    assert e.is_green


def test_unclosed_envelope_is_running_then_never_silently_complete():
    e = _env()
    e.source("cal", Truth.OBSERVED, evidence="x.json")
    assert e.status == STATUS_RUNNING  # crashed mid-mission != done


def test_hard_error_with_no_output_is_failed():
    e = _env()
    e.error("everything", "process died", severity="RED")
    e.close()
    assert e.status == STATUS_FAILED


def test_readonly_noop_mission_is_not_verified_without_evidence():
    """The cleaning-list case: 5 lists inspected, nothing changed."""
    e = _env()
    for i in range(5):
        e.source(f"list_{i}", Truth.OBSERVED)
        e.mutate(f"list_{i}", "none")
    e.close()
    assert e.status == STATUS_PENDING_EVIDENCE  # inspected, but unproven


# --- the renderer cannot be fooled either ------------------------------------

def test_renderer_rederives_and_ignores_tampered_status(tmp_path):
    """A forged status field in a stored envelope must not reach the board."""
    from scripts.founder_live import _rederive

    e = _env()
    e.unknown("alison", "timeout")
    e.prove("out.md")
    e.close()
    d = e.to_dict()
    d["status"] = STATUS_VERIFIED  # forge it
    assert _rederive(d) == STATUS_PARTIAL


def test_uncollected_domain_is_shown_not_omitted():
    """Silence must be loud: a domain with no collector renders NOT CONNECTED."""
    from scripts.founder_live import render

    board = render([], [])
    assert "NO_COLLECTOR" in board
    assert "family_ops" in board
    assert "NOT CONNECTED" in board


def test_board_shows_degraded_mission_without_green(tmp_path):
    from scripts.founder_live import render

    e = _env()
    e.unknown("alison", "timeout")
    e.prove("out.md")
    e.close()
    board = render([], [e.to_dict()])
    assert STATUS_PARTIAL in board
    assert "UNKNOWN  alison" in board


# --- schema / hygiene --------------------------------------------------------

def test_unknown_domain_rejected():
    with pytest.raises(EnvelopeError):
        MissionEnvelope("M-1", "not_a_domain", agent="test")


def test_unattributed_mission_rejected():
    with pytest.raises(EnvelopeError):
        MissionEnvelope("M-1", "family_ops", agent="")


def test_invalid_truth_class_rejected():
    e = _env()
    with pytest.raises(EnvelopeError):
        e.source("x", "PROBABLY_FINE")


def test_roundtrip_preserves_derived_status(tmp_path):
    e = _env()
    e.unknown("alison", "timeout")
    e.prove("out.md")
    e.close()
    p = e.write(tmp_path)
    loaded = json.loads(p.read_text())
    assert loaded["status"] == STATUS_PARTIAL
    assert loaded["status_derived"] is True
