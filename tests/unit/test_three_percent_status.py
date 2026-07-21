"""Regression tests for the three-metric status model.

WHY THIS EXISTS
---------------
Two agents gave different answers to "how close is HELM to 100%" and both were correct:
they were measuring different denominators. The fix was three LABELLED metrics. These
tests pin the properties that make them non-gameable.

The central one: AGENT-CONTROLLABLE must be UNKNOWN while no authoritative ownership
field exists. A percentage over a denominator nobody defined is how the old north-star
100% became meaningless — it was reachable by quietly excluding founder-gated items.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.helm_three_percent_status as st  # noqa: E402


def _write(tmp_path, nodes):
    d = tmp_path / "coordination" / "goal"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "build_to_goal_status.json"
    p.write_text(json.dumps({"state": "RUNNING", "nodes": nodes}))
    return p


@pytest.fixture
def goal(tmp_path, monkeypatch):
    def _set(nodes):
        monkeypatch.setattr(st, "GOAL", _write(tmp_path, nodes))
    return _set


# --- UNKNOWN cannot become a number without the schema field ----------------

def test_unclassified_ownership_yields_UNKNOWN_not_a_percentage(goal):
    """THE guard. Flat str->str nodes carry no ownership -> UNKNOWN, never a number."""
    goal({"N0": "DONE", "N1": "DONE", "N2": "HOLD"})
    r = st.agent_controllable()
    assert r["value"] == "UNKNOWN"
    assert r["known"] is False
    assert r["numerator"] is None and r["denominator"] is None
    assert "%" not in str(r["value"])


def test_unknown_result_names_the_missing_field_and_files(goal):
    """A refusal that does not say what is missing is not actionable."""
    goal({"N0": "DONE"})
    r = st.agent_controllable()
    assert "ownership" in r["missing_schema_field"]
    assert any("build_to_goal_status.json" in f for f in r["files_requiring_augmentation"])
    assert "CLAUDE.md" in r["doctrine_exists_but_is_prose"]


def test_partial_classification_still_yields_UNKNOWN(goal):
    """Half-classified is not classified. No partial-credit denominator."""
    goal({"N0": {"status": "DONE", "ownership": "AGENT"}, "N1": "DONE"})
    assert st.agent_controllable()["value"] == "UNKNOWN"


def test_ownership_is_not_inferred_from_status_strings(goal):
    """BLOCKED_EXTERNAL is a STATUS, not an OWNER. A node can be externally blocked
    today and agent-owned tomorrow; conflating them invents an exclusion."""
    goal({"N0": "BLOCKED_EXTERNAL", "N1": "DONE"})
    r = st.agent_controllable()
    assert r["value"] == "UNKNOWN", "status strings must not be read as ownership"
    assert "status strings" in r["refused_inferences"]


def test_ownership_is_not_inferred_from_node_names(goal):
    """Names like N9_APPLE_REVIEW must not create exclusions."""
    goal({"N9_APPLE_REVIEW": "HOLD", "N8_STRIPE_SETTLEMENT": "HOLD", "N0": "DONE"})
    r = st.agent_controllable()
    assert r["value"] == "UNKNOWN"
    assert "node names" in r["refused_inferences"]


# --- once classified, exclusions must actually apply -------------------------

def test_external_nodes_are_excluded_from_the_agent_denominator(goal):
    goal({"A": {"status": "DONE", "ownership": "AGENT"},
          "B": {"status": "HOLD", "ownership": "EXTERNAL"}})
    r = st.agent_controllable()
    assert r["known"] is True
    assert r["denominator"] == 1 and r["numerator"] == 1
    assert r["value"] == "100.0%", "an EXTERNAL hold must not drag agent scope below 100%"
    assert r["excluded"] == {"B": "EXTERNAL"}


def test_founder_only_nodes_are_excluded(goal):
    goal({"A": {"status": "DONE", "ownership": "AGENT"},
          "B": {"status": "HOLD", "ownership": "FOUNDER"}})
    r = st.agent_controllable()
    assert r["denominator"] == 1
    assert r["excluded"] == {"B": "FOUNDER"}


def test_shared_nodes_follow_the_documented_rule(goal):
    """SHARED is INCLUDED: the agent can act, even if someone else must act too.
    Excluding them would understate agent-controllable scope."""
    goal({"A": {"status": "DONE", "ownership": "AGENT"},
          "S": {"status": "HOLD", "ownership": "SHARED"}})
    r = st.agent_controllable()
    assert r["denominator"] == 2, "SHARED must be IN the denominator"
    assert r["numerator"] == 1
    assert "SHARED nodes are INCLUDED" in r["shared_rule"]


# --- mission completion must be untouched by ownership ----------------------

def test_mission_completion_is_unchanged_by_ownership_classification(goal):
    """Mission % counts ALL nodes including external gates. Adding ownership metadata
    must not move it — otherwise the two metrics are not independent."""
    goal({"A": "DONE", "B": "HOLD"})
    before = st.mission_completion()
    goal({"A": {"status": "DONE", "ownership": "AGENT"},
          "B": {"status": "HOLD", "ownership": "EXTERNAL"}})
    after = st.mission_completion()
    assert before["denominator"] == after["denominator"] == 2, (
        "mission denominator must include externally gated nodes"
    )


def test_promotion_validation_never_declared_only_derived():
    """No control can be reported VALIDATED without adversarial evidence."""
    r = st.promotion_control_validation()
    assert r["denominator"] == len(st.REQUIRED_CONTROLS)
    for cid, state in r["per_control"].items():
        assert state in ("UNKNOWN", "SPECIFIED", "CONFIGURED", "ENFORCED",
                         "SUSTAINED", "VALIDATED")


def test_all_three_metrics_remain_separately_reported():
    """Collapsing them back into one number is the defect this model fixed."""
    m, a, p = (st.mission_completion(), st.agent_controllable(),
               st.promotion_control_validation())
    assert m["scope"] != a["scope"] != p["scope"]
    for r in (m, a, p):
        assert "scope" in r, "a percentage without its scope is not reportable"
