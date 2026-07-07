# -*- coding: utf-8 -*-
"""
tests/test_factory_runtime_truth.py
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_factory_runtime_truth():
    resp = client.get("/api/brain/factory-runtime-truth")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "factories" in data
    assert "software" in data["factories"]
    assert "music" in data["factories"]
    assert "research" in data["factories"]
    assert data["factories"]["software"]["status"] in ["GO", "NO_GO", "UNKNOWN", "STALE"]
