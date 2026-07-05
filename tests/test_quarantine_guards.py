import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app, follow_redirects=False)

def test_quarantine_isolation():
    # Set feature flag on
    os.environ["HAS_QUARANTINE_MODE"] = "true"
    os.environ["HAS_MODE"] = "development"
    
    # 1. Non-HAS endpoint should be blocked (403)
    resp = client.get("/api/tv/health")
    assert resp.status_code == 403
    assert resp.json() == {"detail": "Route is quarantined in HAS-only mode."}
    
    resp = client.get("/api/v1/app-store/listing")
    assert resp.status_code == 403
    assert resp.json() == {"detail": "Route is quarantined in HAS-only mode."}
    
    # 2. HAS/core endpoint should be allowed (200)
    resp = client.get("/health")
    assert resp.status_code == 200

def test_quarantine_disabled():
    # Set feature flag off
    os.environ["HAS_QUARANTINE_MODE"] = "false"
    os.environ["HAS_MODE"] = "development"
    
    resp = client.get("/api/tv/health")
    assert resp.status_code == 200

def test_mock_llm_production_blocked():
    os.environ["HAS_QUARANTINE_MODE"] = "false"
    os.environ["HAS_MODE"] = "production"
    
    resp = client.get("/api/v1/mock/llm/v1/models")
    assert resp.status_code == 403
    assert resp.json() == {"detail": "Mock LLM endpoints are disabled in production mode."}

def test_mock_llm_development_allowed():
    os.environ["HAS_QUARANTINE_MODE"] = "false"
    os.environ["HAS_MODE"] = "development"
    
    resp = client.get("/api/v1/mock/llm/v1/models")
    assert resp.status_code == 200

def test_legacy_path_redirect():
    os.environ["HAS_QUARANTINE_MODE"] = "false"
    os.environ["HAS_MODE"] = "development"
    
    resp = client.get("/api/app-store/listing")
    assert resp.status_code == 307
    assert resp.headers["location"] == "/api/v1/app-store/listing"

def test_core_contract_schemas():
    os.environ["HAS_QUARANTINE_MODE"] = "false"
    os.environ["HAS_MODE"] = "development"
    
    core_paths = [
        "/health",
        "/api/v1/relay/health",
        "/api/v1/readiness/status"
    ]
    
    required_keys = {
        "data", "source", "source_id", "observed_at", 
        "received_at", "ttl_ms", "freshness", "correlation_id", "evidence_refs"
    }
    
    for path in core_paths:
        resp = client.get(path)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, dict)
        for key in required_keys:
            assert key in body, f"Key '{key}' missing in path '{path}' response: {body}"

