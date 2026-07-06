"""Tests for the orchestrator->structured-queue translator (pure mapping, no side effects)."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("hat", REPO / "scripts" / "hoch_action_translator.py")
hat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hat)


def test_orchestrator_flagged_approval_passes_through():
    rec = {"id": "x", "title": "Deploy prod", "risk": "HIGH", "requires_michael_approval": True}
    a, why = hat.map_action(rec)
    assert a["requires_michael_approval"] is True
    assert a["exec"]["type"] == "advisory"


def test_non_safe_risk_routes_to_approval():
    rec = {"id": "x", "title": "Tag release", "risk": "RELEASE", "requires_michael_approval": False}
    a, _ = hat.map_action(rec)
    assert a["requires_michael_approval"] is True


def test_safe_readiness_maps_to_run_script():
    rec = {"id": "x", "title": "Check BRAIN M1 readiness", "risk": "SAFE",
           "requires_michael_approval": False, "reason": "verify brain m1 readiness"}
    a, why = hat.map_action(rec)
    assert a["requires_michael_approval"] is False
    assert a["exec"] == {"type": "run_script", "script": "scripts/verify_brain_m1_readiness.py"}
    assert a["category"] == "verification"


def test_safe_build_maps_to_frontend_build():
    rec = {"id": "x", "title": "Rebuild the shell", "risk": "SAFE_BUILD",
           "requires_michael_approval": False, "reason": "npm run build the react dashboard"}
    a, _ = hat.map_action(rec)
    assert a["exec"]["type"] == "frontend_build"
    assert a["category"] == "build"


def test_unmapped_safe_task_defaults_to_approval():
    rec = {"id": "x", "title": "Design phase 2 voice policy", "risk": "SAFE_DOC",
           "requires_michael_approval": False, "reason": "write a design doc"}
    a, why = hat.map_action(rec)
    assert a["requires_michael_approval"] is True   # unknown = human
    assert "unmapped" in why
