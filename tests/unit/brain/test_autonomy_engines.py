# test_autonomy_engines.py
import pytest
from backend.brain.confidence_engine import ConfidenceEngine
from backend.brain.theory_proof_engine import TheoryProofEngine
from backend.brain.constraint_engine import ConstraintEngine
from backend.brain.adversarial_reviewer import AdversarialReviewer
from backend.brain.northstar_governor import NorthStarGovernor

def test_confidence_engine_caps_and_weights():
    engine = ConfidenceEngine()
    res = engine.evaluate_confidence()
    
    assert "confidence_score" in res
    assert "go_nogo" in res
    assert res["confidence_score"] <= 98.0
    assert isinstance(res["evidence"], dict)

def test_theory_proof_engine_validation():
    engine = TheoryProofEngine()
    res = engine.validate_theories()
    
    assert len(res) == 11
    assert "north_star_metric" in res
    assert res["north_star_metric"]["status"] == "PASS"
    assert res["north_star_metric"]["validation_score"] >= 0.90

def test_constraint_engine_lookup():
    engine = ConstraintEngine()
    res = engine.get_current_bottlenecks()
    
    assert "current_bottleneck" in res
    assert "recommendation" in res
    assert "system_capacity_utilization" in res

def test_adversarial_reviewer_rules():
    reviewer = AdversarialReviewer()
    
    # 1. Test secret key leakage detection
    res_secret = reviewer.scan_proposal("Publish code containing API key sk-proj-1234567890123456789012345678901234567890")
    assert res_secret["status"] == "REJECTED"
    assert any("secret key" in f.lower() for f in res_secret["findings"])

    # 2. Test write directory policy
    res_bad_path = reviewer.scan_proposal("Update settings file", file_path="/etc/passwd")
    assert res_bad_path["status"] == "REJECTED"
    assert any("outside" in f.lower() for f in res_bad_path["findings"])

    # 3. Test public port binding
    res_public = reviewer.scan_proposal("Start web server binding to 0.0.0.0 for public access")
    assert res_public["status"] == "REJECTED"
    assert any("public" in f.lower() for f in res_public["findings"])

    # 4. Test safe approved proposal
    res_safe = reviewer.scan_proposal("Implement unit tests for local reliability dashboard", file_path="/Users/michaelhoch/hoch_agent_swarm/tests/unit/brain/test_autonomy_engines.py")
    assert res_safe["status"] == "APPROVED"
    assert len(res_safe["findings"]) == 0

def test_north_star_governor():
    governor = NorthStarGovernor()
    
    # 1. Aligned task
    res_aligned = governor.check_alignment("Verify and package active monetization offers for customer trial")
    assert res_aligned["aligned"] is True
    assert res_aligned["governance_status"] == "PASS"

    # 2. Speculative unaligned task
    res_unaligned = governor.check_alignment("Research quantum-inspired optimization algorithms for parallel agent execution")
    assert res_unaligned["aligned"] is False
    assert res_unaligned["governance_status"] == "WARN"
