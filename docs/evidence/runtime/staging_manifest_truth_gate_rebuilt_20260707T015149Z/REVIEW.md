# Rebuilt Truth Gate Staging Manifest Review

## Allowlist
backend/main.py
backend/brain/live_runtime_aggregator.py
backend/brain/runtime_truth_validator.py
tests/test_live_runtime_truth_validator.py
tests/test_brain_truth_endpoints.py
tests/test_factory_runtime_truth.py
tests/test_reasoning_graph.py
tests/test_no_fake_green_truth_endpoints.py
docs/evidence/runtime/post_containment_truth_endpoint_wiring.md
docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z
docs/evidence/runtime/source_authority_reasoning_graph_cleanup.md
docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z
docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z
has_live_project_tracker/data/brain_runtime_truth.json
has_live_project_tracker/data/factory_runtime_truth.json
has_live_project_tracker/data/reasoning_graph.json
has_live_project_tracker/data/source_authority_manifest.json

## Existence check
OK backend/main.py
OK backend/brain/live_runtime_aggregator.py
OK backend/brain/runtime_truth_validator.py
OK tests/test_live_runtime_truth_validator.py
OK tests/test_brain_truth_endpoints.py
OK tests/test_factory_runtime_truth.py
OK tests/test_reasoning_graph.py
OK tests/test_no_fake_green_truth_endpoints.py
OK docs/evidence/runtime/post_containment_truth_endpoint_wiring.md
OK docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z
OK docs/evidence/runtime/source_authority_reasoning_graph_cleanup.md
OK docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z
OK docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z
OK has_live_project_tracker/data/brain_runtime_truth.json
OK has_live_project_tracker/data/factory_runtime_truth.json
OK has_live_project_tracker/data/reasoning_graph.json
OK has_live_project_tracker/data/source_authority_manifest.json

## Git status for allowlist
 M backend/main.py
?? backend/brain/live_runtime_aggregator.py
?? backend/brain/runtime_truth_validator.py
?? tests/test_live_runtime_truth_validator.py
?? tests/test_brain_truth_endpoints.py
?? tests/test_factory_runtime_truth.py
?? tests/test_reasoning_graph.py
?? tests/test_no_fake_green_truth_endpoints.py
?? docs/evidence/runtime/post_containment_truth_endpoint_wiring.md
?? docs/evidence/runtime/launchd_bootout_containment_20260707T013449Z/
?? docs/evidence/runtime/source_authority_reasoning_graph_cleanup.md
?? docs/evidence/runtime/source_graph_independent_verify_20260707T013849Z/
?? docs/evidence/runtime/main_py_mount_anchor_repair_20260707T015018Z/
?? has_live_project_tracker/data/brain_runtime_truth.json
?? has_live_project_tracker/data/factory_runtime_truth.json
?? has_live_project_tracker/data/reasoning_graph.json
?? has_live_project_tracker/data/source_authority_manifest.json

## Diff stat for tracked allowlist files
 backend/main.py | 69 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 69 insertions(+)

## Critical verification
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

backend/main.py:5362
  /Users/michaelhoch/hoch_agent_swarm/backend/main.py:5362: DeprecationWarning: 
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
======================= 18 passed, 77 warnings in 5.73s ========================

## Containment
Containment CLEAN

## Endpoint smoke
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
