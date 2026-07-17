"""Tests for the HELM Mission Assurance Index (HMAI).

These read the REAL repo evidence via compute_hmai() — no fixtures substituted for
file reads. The core anti-fake-green invariant under test: an UNKNOWN pillar is
NEVER counted as green and NEVER scored as a pass.
"""
from __future__ import annotations

from backend.truth.hmai import compute_hmai, PILLAR_PRODUCERS, UNKNOWN, VERIFIED


def test_compute_hmai_runs_and_has_shape():
    r = compute_hmai()
    assert isinstance(r, dict)
    for k in ("index", "band", "coverage_pct", "can_mission_safely_proceed",
              "top_reasons", "pillars", "pillar_state_counts", "doctrine"):
        assert k in r, f"missing key {k}"


def test_returns_all_pillars():
    r = compute_hmai()
    pillars = r["pillars"]
    assert len(pillars) == len(PILLAR_PRODUCERS)
    keys = {p["key"] for p in pillars}
    for expected in ("mission_execution", "evidence_freshness", "founder_approvals",
                     "runtime_truth", "cyber_security", "ai_governance",
                     "supply_chain_zt"):
        assert expected in keys, f"pillar {expected} absent"
    # every pillar carries its own state + freshness fields
    for p in pillars:
        assert "state" in p and "score" in p and "weight" in p
        assert "age_seconds" in p and "source" in p


def test_unknown_pillars_are_not_green_and_not_scored():
    """The load-bearing NO-FAKE-GREEN invariant."""
    r = compute_hmai()
    unknown = [p for p in r["pillars"] if p["state"] == UNKNOWN]
    for p in unknown:
        assert p["counts_as_green"] is False, f"{p['key']} UNKNOWN but counts_as_green"
        assert p["score"] is None, f"{p['key']} UNKNOWN but carries a numeric score"
        assert p["scored"] is False, f"{p['key']} UNKNOWN but marked scored"


def test_ai_governance_is_honestly_unknown():
    """No live AI-governance producer exists -> it must be UNKNOWN, not invented green."""
    r = compute_hmai()
    ai = next(p for p in r["pillars"] if p["key"] == "ai_governance")
    assert ai["state"] == UNKNOWN
    assert ai["counts_as_green"] is False
    assert ai["key"] in r["unknown_pillars"]


def test_index_is_bounded_and_downweighted_by_unknowns():
    r = compute_hmai()
    idx = r["index"]
    assert idx is None or (0.0 <= idx <= 100.0)
    # coverage < 100 whenever any pillar is UNKNOWN; index computed over FULL weight
    if r["pillar_state_counts"]["UNKNOWN"] > 0:
        assert r["coverage_pct"] < 100.0
    # a green pillar must be VERIFIED-stated (no DEGRADED/STALE rendered green)
    for p in r["pillars"]:
        if p["counts_as_green"]:
            assert p["state"] == VERIFIED


def test_top_reasons_and_proceed_present():
    r = compute_hmai()
    assert isinstance(r["top_reasons"], list) and len(r["top_reasons"]) <= 3
    assert isinstance(r["can_mission_safely_proceed"], bool)
    # blockers list must exist and be consistent with the boolean
    assert isinstance(r["proceed_blockers"], list)
    if r["can_mission_safely_proceed"]:
        assert r["proceed_blockers"] == []
    else:
        assert len(r["proceed_blockers"]) > 0
