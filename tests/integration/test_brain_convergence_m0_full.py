import json
import tempfile
from pathlib import Path

from backend.brain_convergence.champion import load_registry, promote, mean_champion_score
from backend.brain_convergence.convergence import update as conv_update


def test_promote_only_on_strictly_better():
    reg = {"generation": 0, "champions": {}}
    r1 = promote(reg, {"Cyber": {"gene_id": "g1", "title": "A", "score": 60.0}}, "hashA")
    assert r1["promoted"] == ["Cyber"]
    # equal score -> held (no churn)
    r2 = promote(r1["registry"], {"Cyber": {"gene_id": "g2", "title": "B", "score": 60.0}}, "hashB")
    assert r2["held"] == ["Cyber"] and r2["registry"]["champions"]["Cyber"]["gene_id"] == "g1"
    # better score -> promoted
    r3 = promote(r2["registry"], {"Cyber": {"gene_id": "g3", "title": "C", "score": 70.0}}, "hashC")
    assert r3["promoted"] == ["Cyber"] and r3["registry"]["champions"]["Cyber"]["gene_id"] == "g3"


def test_champion_is_verified_on_heldout():
    reg = {"generation": 0, "champions": {}}
    r = promote(reg, {"AI": {"gene_id": "g", "title": "T", "score": 80.0}}, "h")
    assert r["registry"]["champions"]["AI"]["state"] == "VERIFIED_ON_HELDOUT"


def test_mean_champion_score():
    reg = {"generation": 1, "champions": {"a": {"score": 60.0}, "b": {"score": 80.0}}}
    assert mean_champion_score(reg) == 70.0


def test_convergence_detects_plateau():
    f = tempfile.mktemp(suffix=".json")
    conv_update(f, 1, 70.0)         # gen 1: no gain (baseline)
    conv_update(f, 2, 70.1)         # gain 0.1
    conv_update(f, 3, 70.2)         # gain 0.1
    s = conv_update(f, 4, 70.25)    # gain 0.05 -> 3 consecutive gains < epsilon
    assert s["converged"] is True and s["state"] == "CONVERGED"


def test_convergence_improving_not_converged():
    f = tempfile.mktemp(suffix=".json")
    conv_update(f, 1, 50.0)
    s = conv_update(f, 2, 60.0)  # gain 10 > epsilon
    assert s["converged"] is False and s["state"] == "IMPROVING"
