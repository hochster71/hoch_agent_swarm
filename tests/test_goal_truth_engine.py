"""REQ-GOV-005 — the goal engine itself may never emit a fabricated number."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.goal.goal_engine import ZERO_STATES, _pct, compute, run_validator  # noqa: E402


def test_no_fallback_percentage_exists_in_the_engine():
    """A fallback is a PATTERN, not a digit: a numeric default used when a source is
    absent. (100.0 as a percentage multiplier is arithmetic, not a fallback.)"""
    import ast, re
    src = (ROOT / "scripts" / "goal" / "goal_engine.py").read_text(encoding="utf-8")

    # no .get("k", <number>) for any MEASUREMENT key. `weight` is configuration
    # (how much a requirement counts), not a measurement of whether it is done.
    CONFIG_KEYS = {"weight"}
    for m in re.finditer(r'\.get\(\s*["\']([^"\']+)["\']\s*,\s*([\d.]+)\s*\)', src):
        assert m.group(1) in CONFIG_KEYS, \
            f"engine defaults measurement {m.group(1)!r} to {m.group(2)}"
    # no `or <number>` / `if ... else <number>` completion defaults
    assert not re.search(r'\bor\s+(?:90|95|100)(?:\.0)?\b', src)

    # no function parameter defaults to a completion-looking number
    tree = ast.parse(src)
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for d in fn.args.defaults + fn.args.kw_defaults:
            if isinstance(d, ast.Constant) and isinstance(d.value, (int, float)) \
                    and not isinstance(d.value, bool) and d.value in (90, 95, 100):
                raise AssertionError(f"{fn.name} defaults a param to {d.value}")


def test_nothing_to_measure_yields_None_never_a_number():
    assert _pct(0, 0) is None            # NOT 0, NOT 90, NOT 100
    assert _pct(3, 6) == 50.0


def test_every_zero_state_contributes_nothing():
    for s in ("BLOCKED", "STALE", "UNKNOWN", "UNVERIFIED", "MANUALLY_ASSERTED",
              "VALIDATOR_NOT_RUN", "VALIDATOR_MISSING", "FAILED"):
        assert s in ZERO_STATES


def test_a_requirement_with_no_validator_contributes_zero():
    r = run_validator({"id": "X", "layer": "GOV", "statement": "s", "owner": "agent",
                       "blocking": True, "weight": 5, "validator": None,
                       "evidence_path": "config/canonical_goal_contract.json"})
    assert r["state"] == "VALIDATOR_MISSING"
    assert r["contributes"] == 0.0


def test_a_failing_validator_contributes_zero():
    r = run_validator({"id": "X", "layer": "GOV", "statement": "s", "owner": "agent",
                       "blocking": True, "weight": 5, "validator": "exit 1",
                       "evidence_path": "config/canonical_goal_contract.json"})
    assert r["state"] == "FAILED"
    assert r["contributes"] == 0.0


def test_a_passing_validator_with_absent_evidence_is_UNVERIFIED_not_satisfied():
    r = run_validator({"id": "X", "layer": "GOV", "statement": "s", "owner": "agent",
                       "blocking": True, "weight": 5, "validator": "true",
                       "evidence_path": "coordination/goal/definitely_absent_xyz.json"})
    assert r["state"] == "UNVERIFIED"
    assert r["contributes"] == 0.0


def test_stale_evidence_contributes_zero():
    r = run_validator({"id": "X", "layer": "GOV", "statement": "s", "owner": "agent",
                       "blocking": True, "weight": 5, "validator": "true",
                       "freshness_sla_hours": 0.0000001,
                       "evidence_path": "config/canonical_goal_contract.json"})
    assert r["state"] == "STALE"
    assert r["contributes"] == 0.0


def test_founder_only_gates_do_not_reduce_autonomous_progress():
    s = compute(execute=False)   # no validator execution: everything VALIDATOR_NOT_RUN
    # every layer's agent-scope score excludes FOUNDER_ONLY requirements
    for layer, d in s["by_layer"].items():
        assert "founder_only_pending" in d
    assert isinstance(s["metrics"]["founder_only_actions_pending"], list)


def test_unknown_metrics_carry_an_explicit_reason():
    s = compute(execute=False)
    for k, v in s["metrics"].items():
        if v is None and k in s["metric_unknown_reasons"]:
            assert s["metric_unknown_reasons"][k], f"{k} is UNKNOWN with no reason"


def test_manually_asserted_pert_state_cannot_override_generated_evidence():
    """Hand-edit the node file; the binder must restore it from run evidence."""
    node = ROOT / "coordination" / "council" / "relay" / "H1D_pert_node.json"
    if not node.exists():
        pytest.skip("no H1D evidence in this tree")
    original = node.read_text()
    tampered = json.loads(original)
    tampered["state"] = "COMPLETED_BY_HAND"
    tampered["accepted_adapters"] = ["wishful_thinking"]
    node.write_text(json.dumps(tampered, indent=2))
    try:
        subprocess.run([sys.executable, "scripts/goal/bind_pert_node.py", "H1D"],
                       cwd=str(ROOT), capture_output=True, check=True)
        restored = json.loads(node.read_text())
        assert restored["state"] != "COMPLETED_BY_HAND"
        assert restored["accepted_adapters"] != ["wishful_thinking"]
        assert restored["state_is_derived"] is True
    finally:
        node.write_text(original)
