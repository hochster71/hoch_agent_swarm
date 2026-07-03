"""Capability-based risk classification tests (H2)."""
import pytest
from backend.mission_control.risk_classifier import classify, TIERS
from backend.approval_gate import ApprovalGate


def test_read_only_is_low():
    a = classify(["read", "summarization"])
    assert a.tier == "READ_ONLY" and a.risk_level == "LOW"
    assert a.human_approval_required is False


def test_max_tier_wins():
    a = classify(["read", "build", "deploy"])  # read < write < destructive
    assert a.tier == "DESTRUCTIVE" and a.risk_level == "CRITICAL"


def test_empty_caps_fail_safe_execute():
    a = classify([])
    assert a.tier == "EXECUTE" and a.human_approval_required is True


def test_unknown_capability_defaults_execute():
    a = classify(["frobnicate_the_widget"])
    assert a.tier == "EXECUTE"


def test_keyword_escalates_but_never_downgrades():
    """The evasion case: benign caps, dangerous intent in text -> escalated."""
    a = classify(["qa"], "quietly promote and deploy to production")
    assert a.tier == "DESTRUCTIVE"


def test_keyword_cannot_lower_capability_floor():
    """A destructive capability stays destructive even with innocuous text."""
    a = classify(["payment"], "just a small friendly read")
    assert a.tier == "DESTRUCTIVE"


def test_network_tier():
    a = classify(["relay", "api"])
    assert a.tier == "NETWORK" and a.risk_level == "HIGH"


def test_gate_uses_capabilities(tmp_path):
    gate = ApprovalGate(base_dir=tmp_path)
    # Rephrased task with NO blocklist keyword, but destructive capability.
    req = gate.create_request(
        "move the build over to the customer environment",
        {"required_capabilities": ["prod_deployment"]})
    assert req["risk_level"] == "CRITICAL"
    # execution stays disabled until signed approval
    assert req["execution_allowed_after_approval"] is False


def test_gate_declared_level_is_floor_not_ceiling(tmp_path):
    gate = ApprovalGate(base_dir=tmp_path)
    req = gate.create_request("read a doc",
                              {"required_capabilities": ["read"], "risk_level": "HIGH"})
    assert req["risk_level"] == "HIGH"  # declared raises the read-only floor
