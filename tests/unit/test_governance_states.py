"""Tests for executable governance doctrine.

Every test here corresponds to a real error made during the PROC-001 review. The suite
exists so those errors fail loudly in code rather than being caught by a careful reader.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.governance_states import (  # noqa: E402
    Control, Epistemic, Evidence, Lifecycle, LifecycleOverclaim, now, resolve,
)


def _c() -> Control:
    return Control("TEST-001", "a control under test")


# --- the rc23 case: designed, never applied ----------------------------------

def test_design_artifact_buys_specified_only():
    c = _c().add(Evidence("design_artifact", "rc23 runbook", now()))
    assert c.state is Lifecycle.SPECIFIED
    assert c.why_not(Lifecycle.CONFIGURED)


def test_configured_is_not_enforced():
    """A setting applied is not a system that refuses violations."""
    c = _c().add(Evidence("config_read", "commit.gpgsign=true", now()))
    assert c.state is Lifecycle.CONFIGURED
    with pytest.raises(LifecycleOverclaim):
        c.assert_at_most(Lifecycle.ENFORCED)


# --- the sustainment error: snapshot cannot buy an interval state ------------

def test_snapshot_cannot_establish_sustained():
    """THE audit error. Enabled at inspection time != continuously enforced."""
    c = _c().add(Evidence("transition_log", "control was on when I looked", now()))
    assert c.state is Lifecycle.UNKNOWN, (
        "point-in-time evidence must not discharge SUSTAINED; that is the same category "
        "error as a collector reporting HEALTHY from a stale heartbeat"
    )


def test_interval_evidence_does_establish_sustained():
    c = _c().add(Evidence("transition_log", "continuous since last audit", now(),
                          interval_start="2026-06-01T00:00:00Z",
                          interval_end="2026-07-20T00:00:00Z"))
    assert c.state is Lifecycle.SUSTAINED


# --- GOV-007: configuration is not validation --------------------------------

def test_configuration_never_reaches_validated():
    c = (_c().add(Evidence("config_read", "signing configured", now()))
             .add(Evidence("refusal_observed", "unsigned push refused", now())))
    assert c.state is Lifecycle.ENFORCED
    with pytest.raises(LifecycleOverclaim) as ei:
        c.assert_at_most(Lifecycle.VALIDATED)
    assert "adversarial" in str(ei.value) and "boundary" in str(ei.value)


def test_adversarial_attempt_that_SUCCEEDED_does_not_validate():
    """If impersonation worked, the control is disproven, not validated."""
    c = _c().add(Evidence("adversarial_test", "impersonation attempt", now(),
                          interval_start=now(), interval_end=now(),
                          adversarial=True, attempt_succeeded=True))
    assert c.state is not Lifecycle.VALIDATED


def test_adversarial_attempt_that_FAILED_at_the_boundary_validates():
    c = _c().add(Evidence("adversarial_test", "impersonation refused by protected ref", now(),
                          interval_start=now(), interval_end=now(),
                          adversarial=True, boundary_exercised=True,
                          attempt_succeeded=False,
                          rejection_reason="GH006: protected branch update failed"))
    assert c.state is Lifecycle.VALIDATED


def test_environmental_failure_does_NOT_validate():
    """THE false-green path in the validation machinery itself.

    An attempt blocked by no-network also reports attempt_succeeded=False. Without
    boundary_exercised, that environmental fault would render as a demonstrated control —
    the same defect as a collector reporting HEALTHY because it could not reach the
    producer, committed by the code that exists to catch it.
    """
    c = _c().add(Evidence("adversarial_test", "push attempt: DNS failure", now(),
                          interval_start=now(), interval_end=now(),
                          adversarial=True, boundary_exercised=False,
                          attempt_succeeded=False,
                          rejection_reason="could not resolve github.com"))
    assert c.state is not Lifecycle.VALIDATED, (
        "an attempt that never reached the enforcement boundary is INCONCLUSIVE"
    )


def test_boundary_unknown_does_not_validate():
    """boundary_exercised=None means nobody recorded it. UNKNOWN, not satisfied."""
    c = _c().add(Evidence("adversarial_test", "attempt, boundary contact unrecorded", now(),
                          interval_start=now(), interval_end=now(),
                          adversarial=True, attempt_succeeded=False))
    assert c.state is not Lifecycle.VALIDATED


# --- the NONE OBSERVED slip --------------------------------------------------

def test_no_observations_is_unobserved_not_absent():
    """'We did not look' must never render as 'we looked and found nothing'."""
    assert resolve([]) is Epistemic.UNOBSERVED


def test_unobserved_dominates():
    assert resolve([Epistemic.OBSERVED_PRESENT, Epistemic.UNOBSERVED]) is Epistemic.UNOBSERVED
    assert resolve([Epistemic.OBSERVED_ABSENT, Epistemic.UNOBSERVED]) is Epistemic.UNOBSERVED


def test_unobserved_evidence_discharges_nothing():
    c = _c().add(Evidence("config_read", "could not read config", now(),
                          epistemic=Epistemic.UNOBSERVED))
    assert c.state is Lifecycle.UNKNOWN


# --- no setter: state cannot be declared -------------------------------------

def test_state_has_no_setter():
    c = _c()
    with pytest.raises(AttributeError):
        c.state = Lifecycle.VALIDATED  # type: ignore[misc]


def test_highest_supported_state_wins_not_latest():
    c = (_c().add(Evidence("refusal_observed", "refused", now()))
             .add(Evidence("design_artifact", "doc", now())))
    assert c.state is Lifecycle.ENFORCED, "a later weaker claim must not lower the verdict"


def test_why_not_names_the_missing_obligation():
    c = _c().add(Evidence("design_artifact", "doc", now()))
    msg = c.why_not(Lifecycle.SUSTAINED)
    assert "transition_log" in msg and "interval" in msg, (
        "a gate that cannot say why it refused is not a gate"
    )
