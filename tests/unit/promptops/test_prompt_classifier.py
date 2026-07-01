from backend.promptops.prompt_classifier import PromptClassifier

def test_prompt_classifier():
    classifier = PromptClassifier()
    
    # Check Kubernetes classification
    assert classifier.classify("Add k3d Kubernetes lane but do not replace Compose until gates pass") == "KUBERNETES_LANE"
    
    # Check Docker classification
    assert classifier.classify("Fix Docker UI truth mismatch, run docker_truth_check") == "DOCKER_RUNTIME"
    
    # Check general classification fallback
    assert classifier.classify("Build HAS e2e production ready no errors") == "GENERAL_E2E_BUILD"
