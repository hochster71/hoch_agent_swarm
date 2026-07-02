import json
import os

def test_helm_profile_exists():
    profile_path = "config/agents/helm.agent.json"
    assert os.path.exists(profile_path), f"{profile_path} does not exist"
    
    with open(profile_path, "r") as f:
        profile = json.load(f)
        
    assert profile["agent_id"] == "helm"
    assert profile["name"] == "HELM"
    assert profile["release_authority"] is False
    assert profile["can_clear_no_active_release_go"] is False
    assert profile["routing_enabled"] is False
    assert "Steer, don't drift." in profile["doctrine"]

def test_helm_system_prompt_doctrine():
    prompt_path = "docs/prompts/helm_system_prompt.md"
    assert os.path.exists(prompt_path), f"{prompt_path} does not exist"
    
    with open(prompt_path, "r") as f:
        content = f.read()
        
    assert "HELM" in content
    assert "Final Verifier controls release" in content
    assert "Evidence beats narrative" in content
    assert "Runtime Truth is authority" in content
    assert "NO_ACTIVE_RELEASE_GO" in content
