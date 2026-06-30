import os
import json
import sqlite3
import urllib.request
import urllib.error
from unittest.mock import MagicMock, patch
from pathlib import Path
from backend.brain.autonomy_loop import AutonomyLoop
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

def test_autonomy_loop_discovery_offline(tmp_path):
    # Set up temporary dirs
    root_dir = tmp_path
    evidence_dir = root_dir / "docs/evidence/nodes"
    evidence_dir.mkdir(parents=True)
    
    # Initialize ledger file
    ledger_path = root_dir / "docs/mission"
    ledger_path.mkdir(parents=True)
    (ledger_path / "mission-ledger.md").write_text("# HAS Mission Ledger\n", encoding="utf-8")

    loop = AutonomyLoop(root_dir=str(root_dir))

    # Mock urllib response to raise connection refused
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        res = loop.run_discovery()
        
        assert res["status"] == "candidate_offline"
        assert res["reachable"] is False
        assert res["models_observed"] == []
        
        # Verify db persistence
        conn = sqlite3.connect(DB_PATH)
        apply_pragmas(conn)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM runtime_worker_mesh WHERE node_name = 'mbpro'").fetchone()
        assert row is not None
        assert row["status"] == "candidate_offline"
        assert row["routing_enabled"] == 0
        assert row["approval_required"] == 1
        conn.close()

        # Verify evidence document
        evidence_files = list(evidence_dir.glob("*-worker-discovery.md"))
        assert len(evidence_files) == 1
        content = evidence_files[0].read_text(encoding="utf-8")
        assert "CANDIDATE_OFFLINE" in content
        assert "Routing Status" in content

        # Verify mission ledger update
        ledger_content = (ledger_path / "mission-ledger.md").read_text(encoding="utf-8")
        assert "Probe worker `mbpro`; set status to CANDIDATE_OFFLINE" in ledger_content


def test_autonomy_loop_discovery_online(tmp_path):
    # Set up temporary dirs
    root_dir = tmp_path
    evidence_dir = root_dir / "docs/evidence/nodes"
    evidence_dir.mkdir(parents=True)
    
    # Initialize ledger file
    ledger_path = root_dir / "docs/mission"
    ledger_path.mkdir(parents=True)
    (ledger_path / "mission-ledger.md").write_text("# HAS Mission Ledger\n", encoding="utf-8")

    loop = AutonomyLoop(root_dir=str(root_dir))

    # Mock urllib response to return valid Ollama tags JSON
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "llama3:8b"},
                {"name": "gemma3:4b"}
            ]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = loop.run_discovery()
        
        assert res["status"] == "active_online"
        assert res["reachable"] is True
        assert "llama3:8b" in res["models_observed"]
        assert "gemma3:4b" in res["models_observed"]
        
        # Verify db persistence
        conn = sqlite3.connect(DB_PATH)
        apply_pragmas(conn)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM runtime_worker_mesh WHERE node_name = 'mbpro'").fetchone()
        assert row is not None
        assert row["status"] == "active_online"
        assert row["routing_enabled"] == 0
        assert row["approval_required"] == 1
        conn.close()

        # Verify evidence document
        evidence_files = list(evidence_dir.glob("*-worker-discovery.md"))
        assert len(evidence_files) == 1
        content = evidence_files[0].read_text(encoding="utf-8")
        assert "ACTIVE_ONLINE" in content
        assert "llama3:8b" in content

        # Verify mission ledger update
        ledger_content = (ledger_path / "mission-ledger.md").read_text(encoding="utf-8")
        assert "Probe worker `mbpro`; set status to ACTIVE_ONLINE" in ledger_content
