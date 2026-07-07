# -*- coding: utf-8 -*-
"""
tests/test_brain_truth_endpoints.py
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_brain_runtime_truth():
    resp = client.get("/api/brain/runtime-truth")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "go_no_go" in data
    assert "evidence" in data


def test_get_champion_runtime_usage():
    resp = client.get("/api/brain/champion-runtime-usage")
    assert resp.status_code == 200
    data = resp.json()
    assert "usages" in data
    assert isinstance(data["usages"], list)


def test_get_champion_outcome_feedback():
    resp = client.get("/api/brain/champion-outcome-feedback")
    assert resp.status_code == 200
    data = resp.json()
    assert "outcomes" in data
    assert isinstance(data["outcomes"], list)
