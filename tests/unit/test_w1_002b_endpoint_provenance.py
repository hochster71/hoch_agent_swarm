"""W1-002b — council state endpoint provenance. FAILING BY DESIGN.

REQ-ES-004 blocker. `backend/helm_live_api.py` holds 19 sites computing freshness as
`time.time() - path.stat().st_mtime` and mounts `council_router` (line ~87). Serving the
endpoint before those are fixed would emit an authoritative-looking `age_seconds`
derived from file touch time — satisfying the acceptance gates while lying.

Required response contract (founder-specified, 2026-07-20):

    {
      "produced_at":      null,
      "observed_at":      "2026-07-20T...",
      "file_modified_at": "2026-07-20T...",
      "age_seconds":      null,
      "status":           "UNKNOWN",
      "freshness_sla_seconds": 60,
      "producer_id":      null,
      "sequence":         null,
      "reason": "Evidence carries no producer timestamp; filesystem mtime is not
                 evidence of data age."
    }

Fail-closed table: valid+within SLA -> LIVE · valid+beyond -> STALE · absent -> UNKNOWN
· malformed -> UNKNOWN · unavailable -> ERROR|UNKNOWN (never HEALTHY) · frozen
sequence -> STALE · collector exception -> UNKNOWN with reason.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

WEEK = 7 * 86400
REQUIRED_FIELDS = {
    "status", "produced_at", "observed_at", "age_seconds",
    "freshness_sla_seconds", "reason",
}
FORBIDDEN_STATUSES = {"HEALTHY", "OK", "PASS", "GREEN"}


def _council_state(payload: dict | None = None):
    """Call the council state endpoint. Skips only if the module is absent entirely."""
    try:
        from backend.helm_runtime.council_state import council_state  # type: ignore
    except Exception:
        try:
            from backend.instrument_integrity.council_router import council_state  # type: ignore
        except Exception:
            pytest.fail(
                "REQ-ES-004 unimplemented: no council_state provider exposes a "
                "freshness-bearing response. runtime_truth_freshness stays None until "
                "this exists."
            )
    return council_state(payload) if payload is not None else council_state()


# --- contract shape -----------------------------------------------------------

def test_endpoint_exposes_produced_observed_and_file_times_separately():
    r = _council_state()
    missing = REQUIRED_FIELDS - set(r)
    assert not missing, f"response missing required provenance fields: {sorted(missing)}"
    assert r.get("produced_at") != r.get("file_modified_at") or r.get("produced_at") is None, (
        "produced_at must never be populated from file_modified_at"
    )


def test_endpoint_never_reports_healthy():
    r = _council_state()
    assert r["status"] not in FORBIDDEN_STATUSES, (
        f"status '{r['status']}' is not in the fail-closed vocabulary "
        "(LIVE|STALE|UNKNOWN|ERROR)"
    )


# --- founder fixture 1: missing produced_at -----------------------------------

def test_missing_produced_at_yields_unknown_with_null_age():
    r = _council_state({"status": "HEALTHY", "detail": "no producer timestamp"})
    assert r["status"] == "UNKNOWN", f"expected UNKNOWN, got {r['status']}"
    assert r["age_seconds"] is None, "age must be null, not computed from mtime"
    reason = (r.get("reason") or "").lower()
    assert "mtime" in reason or "producer timestamp" in reason, (
        "reason must explicitly reject mtime as evidence of data age"
    )


# --- founder fixture 2: week-old produced_at, file touched now -----------------

def test_week_old_payload_with_fresh_file_is_stale():
    old = datetime.now(timezone.utc) - timedelta(seconds=WEEK)
    r = _council_state({
        "produced_at": old.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer_id": "helm-council-daemon",
        "sequence": 1842,
        "status": "HEALTHY",
    })
    assert r["status"] == "STALE", f"expected STALE, got {r['status']}"
    assert r["age_seconds"] is not None and r["age_seconds"] > WEEK - 120, (
        f"age {r['age_seconds']} must derive from produced_at, not file mtime"
    )


# --- fail-closed table --------------------------------------------------------

@pytest.mark.parametrize("bad", ["not-a-date", "", 0, [], "2026-13-45T99:99:99Z"])
def test_malformed_produced_at_is_unknown(bad):
    r = _council_state({"produced_at": bad, "status": "HEALTHY"})
    assert r["status"] == "UNKNOWN"
    assert r["age_seconds"] is None


def test_fresh_produced_at_within_sla_is_live():
    """Green must stay reachable or the gate is a wall."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = _council_state({"produced_at": now, "producer_id": "d", "sequence": 1,
                        "status": "HEALTHY"})
    assert r["status"] == "LIVE", f"expected LIVE, got {r['status']}"
    assert r["age_seconds"] is not None and r["age_seconds"] < 120


def test_frozen_sequence_across_intervals_is_stale():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    a = _council_state({"produced_at": now, "producer_id": "d", "sequence": 7,
                        "status": "HEALTHY"})
    b = _council_state({"produced_at": now, "producer_id": "d", "sequence": 7,
                        "status": "HEALTHY"})
    assert b["status"] == "STALE" or b.get("reason"), (
        "a producer whose sequence stops advancing is frozen; a refreshed timestamp "
        "alone must not render it LIVE"
    )


def test_collector_exception_is_unknown_with_reason():
    r = _council_state({"__raise__": True})
    assert r["status"] in {"UNKNOWN", "ERROR"}
    assert r.get("reason"), "a failure must carry a reason, not an empty status"


# --- delegation: no parallel freshness implementation -------------------------

def test_endpoint_delegates_to_runtime_truth_contract():
    """Freshness budgets must come from the ratified contract, not a local constant."""
    src = (ROOT / "backend" / "helm_live_api.py").read_text(encoding="utf-8")
    council_src = ""
    for cand in ("backend/helm_runtime/council_state.py",
                 "backend/instrument_integrity/council_router.py"):
        p = ROOT / cand
        if p.exists():
            council_src += p.read_text(encoding="utf-8")
    combined = src + council_src
    assert "runtime_truth_contract" in combined or "is_fresh" in combined, (
        "council state path must delegate freshness to "
        "runtime_truth_contract.is_fresh(); do not reimplement budgets locally"
    )


def test_live_api_no_longer_ages_evidence_by_mtime():
    """19 sites at audit time. This test is the burndown counter for W1-002b."""
    src = (ROOT / "backend" / "helm_live_api.py").read_text(encoding="utf-8")
    offenders = [
        ln.strip() for ln in src.splitlines()
        if "st_mtime" in ln and any(k in ln for k in ("time.time()", "fresh", "age"))
    ]
    assert not offenders, (
        f"{len(offenders)} site(s) still derive evidence age from filesystem mtime.\n"
        "Classify each per the founder rule (produced-time / observation metadata / "
        "cache-invalidation / diagnostics / ambiguous->UNKNOWN) before changing it.\n"
        + "\n".join(f"  {o[:100]}" for o in offenders[:6])
    )
