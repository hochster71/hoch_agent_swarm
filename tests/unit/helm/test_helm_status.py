from fastapi.testclient import TestClient
from backend.main import app
from backend.michael_ai.synthesizer import synthesize_current_state
from backend.michael_ai.prompt_builder import build_next_prompt

def test_helm_api_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/helm/status")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "helm"
    assert data["name"] == "HELM"
    assert data["release_authority"] is False
    assert data["routing_enabled"] is False
    assert data["current_constraints"]["active_blocker"] == "NO_ACTIVE_RELEASE_GO"

def test_michael_ai_helm_integration():
    state = synthesize_current_state()
    assert state["current_execution_agent"] == "HELM"
    assert "HELM" in state["available_execution_personae"]

    prompt_data = build_next_prompt()
    assert prompt_data["status"] == "success"
    assert "**TO**: HELM" in prompt_data["prompt"]
    assert "NO_ACTIVE_RELEASE_GO" in prompt_data["prompt"]
