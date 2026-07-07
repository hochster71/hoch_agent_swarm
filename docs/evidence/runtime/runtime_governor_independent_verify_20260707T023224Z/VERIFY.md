# Runtime Governor Independent Verification

## HEAD
4682453cb5593b5432355e34b0447ad9a5b1a75c
4682453 Add post-containment BRAIN truth endpoints

## Git status governor files
 M backend/brain/live_runtime_aggregator.py
?? backend/runtime_governor.py
?? docs/evidence/runtime/runtime_governor_advisory_20260706T205859Z/
?? scripts/runtime_governor_once.py
?? scripts/verify_runtime_governor.py
?? tests/test_runtime_governor.py

## Forbidden code scan
backend/runtime_governor.py:56:            "hoch_daemon.sh",
backend/runtime_governor.py:57:            "hoch_cadence.sh",
backend/runtime_governor.py:58:            "brain_cadence.sh",
backend/runtime_governor.py:59:            "recursive_optimizer",
backend/runtime_governor.py:60:            "phase56_burnin.py"
backend/runtime_governor.py:258:                "hoch200_sync_allowed": False,
scripts/verify_runtime_governor.py:23:        "hoch200_sync_allowed", "git_dirty_summary", "evidence_path"
scripts/verify_runtime_governor.py:36:    if data.get("hoch200_sync_allowed") is not False:
scripts/verify_runtime_governor.py:37:        print("ERROR: hoch200_sync_allowed is not False", file=sys.stderr)
tests/test_runtime_governor.py:72:    assert record["hoch200_sync_allowed"] is False
tests/test_runtime_governor.py:77:    # Mock a violating process (hoch_daemon.sh)
tests/test_runtime_governor.py:82:        "cmdline": ["bash", "scripts/hoch_daemon.sh"]

## Compile

## Tests
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/michaelhoch/hoch_agent_swarm
configfile: pyproject.toml
plugins: cov-7.1.0, anyio-4.14.1, hypothesis-6.156.1
collected 26 items

tests/test_live_runtime_truth_validator.py ......                        [ 23%]
tests/test_brain_truth_endpoints.py ...                                  [ 34%]
tests/test_factory_runtime_truth.py .                                    [ 38%]
tests/test_reasoning_graph.py .                                          [ 42%]
tests/test_no_fake_green_truth_endpoints.py .......                      [ 69%]
tests/test_runtime_governor.py ........                                  [100%]

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
======================= 26 passed, 77 warnings in 0.51s ========================

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

## Fresh advisory governor run
Initializing Runtime Governor in advisory mode...
Verdict: CONDITIONAL
Reasons:
  - Source authority is STALE and reasoning graph is CONDITIONAL.
Evidence written to: /Users/michaelhoch/hoch_agent_swarm/docs/evidence/runtime/runtime_governor_independent_verify_20260707T023224Z/governor_run/decision_record.json

## Governor verifier
[OK] Decision record JSON schema is fully compliant.
[OK] Governor codebase compliance verified (No launchctl, no illegal subprocesses).
SUCCESS: Runtime Governor verification PASSED.

## Decision record summary
{
  "verdict": "CONDITIONAL",
  "reasons": [
    "Source authority is STALE and reasoning graph is CONDITIONAL."
  ],
  "source_authority_status": "STALE",
  "reasoning_graph_status": "CONDITIONAL",
  "mutation_allowed": false,
  "human_approval_required": true,
  "hmf_hrf_paid_execution_allowed": false,
  "hoch200_sync_allowed": false
}
