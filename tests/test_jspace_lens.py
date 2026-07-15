"""Semantic Jacobian Lens — the test comes BEFORE the implementation.

WHAT IT IS (grounded, honest): J-Space's Executive Intelligence measures how SENSITIVE the promotion
decision is to each piece of evidence. The "Jacobian" here is the discrete gradient ∂(decision)/∂(finding):
if a finding flipped from bad to good, how much would the consensus decision move?

  * DRIVERS   — the findings whose flip most changes the decision. Turns 1,800 open findings into the
                handful actually holding the gate closed.
  * FRAGILITY — how close the decision sits to flipping. A verdict that one perturbation would overturn
                is FRAGILE and must not auto-promote. That is 'No Fake Green' as calculus.

Pure and read-only: operates on assessment records, never mutates state, never calls a model.
"""
from __future__ import annotations

from backend.jspace.lens import SemanticJacobianLens, consensus_of, p_withhold   # do not exist yet


def A(observer, subject, assessment):
    return {"observer": observer, "subject": subject, "assessment": assessment}


# ---------------------------------------------------------------- decision primitives
def test_consensus_is_worst_wins():
    """One CONTRADICTED finding contradicts the whole system (fail-closed). Any BLOCKED blocks."""
    assert consensus_of([A("o", "s1", "CONFIRMED_LIVE")]) == "CONFIRMED_LIVE"
    assert consensus_of([A("o", "s1", "CONFIRMED_LIVE"), A("o", "s2", "BLOCKED")]) == "BLOCKED"
    assert consensus_of([A("o", "s1", "BLOCKED"), A("o", "s2", "CONTRADICTED")]) == "CONTRADICTED"


def test_p_withhold_monotonic():
    """P(withhold promotion): 0 when all live, higher when blocked, highest when contradicted."""
    assert p_withhold("CONFIRMED_LIVE") == 0.0
    assert 0.0 < p_withhold("BLOCKED") < p_withhold("CONTRADICTED")
    assert p_withhold("CONTRADICTED") == 1.0


# ---------------------------------------------------------------- drivers
def test_the_single_contradiction_is_the_top_driver():
    """A system that is CONTRADICTED only because of ONE finding must name that finding as the driver —
    flipping it is what would move the gate."""
    rows = [A("truth", "scheduler_instance_consistency", "CONTRADICTED"),
            A("truth", "runtime_pointer", "CONFIRMED_LIVE"),
            A("evidence", "canonical_lease_ledger", "CONFIRMED_LIVE")]
    out = SemanticJacobianLens(rows).compute()
    assert out["consensus"] == "CONTRADICTED"
    assert out["drivers"][0]["subject"] == "scheduler_instance_consistency"
    assert out["drivers"][0]["sensitivity"] > 0     # flipping it lowers P(withhold)


def test_a_finding_that_does_not_move_the_decision_has_zero_sensitivity():
    """With TWO independent contradictions, flipping just one leaves consensus CONTRADICTED (worst-wins),
    so a lone flip does NOT move the top-level decision — its marginal sensitivity is 0. Honesty: the
    lens must not overstate the impact of a finding that changes nothing on its own."""
    rows = [A("truth", "sched", "CONTRADICTED"), A("security", "posture", "CONTRADICTED"),
            A("flow", "leases", "CONFIRMED_LIVE")]
    out = SemanticJacobianLens(rows).compute()
    # neither single flip changes the CONTRADICTED consensus -> both have 0 marginal sensitivity
    assert all(d["sensitivity"] == 0 for d in out["drivers"] if d["subject"] in ("sched", "posture"))
    # but a healthy finding is never a driver
    assert all(d["subject"] != "leases" for d in out["drivers"])


# ---------------------------------------------------------------- fragility
def test_a_knife_edge_decision_is_fragile():
    """One BLOCKED finding, everything else live: the decision (withhold) flips to promote if that ONE
    finding clears. That is fragile — high sensitivity to a single perturbation."""
    rows = [A("security", "control_posture", "BLOCKED"),
            A("flow", "lease_balance", "CONFIRMED_LIVE"),
            A("perf", "live_concurrency", "CONFIRMED_LIVE")]
    out = SemanticJacobianLens(rows).compute()
    assert out["fragility"] > 0.5, "a decision one flip from changing must read as fragile"
    assert out["promotable"] is False


def test_an_all_clear_system_is_robust_and_promotable():
    rows = [A("a", "s1", "CONFIRMED_LIVE"), A("b", "s2", "CONFIRMED_LIVE")]
    out = SemanticJacobianLens(rows).compute()
    assert out["consensus"] == "CONFIRMED_LIVE"
    assert out["fragility"] < 0.35
    assert out["promotable"] is True
    assert out["drivers"] == []


# ---------------------------------------------------------------- fail-closed
def test_no_assessments_is_unknown_never_promotable():
    out = SemanticJacobianLens([]).compute()
    assert out["consensus"] == "UNKNOWN"
    assert out["promotable"] is False
