# Source Authority + Reasoning Graph Independent Verification

## Containment check
Containment CLEAN

## Endpoint status
/health 200
/api/mission/brief 200
/api/v1/relay/health 200
/api/v1/relay/status 200
/api/v1/relay/registry 200
/api/agent-router/ledger 200
/api/pert/data 200
/api/brain/runtime-truth 200
/api/brain/factory-runtime-truth 200
/api/brain/reasoning-graph 200
/api/brain/source-authority 200
/api/brain/champion-runtime-usage 200
/api/brain/champion-outcome-feedback 200

## Source authority summary
{
  "status": "STALE",
  "source_count": 3,
  "sources": [
    {
      "key": "naics_2022",
      "status": "STALE",
      "freshness": "stale",
      "allowed_for_live_ui": true,
      "has_checksum": true,
      "validation_method": "SHA256 checksum matching"
    },
    {
      "key": "onet_28",
      "status": "STALE",
      "freshness": "stale",
      "allowed_for_live_ui": true,
      "has_checksum": true,
      "validation_method": "SHA256 checksum matching"
    },
    {
      "key": "bls_oews_24",
      "status": "STALE",
      "freshness": "stale",
      "allowed_for_live_ui": true,
      "has_checksum": true,
      "validation_method": "SHA256 checksum matching"
    }
  ]
}

## Reasoning graph summary
{
  "status": "CONDITIONAL",
  "node_count": 8,
  "edge_count": 5,
  "source_nodes": [
    {
      "id": "source-naics",
      "status": "STALE",
      "source_authority_ref": "naics_2022"
    },
    {
      "id": "source-onet",
      "status": "STALE",
      "source_authority_ref": "onet_28"
    },
    {
      "id": "source-bls",
      "status": "STALE",
      "source_authority_ref": "bls_oews_24"
    }
  ]
}

## BRAIN runtime truth
{
  "status": "LIVE",
  "go_no_go": "GO",
  "evidence": {
    "has_real_execution": true,
    "fallback_used": false,
    "execution_surface": "agent_runner",
    "usage_id": "c49c0bc24df30937",
    "outcome_linked": true,
    "outcome_status": "COMPLETED",
    "timestamp": "2026-07-06T22:50:47.667898Z",
    "champion_id": "gen-gen-gapfill-caa718343c-20260706T005131-20260706T220723"
  }
}

## Targeted tests
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/michaelhoch/hoch_agent_swarm
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.14.1, hypothesis-6.156.1
collected 18 items

tests/test_live_runtime_truth_validator.py ......                        [ 33%]
tests/test_brain_truth_endpoints.py ...                                  [ 50%]
tests/test_factory_runtime_truth.py .                                    [ 55%]
tests/test_reasoning_graph.py .                                          [ 61%]
tests/test_no_fake_green_truth_endpoints.py .......                      [100%]

=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/fastapi/testclient.py:1
  /Users/michaelhoch/hoch_agent_swarm/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

backend/main.py:5434
  /Users/michaelhoch/hoch_agent_swarm/backend/main.py:5434: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

.venv/lib/python3.13/site-packages/fastapi/applications.py:4675
  /Users/michaelhoch/hoch_agent_swarm/.venv/lib/python3.13/site-packages/fastapi/applications.py:4675: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)  # ty: ignore[deprecated]

backend/brain/doctrine_memory.py:53: 59 warnings
  /Users/michaelhoch/hoch_agent_swarm/backend/brain/doctrine_memory.py:53: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    """, (rule_id, rule_text, datetime.utcnow().isoformat() + "Z"))

backend/brain/doctrine_memory.py:67: 15 warnings
  /Users/michaelhoch/hoch_agent_swarm/backend/brain/doctrine_memory.py:67: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    """, (rule_id, r, datetime.utcnow().isoformat() + "Z"))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 18 passed, 77 warnings in 0.48s ========================
