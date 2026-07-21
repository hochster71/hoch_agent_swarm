"""Tests for scripts/helm_founder_status.py — rewritten 2026-07-20.

WHY REWRITTEN, NOT REPAIRED
---------------------------
The previous version imported `get_file_meta`, which broke collection for the ENTIRE
tests/unit suite. `git log -S"def get_file_meta"` returns nothing: it never existed in
this module. The file was written against a different (or imagined) API — `load_json`
also mismatched, expecting a `(data, err)` tuple where the real function returns the
parsed object and raises on failure.

`get_file_meta` was NOT restored, and must not be. Its signature was `(exists, mtime)`
— filesystem mtime surfaced into the founder status renderer. That is precisely the
mtime-as-produced-time defect class W1-002 removed repo-wide, where a `git checkout`
or `stash pop` silently refreshes the apparent age of stale data. The module is
currently mtime-free (`grep st_mtime` returns nothing) and should stay that way.
Restoring the function to satisfy a stale test would have reintroduced the defect to
make a test pass — the exact inversion this repo's doctrine forbids.

These tests exercise the API that actually exists.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.helm_founder_status import (  # noqa: E402
    classify, extract_status_from_mapping, load_json, normalize, progress_bar,
)


# --- load_json: real contract is "parse or raise", not a (data, err) tuple ----

def test_load_json_reads_a_real_file(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"state": "RUNNING", "percent_to_goal": 90.0}))
    assert load_json(p) == {"state": "RUNNING", "percent_to_goal": 90.0}


def test_load_json_raises_on_missing_file(tmp_path):
    """Fail loudly. A status renderer that silently swallows a missing oracle
    would render a verdict from absent evidence."""
    with pytest.raises(OSError):
        load_json(tmp_path / "does_not_exist.json")


def test_load_json_raises_on_malformed_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    with pytest.raises(json.JSONDecodeError):
        load_json(p)


# --- normalize: None must become UNKNOWN, never a default -------------------

def test_normalize_none_is_unknown_not_fail():
    """UNKNOWN and FAIL are different verdicts. Collapsing them is the defect
    the epistemic-states rule exists to prevent."""
    assert normalize(None) == "UNKNOWN"


def test_normalize_booleans_map_to_pass_fail():
    assert normalize(True) == "PASS"
    assert normalize(False) == "FAIL"


@pytest.mark.parametrize("raw,want", [
    ("in progress", "IN_PROGRESS"), ("blocked-external", "BLOCKED_EXTERNAL"),
    ("  done  ", "DONE"), ("REMOTE_DELIVERED", "REMOTE_DELIVERED"),
])
def test_normalize_canonicalises_case_space_and_hyphen(raw, want):
    assert normalize(raw) == want


# --- extract_status_from_mapping --------------------------------------------

def test_extract_returns_unknown_when_no_status_key():
    """No status key present is UNKNOWN — not GREEN, not FAIL."""
    assert extract_status_from_mapping({"unrelated": 1, "other": "x"}) == "UNKNOWN"


def test_extract_reads_boolean_completion_flags():
    assert extract_status_from_mapping({"validated": True}) == "PASS"
    assert extract_status_from_mapping({"resolved": False}) == "FAIL"


# --- classify: anything not explicitly green is BLOCKED ---------------------

def test_classify_unknown_is_blocked_not_green():
    """Fail closed. An unrecognised status must never render GREEN."""
    assert classify("UNKNOWN", {"DONE", "PASS"}) == "BLOCKED"
    assert classify("", {"DONE", "PASS"}) == "BLOCKED"
    assert classify("SOMETHING_NEW", {"DONE", "PASS"}) == "BLOCKED"


def test_classify_green_only_on_declared_green_states():
    assert classify("done", {"DONE", "PASS"}) == "GREEN"
    assert classify("PASS", {"DONE", "PASS"}) == "GREEN"


# --- progress_bar: clamps rather than overflowing ---------------------------

@pytest.mark.parametrize("pct,filled", [(0, 0), (50, 25), (100, 50), (-10, 0), (250, 50)])
def test_progress_bar_clamps_and_sizes(pct, filled):
    bar = progress_bar(pct, width=50)
    assert len(bar) == 50
    assert bar.count("█") == filled


# --- the module must stay mtime-free (W1-002) -------------------------------

def test_module_does_not_reintroduce_filesystem_mtime():
    """Guards the reason get_file_meta was not restored.

    If a future change surfaces st_mtime here, a stale oracle refreshed by a git
    checkout would render as current in the founder's status view.
    """
    src = (ROOT / "scripts" / "helm_founder_status.py").read_text(encoding="utf-8")
    offenders = [ln.strip() for ln in src.splitlines()
                 if "st_mtime" in ln and "mtime-metadata-ok" not in ln]
    assert not offenders, (
        "filesystem mtime reintroduced into the founder status renderer:\n  "
        + "\n  ".join(offenders)
        + "\nUse a producer timestamp, or tag the line `# mtime-metadata-ok` if it is "
          "genuinely file metadata and never presented as data age."
    )
