from backend.coding_control_plane.defect_classifier import DefectClassifier

def test_defect_classifier_critical():
    classifier = DefectClassifier()
    res = classifier.classify("Fatal server crash on startup", "backend")
    assert res["severity"] == "CRITICAL"
    assert res["owner_agent"] == "Architect Agent"
    assert res["safe_auto_fix"] is False

def test_defect_classifier_warning():
    classifier = DefectClassifier()
    res = classifier.classify("UserWarning: deprecation of module", "backend")
    assert res["severity"] == "MEDIUM"
    assert res["owner_agent"] == "Refactor Agent"
    assert res["safe_auto_fix"] is True

def test_defect_classifier_formatting():
    classifier = DefectClassifier()
    res = classifier.classify("ruff formatting issues detected in main.py", "backend")
    assert res["severity"] == "LOW"
    assert res["owner_agent"] == "Lint Agent"
    assert res["safe_auto_fix"] is True
