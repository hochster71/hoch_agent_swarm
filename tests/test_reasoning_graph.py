# -*- coding: utf-8 -*-
"""
tests/test_reasoning_graph.py
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_reasoning_graph():
    resp = client.get("/api/brain/reasoning-graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert len(data["nodes"]) > 0
