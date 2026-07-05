import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

def test_evidence_ledger_logging():
    client = TestClient(app)
    
    payload = {
        "task": "Test capability execution ledger logging functionality",
        "context": "Staging unit test run",
        "industry": "NorthStar Swarm OS",
        "requested_action": "test"
    }
    
    response = client.post("/api/agent-router/route", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert "task_id" in data
    assert "winner" in data
    
    # Verify ledger file exists and contains the entry
    ledger_path = Path(__file__).parent.parent / "data" / "agent_execution_ledger.jsonl"
    assert ledger_path.exists()
    
    found = False
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry.get("task_id") == data["task_id"]:
                    found = True
                    # Check selected agent ID and content hash matches the winner
                    assert entry["selected_agent_id"] == data["winner"]["gene_id"]
                    assert entry["agent_content_hash"] == data["winner"]["content_hash"]
                    assert entry["registry_version"] is not None
                    break
                    
    assert found is True
