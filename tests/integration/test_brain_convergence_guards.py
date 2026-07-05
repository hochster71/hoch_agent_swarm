from backend.brain_convergence.scorer import score_prompt, compare
from backend.brain_convergence.splits import make_splits, assert_disjoint
from backend.brain_convergence.judge_audit import audit_scorer, KNOWN_BAD, KNOWN_GOOD

import pytest


# --- scorer ---------------------------------------------------------------

def test_scorer_is_deterministic():
    assert score_prompt(KNOWN_GOOD) == score_prompt(KNOWN_GOOD)


def test_scorer_ranks_good_above_bad():
    assert score_prompt(KNOWN_GOOD)["overall"] > score_prompt(KNOWN_BAD)["overall"]


def test_scorer_labels_mechanical_proxy():
    r = score_prompt(KNOWN_GOOD)
    assert r["method"] == "MECHANICAL_PROXY" and r["rung"] == 1
    assert len(r["dimensions"]) == 10


def test_compare_head_to_head():
    c = compare(KNOWN_GOOD, KNOWN_BAD)
    assert c["candidate_wins"] is True and c["delta"] > 0


# --- splits (held-out discipline) ----------------------------------------

def _pool():
    return {"Cyber": [f"c{i}" for i in range(20)], "AI": [f"a{i}" for i in range(10)]}


def test_splits_are_disjoint():
    s = make_splits(_pool())
    rep = assert_disjoint(s)          # raises on leakage
    assert rep["disjoint"] is True


def test_splits_are_deterministic():
    assert make_splits(_pool())["provenance_hash"] == make_splits(_pool())["provenance_hash"]


def test_splits_cover_every_gene():
    p = _pool()
    s = make_splits(p)
    total = sum(len(v) for v in p.values())
    assert len(s["train"]) + len(s["dev"]) + len(s["heldout"]) == total


def test_leakage_is_detected():
    s = make_splits(_pool())
    s["dev"].append(s["train"][0])    # inject leakage
    with pytest.raises(AssertionError):
        assert_disjoint(s)


# --- judge audit (seeded fault) ------------------------------------------

def test_scorer_audit_passes_on_healthy_scorer():
    a = audit_scorer()
    assert a["passed"] is True
    assert a["known_bad_score"] < a["floor"]
    assert a["known_good_score"] > a["ceiling"]
    assert a["separation"] > 0


def test_audit_fails_if_floor_impossibly_high():
    # If we demand a bad prompt score below 0, the audit must FAIL (guard works).
    a = audit_scorer(floor=-1.0)
    assert a["passed"] is False
    assert "FREEZE PROMOTIONS" in a["verdict"]
