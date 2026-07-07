# -*- coding: utf-8 -*-
"""
tests/test_live_runtime_truth_validator.py
"""

import json
from pathlib import Path
from backend.brain.runtime_truth_validator import (
    get_file_status,
    validate_source_manifest,
    validate_brain_runtime_proof,
    STALE_THRESHOLD_SECONDS
)


def test_get_file_status_missing(tmp_path):
    path = tmp_path / "non_existent.json"
    assert get_file_status(path) == "UNKNOWN"


def test_get_file_status_quarantined(tmp_path):
    path = tmp_path / "_quarantine_file.json"
    path.write_text("{}", encoding="utf-8")
    assert get_file_status(path) == "QUARANTINED"


def test_get_file_status_stale(tmp_path, monkeypatch):
    path = tmp_path / "file.json"
    path.write_text("{}", encoding="utf-8")
    # Mock stat to return mtime far in the past
    class MockStat:
        st_mtime = 0
    monkeypatch.setattr(Path, "stat", lambda self, *args, **kwargs: MockStat())
    assert get_file_status(path) == "STALE"


def test_get_file_status_malformed(tmp_path):
    path = tmp_path / "file.json"
    path.write_text("invalid json", encoding="utf-8")
    assert get_file_status(path) == "MALFORMED"


def test_validate_source_manifest(tmp_path):
    manifest_path = tmp_path / "source_manifest.json"
    manifest_data = {
        "test_source": {
            "source_name": "Test Source",
            "local_path": str(tmp_path / "source.csv"),
            "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # empty file sha256
        }
    }
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    
    # Check with missing CSV
    res = validate_source_manifest(manifest_path)
    assert res["status"] == "NO_GO"
    assert res["sources"]["test_source"]["status"] == "UNKNOWN"

    # Write empty CSV (matching checksum)
    csv_path = tmp_path / "source.csv"
    csv_path.write_bytes(b"")
    res = validate_source_manifest(manifest_path)
    assert res["status"] == "GO"
    assert res["sources"]["test_source"]["status"] == "GO"


def test_validate_brain_runtime_proof(tmp_path):
    usage_path = tmp_path / "usages.jsonl"
    outcome_path = tmp_path / "outcomes.jsonl"

    # Case 1: Empty files
    usage_path.write_text("", encoding="utf-8")
    outcome_path.write_text("", encoding="utf-8")
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "NO_GO"

    # Case 2: Executions exist but fallback used
    usage_path.write_text(json.dumps({
        "usage_id": "u1",
        "fallback_used": True,
        "execution_surface": "agent_runner"
    }) + "\n", encoding="utf-8")
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "NO_GO"

    # Case 3: Executions exist, non-fallback, but no outcome
    usage_path.write_text(json.dumps({
        "usage_id": "u2",
        "fallback_used": False,
        "execution_surface": "agent_runner"
    }) + "\n", encoding="utf-8")
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "NO_GO"

    # Case 4: Exclude dashboard surface
    usage_path.write_text(json.dumps({
        "usage_id": "u3",
        "fallback_used": False,
        "execution_surface": "dashboard"
    }) + "\n", encoding="utf-8")
    outcome_path.write_text(json.dumps({
        "usage_id": "u3",
        "status": "COMPLETED"
    }) + "\n", encoding="utf-8")
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "NO_GO"

    # Case 5: Valid proof!
    usage_path.write_text(json.dumps({
        "usage_id": "u4",
        "fallback_used": False,
        "execution_surface": "agent_runner",
        "timestamp": "2026-07-06T20:00:00Z",
        "champion_id": "c1"
    }) + "\n", encoding="utf-8")
    outcome_path.write_text(json.dumps({
        "usage_id": "u4",
        "status": "COMPLETED"
    }) + "\n", encoding="utf-8")
    res = validate_brain_runtime_proof([usage_path], [outcome_path])
    assert res["status"] == "LIVE"
    assert res["go_no_go"] == "GO"
    assert res["evidence"]["usage_id"] == "u4"
