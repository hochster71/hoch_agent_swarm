"""W1-002a — collector provenance. FAILING BY DESIGN until mtime substitution is removed.

Doctrine: unknown propagates until evidence collapses it.
Rule:     no filesystem timestamp may be represented as evidence production time.

Original defect (HeartbeatFileCollector.collect and ModelBindingCollector.collect —
line numbers deliberately omitted, they go stale on the first edit): when a payload
carried no
timestamp key, the collector falls back to `p.stat().st_mtime`. A `git checkout`,
`pull`, `stash pop`, rsync, or backup restore rewrites mtime without changing content,
so week-old data renders OBSERVED/LIVE. All three of those git operations were run in
this repository on 2026-07-20.

These tests define the required behaviour. They fail now. Do not skip them.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.collectors import (  # noqa: E402
    HeartbeatFileCollector, ModelBindingCollector, Truth,
)

WEEK = 7 * 86400


def _write(p: Path, payload: dict, mtime_now: bool = True) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload), encoding="utf-8")
    if mtime_now:
        os.utime(p, None)  # touch: mtime = now, content unchanged


def _collect(tmp_path: Path, payload: dict, ts_key: str = "timestamp"):
    """Collect against a file whose mtime is NOW but whose content may be old."""
    rel = "coordination/_w1002a_probe.json"
    p = ROOT / rel
    _write(p, payload)
    try:
        c = HeartbeatFileCollector("probe", rel, "engineering", sla_seconds=300,
                                   ts_key=ts_key)
        return c.collect()[0]
    finally:
        p.unlink(missing_ok=True)


# --- required fixture 1: missing produced_at + fresh mtime = UNKNOWN ----------

def test_missing_timestamp_with_fresh_mtime_is_unknown(tmp_path):
    r = _collect(tmp_path, {"status": "HEALTHY", "detail": "no timestamp field"})
    assert r.truth == Truth.UNKNOWN, (
        "heartbeat carries no producer timestamp; file mtime is not evidence of data "
        f"age. Got {r.truth.value} (observed_at={r.observed_at})."
    )
    assert r.age_seconds is None, "age must be null when produced_at is absent"
    assert "mtime" in (r.error or "").lower() or "timestamp" in (r.error or "").lower(), (
        "reason must explicitly state why the reading is UNKNOWN"
    )


# --- required fixture 2: old produced_at + fresh mtime = STALE ----------------

def test_old_payload_timestamp_with_fresh_mtime_is_stale(tmp_path):
    """THE fixture. Content a week old, file touched a second ago."""
    old = (datetime.now(timezone.utc) - timedelta(seconds=WEEK)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = _collect(tmp_path, {"timestamp": old, "status": "HEALTHY"})
    assert r.truth == Truth.CACHED, (
        f"age must derive from produced_at, not mtime. Got {r.truth.value}."
    )
    assert r.age_seconds is not None and r.age_seconds > WEEK - 120, (
        f"age {r.age_seconds} does not reflect the week-old payload timestamp"
    )


# --- required fixture 3: malformed produced_at + fresh mtime = UNKNOWN --------

@pytest.mark.parametrize("bad", ["not-a-date", "", 0, [], {"nested": 1}, "2026-13-45T99:99:99Z"])
def test_malformed_timestamp_is_unknown_not_now(tmp_path, bad):
    r = _collect(tmp_path, {"timestamp": bad, "status": "HEALTHY"})
    assert r.truth == Truth.UNKNOWN, (
        f"malformed timestamp {bad!r} must yield UNKNOWN, never fall back to mtime "
        f"or wall clock. Got {r.truth.value}."
    )
    assert r.age_seconds is None


# --- git-operation forgery ----------------------------------------------------

def test_touching_a_stale_file_cannot_make_it_fresh(tmp_path):
    """Simulates `git checkout` / `pull` rewriting mtime on stale content."""
    old = (datetime.now(timezone.utc) - timedelta(seconds=WEEK)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rel = "coordination/_w1002a_touch.json"
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"timestamp": old, "status": "HEALTHY"}), encoding="utf-8")
    try:
        c = HeartbeatFileCollector("touch", rel, "engineering", sla_seconds=300)
        before = c.collect()[0].truth
        os.utime(p, (time.time(), time.time()))  # the forgery
        after = c.collect()[0].truth
        assert before == after == Truth.CACHED, (
            f"touch changed the verdict {before.value} -> {after.value}; filesystem "
            "timestamps must not influence freshness"
        )
    finally:
        p.unlink(missing_ok=True)


# --- observation time must stay separate from production time ----------------

def test_observed_at_and_produced_at_are_distinct_fields(tmp_path):
    old = (datetime.now(timezone.utc) - timedelta(seconds=WEEK)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = _collect(tmp_path, {"timestamp": old, "status": "HEALTHY"})
    d = r.to_dict()
    assert d.get("collected_at"), "collector observation time must be recorded"
    assert d.get("produced_at"), "produced_at must be surfaced on the success path"
    # STRICT (R4). This fixture guarantees a touched file and a week-old payload, so
    # file_modified_at must be PRESENT and must DIFFER. The prior form allowed
    # `is None` to satisfy the assertion, which let any collector that never populates
    # the field pass unconditionally — a vacuous test masquerading as a guarantee.
    assert d.get("file_modified_at"), (
        "file_modified_at must be recorded so an operator can see a touched file"
    )
    assert d["file_modified_at"] != d["produced_at"], (
        "file_modified_at must never equal produced_at"
    )


# --- sequence: frozen output must be detectable -------------------------------

def test_frozen_sequence_is_detectable(tmp_path):
    """A producer that stops advancing its sequence is stale even if it keeps writing."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = _collect(tmp_path, {"timestamp": now, "producer_id": "p", "sequence": 42,
                            "status": "HEALTHY"})
    assert "sequence" in json.dumps(r.to_dict()), (
        "sequence must be carried through so frozen-producer detection is possible"
    )


# --- ModelBindingCollector inherits the rule ----------------------------------

def test_model_binding_collector_does_not_age_by_mtime():
    """ModelBindingCollector aged role_bindings.json by mtime — same substitution."""
    r = ModelBindingCollector().collect()[0]
    # Skip only when the FILE is missing. "no producer timestamp" is the condition under
    # test — an earlier version of this guard swallowed it and turned the assertion into
    # a skip, which is a silent pass. That is the defect class this suite exists to stop.
    if r.error and ("absent" in r.error or "unreadable" in r.error):
        pytest.skip("role_bindings.json unavailable in this checkout")
    assert r.truth == Truth.UNKNOWN or r.value.get("produced_at"), (
        "role bindings carry no producer timestamp; ageing them by file mtime means a "
        f"git checkout resets their apparent freshness. Got {r.truth.value}."
    )
