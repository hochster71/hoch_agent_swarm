from backend.promptops.fake_completion_risk import FakeCompletionRisk

def test_fake_completion_risk():
    risk_detector = FakeCompletionRisk()
    
    # Test high risk phrase
    high_res = risk_detector.detect_risk("Build HAS e2e production ready no errors complete done")
    assert high_res["risk_level"] == "HIGH"
    assert "production ready" in high_res["flagged_terms"]
    
    # Test low risk phrase
    low_res = risk_detector.detect_risk("Query active telemetry signals from SQLite database")
    assert low_res["risk_level"] == "LOW"
