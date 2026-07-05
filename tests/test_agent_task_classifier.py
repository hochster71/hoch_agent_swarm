from backend.agent_task_classifier import AgentTaskClassifier

def test_task_classification():
    classifier = AgentTaskClassifier()
    
    # Test high risk incident response task
    res1 = classifier.classify({
        "task": "Run containment on server 10.0.4.15 due to suspected active data exfiltration.",
        "context": "Production database server",
        "industry": "",
        "requested_action": "Contain"
    })
    
    assert res1["domain"] == "Incident-Response"
    assert res1["risk_level"] == "HIGH"
    assert res1["confidence"] >= 0.5
    
    # Test low risk qa task
    res2 = classifier.classify({
        "task": "Run regression test suite on the login view",
        "context": "Staging server",
        "industry": "NorthStar Swarm OS",
        "requested_action": "test"
    })
    assert res2["domain"] == "QA"
    assert res2["industry"] == "NorthStar Swarm OS"
    assert res2["risk_level"] == "LOW"
