"""REQ-GOV-005 — behavioral proofs + seeded regressions.

Part 1 proves each former fallback now FAILS CLOSED.
Part 2 REINTRODUCES each prohibited pattern into a scratch copy and proves the scanner
       catches it. A scanner that cannot detect the regression is not a control.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.runtime_truth import primitives as rt  # noqa: E402

SCANNER = ROOT / "scripts" / "verify_runtime_truth_defaults.py"


# ==========================================================================
# PART 1 — the former fallbacks now fail closed
# ==========================================================================

def test_missing_timestamp_yields_the_ratified_shape():
    """The exact contract the founder specified."""
    f = rt.freshness(None)
    assert f["freshness"] == "UNKNOWN"
    assert f["fresh"] is False
    assert f["age_seconds"] is None
    assert f["timestamp_status"] == "MISSING"


def test_missing_timestamp_is_never_stamped_with_now():
    """The old wrap_telemetry_dict did: if not last_updated_iso: last_updated_iso = now().
    Absence of evidence rendered as freshness=0.0s, confidence=HIGH."""
    t = rt.truth(42, source="s", source_updated_at=None)
    assert t["source_updated_at"] is None
    assert t["observed_at"] is None
    assert t["age_seconds"] is None          # NOT 0.0
    assert t["fresh"] is False               # NOT True
    assert t["confidence"] != "HIGH"
    assert t["state"] == "UNVERIFIED"


def test_missing_value_is_MISSING_not_a_number():
    t = rt.truth(source="autonomous_cadence_telemetry")
    assert t["value"] is None                # NOT 90.0
    assert t["state"] == "MISSING"
    assert t["confidence"] == "NONE"


def test_truth_wrapper_cannot_express_a_fallback():
    """The API itself makes the old bug unrepresentable."""
    import inspect
    assert "fallback" not in inspect.signature(rt.truth).parameters
    with pytest.raises(TypeError):
        rt.truth(None, source="s", fallback=90.0)   # type: ignore[call-arg]


def test_malformed_timestamp_is_ERROR_not_fresh():
    f = rt.freshness("not-a-timestamp")
    assert f["timestamp_status"] == "ERROR"
    assert f["fresh"] is False
    assert f["age_seconds"] is None


def test_future_timestamp_is_not_treated_as_fresh():
    f = rt.freshness("2099-01-01T00:00:00Z")
    assert f["fresh"] is False
    assert f["timestamp_status"] == "ERROR"


def test_stale_source_is_STALE_not_OK():
    old = "2020-01-01T00:00:00Z"
    t = rt.truth(7, source="s", source_updated_at=old, sla_seconds=60, verified=True)
    assert t["state"] == "STALE"
    assert t["fresh"] is False
    assert t["confidence"] != "HIGH"


def test_only_a_verified_fresh_observation_reaches_OK():
    now = rt.generated_at()
    t = rt.truth(7, source="s", source_updated_at=now, sla_seconds=3600, verified=True)
    assert t["state"] == "OK"
    assert t["validated_at"] is not None
    assert rt.is_displayable_success(t) is True
    # unverified: present, but nobody confirmed it
    u = rt.truth(7, source="s", source_updated_at=now, sla_seconds=3600, verified=False)
    assert u["state"] == "UNVERIFIED"
    assert rt.is_displayable_success(u) is False


def test_unknown_is_never_displayable_as_success():
    assert rt.is_displayable_success(rt.unknown("s")) is False
    assert rt.is_displayable_success(rt.error("s", "boom")) is False
    assert rt.is_displayable_success(rt.truth(source="s")) is False


def test_pert_server_wrapper_delegates_to_truth_and_drops_legacy_fallback():
    """An un-migrated caller passing fallback= must NOT get its default honoured."""
    sys.path.insert(0, str(ROOT / "backend"))
    from backend import pert_server as ps
    t = ps.wrap_telemetry_dict(None, "autonomous_cadence_telemetry", None, fallback=90.0)
    assert t["value"] is None                # the 90.0 is swallowed, never honoured
    assert t["state"] == "MISSING"
    assert t["age_seconds"] is None


def test_goal_completion_is_sourced_from_the_canonical_engine_not_a_literal():
    src = (ROOT / "backend" / "pert_server.py").read_text(encoding="utf-8")
    assert "canonical_goal_engine" in src
    # the old weight-sum-over-hardcoded-statuses must no longer feed the metric
    assert 'wrap_telemetry_dict(int(goal_completion_percent)' not in src


# ==========================================================================
# PART 2 — seeded regressions: reintroduce each pattern, scanner must FAIL
# ==========================================================================

def _run_scanner_on(tmp_root: Path) -> int:
    """Run the scanner COPY inside the scratch tree, so its ROOT resolves to the scratch
    tree and it scans the seeded files -- not the real repo."""
    scanner = tmp_root / "scripts" / "verify_runtime_truth_defaults.py"
    return subprocess.run([sys.executable, str(scanner)], cwd=str(tmp_root),
                          capture_output=True, text=True).returncode


@pytest.fixture
def scratch(tmp_path):
    """A minimal tree the scanner can scan: real scanner, copied targets."""
    (tmp_path / "backend" / "runtime_truth").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "coordination" / "goal").mkdir(parents=True)
    for rel in ["backend/pert_server.py", "backend/main.py",
                "backend/runtime_truth/primitives.py"]:
        (tmp_path / rel).write_text((ROOT / rel).read_text(encoding="utf-8"),
                                    encoding="utf-8")
    (tmp_path / "backend" / "__init__.py").write_text("")
    (tmp_path / "backend" / "runtime_truth" / "__init__.py").write_text("")
    (tmp_path / "scripts" / "verify_runtime_truth_defaults.py").write_text(
        SCANNER.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_seeded_baseline_is_clean(scratch):
    """Control: the unmodified tree passes. Without this, the regressions below prove nothing."""
    assert _run_scanner_on(scratch) == 0


def test_seeded_regression_P1_metric_fallback_default(scratch):
    p = scratch / "backend" / "pert_server.py"
    src = p.read_text()
    # goal_completion_percent no longer flows through compute_gap at all -- it comes
    # from the canonical engine. Seed the regression on a metric that DOES.
    before = 'compute_gap.get("compute_utilization_percent")'
    assert before in src, "fixture drifted: seed target absent"
    src = src.replace(before, 'compute_gap.get("compute_utilization_percent", 55.0)', 1)
    p.write_text(src)
    assert _run_scanner_on(scratch) != 0, "scanner failed to catch a reintroduced fallback default"


def test_seeded_regression_P2_fallback_kwarg(scratch):
    p = scratch / "backend" / "pert_server.py"
    src = p.read_text()
    src = src.replace('wrap_telemetry_dict(high_risk_approval_list, "has_approval_queue_ledger", metrics_ts)',
                      'wrap_telemetry_dict(high_risk_approval_list, "has_approval_queue_ledger", metrics_ts, fallback=[])', 1)
    p.write_text(src)
    assert _run_scanner_on(scratch) != 0, "scanner failed to catch a reintroduced fallback= kwarg"


def test_seeded_regression_P3_fabricated_timestamp(scratch):
    p = scratch / "backend" / "pert_server.py"
    src = p.read_text()
    src += (
        "\n\ndef _seeded_regression(last_updated_ts=None):\n"
        "    if not last_updated_ts:\n"
        "        last_updated_ts = datetime.now(timezone.utc).isoformat()\n"
        "    return last_updated_ts\n"
    )
    p.write_text(src)
    assert _run_scanner_on(scratch) != 0, "scanner failed to catch a reintroduced now() substitution"


def test_seeded_regression_P4_fabricated_confidence_literal(scratch):
    p = scratch / "backend" / "pert_server.py"
    src = p.read_text()
    src = src.replace('confidence_string = "UNKNOWN"',
                      'confidence_string = "95% Confidence (PERT Beta-Distribution)"', 1)
    p.write_text(src)
    assert _run_scanner_on(scratch) != 0, "scanner failed to catch a reintroduced fabricated literal"


def test_seeded_regression_P5_truth_wrapper_can_fake_freshness(scratch):
    p = scratch / "backend" / "runtime_truth" / "primitives.py"
    src = p.read_text()
    # reintroduce the original bug: missing timestamp -> now()
    src = src.replace("    dt = parse_ts(source_timestamp)\n    if dt is None:",
                      "    dt = parse_ts(source_timestamp)\n    if dt is None:\n        dt = utc_now()\n    if False:", 1)
    p.write_text(src)
    assert _run_scanner_on(scratch) != 0, "scanner failed to catch a truth wrapper that fakes freshness"


def test_seeded_regression_readiness_score_defaults_to_100(scratch):
    p = scratch / "backend" / "main.py"
    src = p.read_text()
    src = src.replace('.get("readiness_score")', '.get("readiness_score", 100)', 1)
    p.write_text(src)
    assert _run_scanner_on(scratch) != 0, "scanner failed to catch readiness_score defaulting to 100"


def test_seeded_regression_status_defaults_to_PASS(scratch):
    p = scratch / "backend" / "main.py"
    src = p.read_text()
    src = src.replace('.get("status", "UNKNOWN")', '.get("status", "PASS")', 1)
    p.write_text(src)
    assert _run_scanner_on(scratch) != 0, "scanner failed to catch status defaulting to PASS"
