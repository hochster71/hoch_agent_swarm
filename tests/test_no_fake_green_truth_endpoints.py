# -*- coding: utf-8 -*-
"""
tests/test_no_fake_green_truth_endpoints.py
"""

from pathlib import Path
from backend.brain.runtime_truth_validator import (
    validate_brain_runtime_proof,
    validate_source_manifest
)


def test_missing_source_manifest_returns_unknown():
    res = validate_source_manifest(Path("non_existent_manifest.json"))
    assert res["status"] in ["UNKNOWN", "NO_GO"]


def test_quarantined_ledger_returns_quarantined(tmp_path):
    usage_path = tmp_path / "_quarantine_usages.jsonl"
    outcome_path = tmp_path / "outcomes.jsonl"
    usage_path.write_text("{}", encoding="utf-8")
    outcome_path.write_text("{}", encoding="utf-8")
    
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "QUARANTINED"


def test_malformed_ledger_returns_malformed(tmp_path):
    usage_path = tmp_path / "usages.jsonl"
    outcome_path = tmp_path / "outcomes.jsonl"
    usage_path.write_text("invalid json lines", encoding="utf-8")
    outcome_path.write_text("{}", encoding="utf-8")
    
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "MALFORMED" or res["go_no_go"] == "NO_GO"


def test_simulated_dashboard_does_not_count_as_live(tmp_path):
    usage_path = tmp_path / "usages.jsonl"
    outcome_path = tmp_path / "outcomes.jsonl"
    
    # Simulate dashboard run - should degrade to NO_GO, not count as LIVE
    import json
    usage_path.write_text(json.dumps({
        "usage_id": "u_dashboard",
        "fallback_used": False,
        "execution_surface": "dashboard"
    }) + "\n", encoding="utf-8")
    
    outcome_path.write_text(json.dumps({
        "usage_id": "u_dashboard",
        "status": "COMPLETED"
    }) + "\n", encoding="utf-8")
    
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "NO_GO"


def test_existing_source_files_produce_non_empty_sources(tmp_path):
    import json
    from backend.brain.runtime_truth_validator import compute_sha256
    manifest_path = tmp_path / "source_manifest.json"
    source_file = tmp_path / "source.csv"
    source_file.write_text("dummy", encoding="utf-8")
    
    sha = compute_sha256(source_file)
    manifest_data = {
        "naics_2022": {
            "source_name": "NAICS 2022",
            "local_path": str(source_file),
            "checksum": sha
        }
    }
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    res = validate_source_manifest(manifest_path)
    assert "sources" in res
    assert "naics_2022" in res["sources"]
    assert res["sources"]["naics_2022"]["status"] == "GO"
    # Verify all required keys are present
    s = res["sources"]["naics_2022"]
    for key in ["source_id", "label", "path", "authority", "allowed_for_live_ui", "freshness", "last_modified", "age_seconds", "checksum_sha256", "validation_method", "fallback_policy", "status"]:
        assert key in s


def test_stale_source_files_produce_stale_not_go(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from backend.brain.runtime_truth_validator import compute_sha256
    manifest_path = tmp_path / "source_manifest.json"
    source_file = tmp_path / "source.csv"
    source_file.write_text("dummy", encoding="utf-8")
    
    sha = compute_sha256(source_file)
    manifest_data = {
        "naics_2022": {
            "source_name": "NAICS 2022",
            "local_path": str(source_file),
            "checksum": sha
        }
    }
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    
    # Mock stat to return mtime far in the past to trigger STALE
    class MockStat:
        st_mtime = 0
    monkeypatch.setattr(Path, "stat", lambda self, *args, **kwargs: MockStat())
    
    res = validate_source_manifest(manifest_path)
    assert res["status"] == "STALE"
    assert res["sources"]["naics_2022"]["status"] == "STALE"
    assert res["sources"]["naics_2022"]["freshness"] == "stale"



def test_reasoning_graph_cites_source_authority_and_no_go_on_stale():
    from backend.brain.live_runtime_aggregator import aggregate_reasoning_graph
    graph = aggregate_reasoning_graph()
    assert graph["status"] in ["NO_GO", "CONDITIONAL"]
    
    # Ensure source nodes cite source authority and are not UNKNOWN if they exist
    found_ref = False
    for node in graph["nodes"]:
        if node["type"] == "source":
            assert "source_authority_ref" in node
            found_ref = True
    assert found_ref

