import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.toolops_manager import ToolOpsManager
from backend.modelops_manager import ModelOpsManager
from pathlib import Path
import json
import shutil

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown_toolops_files():
    base_dir = Path(__file__).resolve().parent.parent
    reg_path = base_dir / "data" / "prompt_registry" / "tool_registry.json"
    state_path = base_dir / "data" / "prompt_registry" / "toolops_state.json"
    model_reg_path = base_dir / "data" / "prompt_registry" / "model_registry.json"
    
    # Backups
    reg_bak = base_dir / "data" / "prompt_registry" / "tool_registry.json.bak"
    state_bak = base_dir / "data" / "prompt_registry" / "toolops_state.json.bak"
    model_reg_bak = base_dir / "data" / "prompt_registry" / "model_registry.json.bak"
    
    if reg_path.exists():
        shutil.copy(reg_path, reg_bak)
    if state_path.exists():
        shutil.copy(state_path, state_bak)
    if model_reg_path.exists():
        shutil.copy(model_reg_path, model_reg_bak)
        
    yield
    
    # Restore
    if reg_bak.exists():
        shutil.copy(reg_bak, reg_path)
        reg_bak.unlink()
    if state_bak.exists():
        shutil.copy(state_bak, state_path)
        state_bak.unlink()
    if model_reg_bak.exists():
        shutil.copy(model_reg_bak, model_reg_path)
        model_reg_bak.unlink()

def test_toolops_endpoints_exist_and_fetch():
    # 1. Fetch tools
    res = client.get("/api/toolops/tools")
    assert res.status_code == 200
    tools = res.json()
    assert isinstance(tools, list)
    assert any(t["tool_id"] == "shell" for t in tools)

    # 2. Fetch policies
    res_policies = client.get("/api/toolops/policies")
    assert res_policies.status_code == 200
    data = res_policies.json()
    assert "policies" in data
    assert len(data["policies"]) >= 5

    # 3. Fetch blocked actions
    res_blocked = client.get("/api/toolops/blocked")
    assert res_blocked.status_code == 200
    data_blocked = res_blocked.json()
    assert "blocked_actions" in data_blocked
    assert "pending_approvals" in data_blocked

def test_toolops_authorization_safe_vs_destructive():
    # 1. Safe read-only tool should auto-approve
    payload_safe = {
        "tool_id": "file_read",
        "agent_role": "Developer",
        "prompt_family": "CODING",
        "model_id": "ollama/llama3",
        "params": {"file_path": "test.txt"}
    }
    res_safe = client.post("/api/toolops/authorize", json=payload_safe)
    assert res_safe.status_code == 200
    assert res_safe.json()["verdict"] == "APPROVED"

    # 2. Destructive tool (shell) should require operator approval (raising 400 with APPROVAL_REQUIRED)
    payload_destructive = {
        "tool_id": "shell",
        "agent_role": "SystemOwner",
        "prompt_family": "CODING",
        "model_id": "ollama/llama3",
        "params": {"command": "ls -la"}
    }
    res_destructive = client.post("/api/toolops/authorize", json=payload_destructive)
    assert res_destructive.status_code == 400
    assert "APPROVAL_REQUIRED" in res_destructive.json()["detail"]

def test_unknown_host_blocking():
    # Outbound http request to unknown host should be blocked
    payload = {
        "tool_id": "http_request",
        "agent_role": "Researcher",
        "prompt_family": "QA",
        "model_id": "ollama/llama3",
        "params": {"url": "https://malicious-server.evil.com/exfiltrate"}
    }
    res = client.post("/api/toolops/authorize", json=payload)
    assert res.status_code == 400
    assert "UNKNOWN_HOST_BLOCKED" in res.json()["detail"]

    # Request to approved host should require approval (requires_approval is True)
    payload_ok = {
        "tool_id": "http_request",
        "agent_role": "Researcher",
        "prompt_family": "QA",
        "model_id": "ollama/llama3",
        "params": {"url": "https://github.com/api/v3"}
    }
    res_ok = client.post("/api/toolops/authorize", json=payload_ok)
    assert res_ok.status_code == 400
    assert "APPROVAL_REQUIRED" in res_ok.json()["detail"]

def test_exfiltration_and_blocked_patterns():
    # 1. Secret exfiltration pattern (passwd)
    payload = {
        "tool_id": "file_read",
        "agent_role": "Developer",
        "prompt_family": "CODING",
        "model_id": "ollama/llama3",
        "params": {"file_path": "/etc/passwd"}
    }
    res = client.post("/api/toolops/authorize", json=payload)
    assert res.status_code == 400
    assert "BLOCKED_EXFILTRATION_PATTERN" in res.json()["detail"]

    # 2. Tool-specific blocked pattern
    payload_specific = {
        "tool_id": "shell",
        "agent_role": "SystemOwner",
        "prompt_family": "CODING",
        "model_id": "ollama/llama3",
        "params": {"command": "rm -rf /Users/michaelhoch"}
    }
    res_spec = client.post("/api/toolops/authorize", json=payload_specific)
    assert res_spec.status_code == 400
    assert "BLOCKED_PATTERN_DETECTED" in res_spec.json()["detail"]

def test_low_trust_model_privileged_block():
    # Mock model evaluation failure for ollama/llama3
    modelops = ModelOpsManager()
    modelops.execute_eval("ollama/llama3", simulated_score=0.55) # Model is now failed_eval (low trust)

    # Attempting to authorize a privileged tool (database) with low-trust model should be blocked
    payload = {
        "tool_id": "database",
        "agent_role": "SystemOwner",
        "prompt_family": "CODING",
        "model_id": "ollama/llama3",
        "params": {"query": "SELECT * FROM users"}
    }
    res = client.post("/api/toolops/authorize", json=payload)
    assert res.status_code == 400
    assert "LOW_TRUST_MODEL_BLOCKED" in res.json()["detail"]

def test_approval_overrides_flow():
    # Request shell tool (requires approval)
    payload = {
        "tool_id": "shell",
        "agent_role": "SystemOwner",
        "prompt_family": "CODING",
        "model_id": "ollama/llama3",
        "params": {"command": "echo 'Hello World'"}
    }
    
    with pytest.raises(ValueError) as exc:
        mgr = ToolOpsManager()
        mgr.authorize_action(**payload)
    assert "APPROVAL_REQUIRED" in str(exc.value)

    # Fetch pending approvals to get action_id
    res_blocked = client.get("/api/toolops/blocked")
    pending = res_blocked.json()["pending_approvals"]
    assert len(pending) > 0
    action_id = pending[0]["action_id"]

    # Approve the action
    res_app = client.post("/api/toolops/approve", json={"action_id": action_id, "operator": "CLAWDE HOCH"})
    assert res_app.status_code == 200
    assert res_app.json()["verdict"] == "APPROVED"

    # Authorize again, should pass now!
    res_auth = client.post("/api/toolops/authorize", json=payload)
    assert res_auth.status_code == 200
    assert res_auth.json()["verdict"] == "APPROVED"

def test_ci_compliance_gate():
    res = client.post("/api/toolops/ci-gate")
    assert res.status_code == 200
    assert res.json()["status"] == "PASSED"
