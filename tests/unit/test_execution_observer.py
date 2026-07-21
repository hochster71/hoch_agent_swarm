"""CYB-002 — the observer must not overstate what a window proves.

The danger is not a wrong reading. It is a correct reading described too strongly:
"not loaded during one run" quietly becoming "unreachable".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.execution_observer import (  # noqa: E402
    WATCHED, accumulate, observe, write_evidence,
)


def test_observes_a_watched_import_when_it_actually_happens():
    """Positive control. If the observer cannot see a load, its silence means nothing."""
    _, obs = observe(lambda: __import__("json"), label="t")
    assert obs.outcome == "COMPLETED"


def test_records_watched_package_as_NOT_loaded_when_it_is_not():
    _, obs = observe(lambda: 1 + 1, label="t")
    assert set(obs.watched_not_loaded) == set(WATCHED)
    assert obs.watched_loaded == {}


def test_a_raising_callable_still_produces_an_observation():
    """Fail OPEN for the observation. An unobserved failure leaves no trace, and a run
    with no trace is unattributable work."""
    def boom():
        raise RuntimeError("x")
    _, obs = observe(boom, label="t")
    assert obs.outcome == "RAISED" and "RuntimeError" in obs.error
    assert obs.finished_at


def test_evidence_says_IN_THIS_RUN_and_refuses_the_word_unreachable():
    """THE guard. One window is one observation."""
    _, obs = observe(lambda: None, label="t")
    ev = obs.to_evidence()
    assert "watched_NOT_LOADED_in_this_run" in ev
    assert ev["observation_windows"] == 1
    assert "NOT 'unreachable'" in ev["claim_this_supports"]
    assert "unreachable" not in json.dumps(ev.get("watched_NOT_LOADED_in_this_run"))


def test_evidence_is_hashed_and_self_describing():
    _, obs = observe(lambda: None, label="t")
    ev = obs.to_evidence()
    assert len(ev["content_hash"]) == 64
    assert ev["evidence_class"] == "OBSERVED_EXECUTION"
    assert ev["schema_version"]


def test_observer_installs_no_import_hooks():
    """An observer that alters execution produces evidence about itself."""
    before = list(sys.meta_path)
    observe(lambda: __import__("base64"), label="t")
    assert list(sys.meta_path) == before


def test_accumulation_with_zero_windows_supports_NO_claim(tmp_path):
    a = accumulate(tmp_path)
    assert a["observation_windows"] == 0
    assert "NO WINDOWS RECORDED" in a["claim_supported"]


def test_accumulation_counts_windows_and_never_says_impossible(tmp_path):
    for i in range(3):
        _, obs = observe(lambda: None, label=f"w{i}")
        write_evidence(obs, tmp_path / f"obs_w{i}.json")
    a = accumulate(tmp_path)
    assert a["observation_windows"] == 3
    assert "not observed across 3" in a["claim_supported"]
    assert a["claim_NOT_supported"] == "impossible / unreachable / cannot occur"
    assert a["per_package"]["mcp"]["not_observed_in"] == 3
    assert a["per_package"]["mcp"]["loaded_in"] == 0


def test_accumulation_states_that_count_is_not_diversity(tmp_path):
    """3 windows over the same code path is not 3x the coverage. The artifact must say so
    rather than let a reader infer breadth from a number."""
    a = accumulate(tmp_path)
    assert "DIVERSITY" in a["coverage_caveat"]
