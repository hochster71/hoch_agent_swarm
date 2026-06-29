import os
from backend.meta_orchestrator.omission_detector import OmissionDetector

def test_omission_detector_runs_scans():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    detector = OmissionDetector(project_root)
    gaps = detector.run_all_scans()
    
    assert isinstance(gaps, list)
    # Check that each gap has expected structure
    for gap in gaps:
        assert "category" in gap
        assert "target" in gap
        assert "description" in gap
        assert "severity" in gap
