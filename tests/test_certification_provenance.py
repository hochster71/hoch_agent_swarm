"""Tests for certification reproducibility + resource-trend reporting.

The classifier decides leak-vs-plateau, which drives a real operational call
(abort a certification vs let it run). It is tested against synthetic series.
"""
from __future__ import annotations

import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

spec = importlib.util.spec_from_file_location(
    "certification_provenance", os.path.join(ROOT, "scripts", "soak", "certification_provenance.py")
)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)


def trend(values):
    return [{"sys_mem_pct_mean": v} for v in values]


# --- leak vs plateau: the distinction a snapshot cannot make -----------------

def test_monotonic_growth_is_classified_as_rising():
    r = cp.classify_memory(trend([81, 85, 89, 92, 94]))
    assert r["pattern"] == "RISING"
    assert r["floor_drift_pts"] > 0
    assert "accumulation" in r["note"]


def test_high_but_stable_is_a_plateau_not_a_leak():
    """94% flat is a different risk from 81->94 climbing."""
    r = cp.classify_memory(trend([93.0, 94.0, 93.5, 94.0, 93.8]))
    assert r["pattern"] == "PLATEAU"
    assert "not the thing growing" in r["note"]


def test_sawtooth_returning_to_baseline_is_not_a_leak():
    """Regression: an alternating series ending on a peak previously read as RISING.

    The floor is what matters — this one returns to 70 every cycle, so nothing is
    accumulating, however alarming the peaks look.
    """
    r = cp.classify_memory(trend([70, 95, 70, 95, 70, 95]))
    assert r["pattern"] == "OSCILLATING"
    assert r["floor_drift_pts"] == 0.0


def test_a_leak_is_caught_even_when_peaks_stay_flat():
    """Peaks pinned at the ceiling, floor climbing — the classic leak signature."""
    r = cp.classify_memory(trend([60, 95, 70, 95, 80, 95]))
    assert r["pattern"] == "RISING"
    assert r["floor_drift_pts"] >= 2.0


def test_insufficient_data_is_reported_not_guessed():
    r = cp.classify_memory(trend([94, 94]))
    assert r["pattern"] == "INSUFFICIENT_DATA"


# --- reproducibility grading uses the ratified vocabulary --------------------

def test_grade_values_come_from_the_ratified_truth_vocabulary():
    from backend.security.proof_contract import Truth
    valid = {t.value for t in Truth}
    for g in ("OBSERVED", "DERIVED", "ASSERTED", "UNKNOWN"):
        assert g in valid, "grades must not invent a parallel scale"


def test_head_changed_is_unknown_without_a_start_timestamp():
    r = cp.head_changed_since("")
    assert r["changed"] == cp.UNKNOWN_VALUE


def test_head_changed_detects_commits_after_a_past_timestamp():
    r = cp.head_changed_since("2000-01-01T00:00:00Z")
    assert r["changed"] is True
    assert r["commits_during_run"], "must list the commits it based the judgement on"


def test_metrics_loader_tolerates_a_partial_final_line(tmp_path):
    """A live soak may be mid-flush; a torn line must not crash the reporter."""
    d = tmp_path / "run"
    d.mkdir()
    (d / "soak_metrics.jsonl").write_text(
        '{"uptime_s": 1, "resources": {"system_mem_pct": 90}}\n{"uptime_s": 2, "reso'
    )
    rows = cp.load_metrics(os.path.relpath(str(d), ROOT))
    assert len(rows) == 1


def test_report_builds_against_the_live_run_without_mutating_it(tmp_path):
    before = os.path.getmtime(os.path.join(ROOT, "coordination", "soak", "soak_metrics.jsonl"))
    rep = cp.build("coordination/soak")
    after = os.path.getmtime(os.path.join(ROOT, "coordination", "soak", "soak_metrics.jsonl"))
    assert "certification" in rep and "reproducibility" in rep["certification"]
    assert before == after, "the reporter must be strictly read-only"
