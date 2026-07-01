from backend.runtime_truth.readiness_calculator import calculate_governed_readiness

def test_meta_orchestrator_readiness():
    res = calculate_governed_readiness()
    assert "score" in res
    assert "caps" in res
