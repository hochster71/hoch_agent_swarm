"""Adversarial tests for live-state collectors.

The danger these guard against is the mirror image of the envelope tests. Envelopes
could be flattened to green by an agent's declaration; collectors can be flattened to
green by a *stale payload that says it is healthy*. Every test below is an attempt to
get a dead signal, an unobservable host, or a broken environment to render as good news.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.collectors import (  # noqa: E402
    SCOPE_INDIRECT, SCOPE_LOCAL, SCOPE_REMOTE, Collector, GitCollector,
    HeartbeatFileCollector, ModelBindingCollector, ProcessCollector, Reading,
    TestCollector, Truth, collect_all, domain_verdict,
)


def _r(**kw) -> Reading:
    base = dict(name="x", domain="engineering", scope=SCOPE_LOCAL,
                collector="T", sla_seconds=300)
    base.update(kw)
    return Reading(**base)


def _ago(seconds: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


# --- the central invariant: freshness gates truth ----------------------------

def test_stale_healthy_payload_is_cached_not_observed():
    """The helm_supervisor case: says HEALTHY, six days old."""
    r = _r(value={"declared_status": "HEALTHY", "processes": {"backend": "RUNNING"}},
           observed_at=_ago(6 * 86400), sla_seconds=300)
    assert r.truth == Truth.CACHED
    assert not r.advancing        # cannot turn a panel green
    assert r.is_stale


def test_fresh_reading_is_observed_and_advancing():
    r = _r(value={"ok": True}, observed_at=_ago(10), sla_seconds=300)
    assert r.truth == Truth.OBSERVED
    assert r.advancing


def test_payload_claiming_pass_cannot_override_staleness():
    """live_telemetry_freshness.json: status PASS, 17 days old."""
    r = _r(value={"status": "PASS"}, observed_at=_ago(17 * 86400), sla_seconds=1800)
    assert r.truth == Truth.CACHED
    assert not r.advancing


def test_reading_with_no_timestamp_is_unknown_not_fresh():
    r = _r(value={"status": "HEALTHY"}, observed_at=None)
    assert r.truth == Truth.UNKNOWN
    assert not r.advancing


def test_error_reading_is_unknown_regardless_of_value():
    r = _r(value={"status": "HEALTHY"}, observed_at=_ago(1), error="unreadable")
    assert r.truth == Truth.UNKNOWN


def test_empty_value_is_unknown():
    r = _r(value={}, observed_at=_ago(1))
    assert r.truth == Truth.UNKNOWN


def test_boundary_exactly_at_sla_is_still_observed():
    # Pin read_at so the boundary is exact rather than microsecond-drifted.
    base = datetime.now(timezone.utc)
    at = _r(value={"ok": 1}, observed_at=base - timedelta(seconds=300),
            read_at=base, sla_seconds=300)
    assert at.truth == Truth.OBSERVED
    past = _r(value={"ok": 1}, observed_at=base - timedelta(seconds=301),
              read_at=base, sla_seconds=300)
    assert past.truth == Truth.CACHED


# --- host scope honesty -------------------------------------------------------

def test_process_collector_refuses_to_report_foreign_host():
    """Must not present sandbox PIDs as HELM's runtime."""
    rs = ProcessCollector().collect()
    r = rs[0]
    import platform
    if platform.node() != "michaels-macbook-pro":
        assert r.scope == SCOPE_REMOTE
        assert r.truth == Truth.UNKNOWN
        assert "not the HELM runtime host" in (r.error or "")


def test_heartbeat_collector_is_never_local_scope():
    """Reading a file the Mac wrote is INDIRECT, never live observation of the Mac."""
    c = HeartbeatFileCollector("hb", "nope.json", "engineering", 300)
    assert c.scope == SCOPE_INDIRECT


def test_model_collector_does_not_invent_liveness():
    r = ModelBindingCollector().collect()[0]
    if not r.error:
        assert r.value.get("invocation_state") == "NOT_OBSERVABLE"
        assert "ACTIVE" not in json.dumps(r.value.get("invocation_state"))


# --- environmental failure is not a code verdict ------------------------------

def test_unrunnable_suite_is_unknown_not_fail():
    """A missing dependency is not evidence the code is broken. Fake red is still fake."""
    r = TestCollector(target="tests/unit").collect()[0]
    if r.error and "not executable" in r.error:
        assert r.truth == Truth.UNKNOWN
        assert r.value == {}          # no PASS/FAIL claim at all


def test_tests_not_run_is_unknown():
    r = TestCollector(run=False).collect()[0]
    assert r.truth == Truth.UNKNOWN


# --- collectors never raise ---------------------------------------------------

def test_exploding_collector_yields_unknown_reading_not_crash():
    class Boom(Collector):
        name = "boom"

        def collect(self):
            raise RuntimeError("detonated")

    rs = Boom().safe_collect()
    assert len(rs) == 1
    assert rs[0].truth == Truth.UNKNOWN
    assert "detonated" in (rs[0].error or "")


def test_missing_file_collector_is_unknown_not_silent():
    r = HeartbeatFileCollector("gone", "does/not/exist.json", "engineering", 300).collect()[0]
    assert r.truth == Truth.UNKNOWN
    assert "absent" in (r.error or "")


# --- domain verdicts ----------------------------------------------------------

def test_domain_with_only_stale_readings_is_stale_not_observed():
    rs = [_r(domain="factory", value={"state": "ACTIVE"}, observed_at=_ago(999999))]
    assert domain_verdict(rs, "factory") == "STALE"


def test_domain_with_no_collector_is_named_explicitly():
    assert domain_verdict([], "family_ops") == "NO_COLLECTOR"


def test_domain_with_one_fresh_reading_is_observed():
    rs = [_r(domain="engineering", value={"ok": 1}, observed_at=_ago(5)),
          _r(domain="engineering", value={"x": 1}, observed_at=_ago(999999))]
    assert domain_verdict(rs, "engineering") == "OBSERVED"


def test_domain_with_only_errors_is_unreachable():
    rs = [_r(domain="deployment", error="no target")]
    assert domain_verdict(rs, "deployment") == "UNREACHABLE"


# --- git is genuinely live ----------------------------------------------------

def test_git_collector_reports_real_head():
    r = GitCollector().collect()[0]
    if not r.error:
        assert r.truth == Truth.OBSERVED
        assert len(r.value["head"]) >= 7
        assert r.value["worktree"].startswith(("CLEAN", "DIRTY"))


# --- board-level: stale signals cannot produce a green summary ----------------

def test_board_reports_stale_count_and_does_not_hide_it():
    from scripts.founder_live import render

    stale = _r(name="helm_supervisor", value={"declared_status": "HEALTHY"},
               observed_at=_ago(6 * 86400), sla_seconds=300)
    board = render([stale], [])
    assert "STALE SIGNALS: 1" in board
    assert "treat as UNKNOWN" in board


def test_board_never_prints_bare_healthy_for_stale_daemon():
    from scripts.founder_live import render

    stale = _r(name="helm_supervisor", value={"declared_status": "HEALTHY"},
               observed_at=_ago(6 * 86400), sla_seconds=300)
    board = render([stale], [])
    # the claim is shown, but always quoted and always paired with its age
    assert "claims 'HEALTHY'" in board
    assert "written 6.0d ago" in board
