"""Tests for the G1 demand-validation gate (pure evaluate, no side effects)."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dv", REPO / "scripts" / "verify_demand_validation.py")
dv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dv)

TH = {"prospects": 10, "discovery_calls": 3, "wtp_signals": 1, "named_buyers": 1}


def test_pending_when_empty():
    v, c, m = dv.evaluate({"thresholds": TH})
    assert v == "PENDING"
    assert m["prospects"] == 10 and m["named_buyers"] == 1


def test_pass_when_all_thresholds_met():
    d = {"thresholds": TH, "prospects": [{}] * 10, "discovery_calls": [{}] * 3,
         "wtp_signals": [{}] * 1, "named_buyers": [{}] * 1}
    v, c, m = dv.evaluate(d)
    assert v == "PASS" and m == {}


def test_partial_reports_exact_shortfall():
    d = {"thresholds": TH, "prospects": [{}] * 10, "discovery_calls": [{}] * 1,
         "wtp_signals": [], "named_buyers": [{}] * 1}
    v, c, m = dv.evaluate(d)
    assert v == "PENDING"
    assert m["discovery_calls"] == 2 and m["wtp_signals"] == 1
    assert "prospects" not in m and "named_buyers" not in m
