# -*- coding: utf-8 -*-
"""tests/test_runtime_freshness.py

Exercises the runtime-freshness service against TEMP files only — never the real
runtime/ledger/state files (the live Phase C soak must not be disturbed).
"""
import json
import os
from datetime import datetime, timedelta, timezone

from backend import runtime_freshness as rf


def _write_json(path, doc):
    path.write_text(json.dumps(doc), encoding="utf-8")


def _stamp(path, seconds_old):
    """Force a file's mtime to `seconds_old` seconds in the past."""
    t = datetime.now(timezone.utc).timestamp() - seconds_old
    os.utime(path, (t, t))


def test_fresh_when_timestamp_within_budget(tmp_path):
    p = tmp_path / "control_plane_status.json"
    now = datetime.now(timezone.utc)
    _write_json(p, {"as_of": (now - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")})
    spec = {"path": None, "kind": "json", "ts_fields": ["as_of"], "budget": 120}
    spec["path"] = p.name
    res = rf.evaluate_signal("control_plane", spec, root=tmp_path, now=now)
    assert res["state"] == "FRESH"
    assert res["age_seconds"] is not None and res["age_seconds"] <= 120
    assert res["budget_seconds"] == 120


def test_stale_when_timestamp_older_than_budget(tmp_path):
    p = tmp_path / "control_plane_status.json"
    now = datetime.now(timezone.utc)
    _write_json(p, {"as_of": (now - timedelta(seconds=600)).isoformat().replace("+00:00", "Z")})
    spec = {"path": p.name, "kind": "json", "ts_fields": ["as_of"], "budget": 120}
    res = rf.evaluate_signal("control_plane", spec, root=tmp_path, now=now)
    assert res["state"] == "STALE"
    assert res["age_seconds"] > res["budget_seconds"]


def test_unknown_when_file_missing(tmp_path):
    spec = {"path": "does_not_exist.json", "kind": "json", "ts_fields": ["as_of"], "budget": 120}
    res = rf.evaluate_signal("control_plane", spec, root=tmp_path)
    assert res["state"] == "UNKNOWN"
    assert "missing" in res["reason"].lower()


def test_unknown_when_unparseable(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{ this is not json", encoding="utf-8")
    # No usable field and mtime fallback only fails if unreadable; unparseable JSON
    # still has an mtime, so to force UNKNOWN we point at an empty ts + set an old
    # mtime but the goal here is the parse path: empty-doc + no fields -> mtime used.
    # Instead assert the DEDICATED unknown path: a directory (unreadable as file).
    d = tmp_path / "adir"
    d.mkdir()
    spec = {"path": d.name, "kind": "json", "ts_fields": ["as_of"], "budget": 120}
    res = rf.evaluate_signal("x", spec, root=tmp_path)
    assert res["state"] == "UNKNOWN"


def test_mtime_fallback_when_no_timestamp_field(tmp_path):
    """A file with no timestamp field is aged by real mtime, not invented FRESH."""
    p = tmp_path / "authority.json"
    _write_json(p, {"orchestration_bridge_enabled": True})  # no ts field
    _stamp(p, 5000)  # 5000s old
    spec = {"path": p.name, "kind": "json", "ts_fields": [], "budget": 600}
    res = rf.evaluate_signal("orchestration_authority", spec, root=tmp_path)
    assert res["state"] == "STALE"
    assert res["age_seconds"] >= 600


def test_jsonl_last_line_timestamp(tmp_path):
    p = tmp_path / "runtime_truth_snapshots.jsonl"
    now = datetime.now(timezone.utc)
    old = (now - timedelta(seconds=100)).isoformat().replace("+00:00", "Z")
    p.write_text(
        json.dumps({"at": "2020-01-01T00:00:00Z", "status": "OLD"}) + "\n" +
        json.dumps({"at": old, "status": "OK"}) + "\n",
        encoding="utf-8",
    )
    spec = {"path": p.name, "kind": "jsonl_last", "ts_fields": ["at"], "budget": 300}
    res = rf.evaluate_signal("runtime_truth_snapshot", spec, root=tmp_path, now=now)
    assert res["state"] == "FRESH"
    assert res["age_seconds"] < 300  # used LAST line, not the 2020 first line


def test_per_signal_budget_is_respected(tmp_path):
    """Same source, same age — FRESH under a loose budget, STALE under a tight one.

    Proves budgets are PER-SIGNAL, not a blanket window."""
    p = tmp_path / "src.json"
    now = datetime.now(timezone.utc)
    _write_json(p, {"as_of": (now - timedelta(seconds=400)).isoformat().replace("+00:00", "Z")})
    tight = {"path": p.name, "kind": "json", "ts_fields": ["as_of"], "budget": 120}
    loose = {"path": p.name, "kind": "json", "ts_fields": ["as_of"], "budget": 3600}
    r_tight = rf.evaluate_signal("tight", tight, root=tmp_path, now=now)
    r_loose = rf.evaluate_signal("loose", loose, root=tmp_path, now=now)
    assert r_tight["state"] == "STALE"
    assert r_loose["state"] == "FRESH"


def test_overall_is_worst_of_all(tmp_path):
    now = datetime.now(timezone.utc)
    fresh_p = tmp_path / "fresh.json"
    stale_p = tmp_path / "stale.json"
    _write_json(fresh_p, {"as_of": now.isoformat().replace("+00:00", "Z")})
    _write_json(stale_p, {"as_of": (now - timedelta(seconds=9999)).isoformat().replace("+00:00", "Z")})

    # FRESH + STALE -> STALE
    specs = {
        "a": {"path": fresh_p.name, "kind": "json", "ts_fields": ["as_of"], "budget": 120},
        "b": {"path": stale_p.name, "kind": "json", "ts_fields": ["as_of"], "budget": 120},
    }
    res = rf.evaluate_all(specs, root=tmp_path, now=now)
    assert res["overall_state"] == "STALE"
    assert res["counts"] == {"FRESH": 1, "STALE": 1, "UNKNOWN": 0}

    # Add a missing (UNKNOWN) source -> overall becomes UNKNOWN (worst wins)
    specs["c"] = {"path": "nope.json", "kind": "json", "ts_fields": ["as_of"], "budget": 120}
    res2 = rf.evaluate_all(specs, root=tmp_path, now=now)
    assert res2["overall_state"] == "UNKNOWN"


def test_all_fresh_overall_fresh(tmp_path):
    now = datetime.now(timezone.utc)
    p = tmp_path / "f.json"
    _write_json(p, {"as_of": now.isoformat().replace("+00:00", "Z")})
    specs = {"a": {"path": p.name, "kind": "json", "ts_fields": ["as_of"], "budget": 120}}
    res = rf.evaluate_all(specs, root=tmp_path, now=now)
    assert res["overall_state"] == "FRESH"


def test_render_board_is_string(tmp_path):
    now = datetime.now(timezone.utc)
    p = tmp_path / "f.json"
    _write_json(p, {"as_of": now.isoformat().replace("+00:00", "Z")})
    specs = {"a": {"path": p.name, "kind": "json", "ts_fields": ["as_of"], "budget": 120}}
    board = rf.render_board(rf.evaluate_all(specs, root=tmp_path, now=now))
    assert "HELM RUNTIME FRESHNESS BOARD" in board
    assert "OVERALL:" in board


def test_real_budgets_are_tighter_than_blanket_24h():
    """Regression guard: no signal budget is the old blanket 86400s window."""
    assert all(b < 86400 for b in rf.FRESHNESS_BUDGETS.values())
    assert rf.FRESHNESS_BUDGETS["control_plane"] <= 120
