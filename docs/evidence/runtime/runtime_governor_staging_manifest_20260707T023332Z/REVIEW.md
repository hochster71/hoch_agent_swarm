# Runtime Governor Staging Manifest Review

## Allowlist
backend/runtime_governor.py
scripts/runtime_governor_once.py
scripts/verify_runtime_governor.py
tests/test_runtime_governor.py
backend/brain/live_runtime_aggregator.py
docs/evidence/runtime/runtime_governor_advisory_20260706T205859Z
docs/evidence/runtime/runtime_governor_independent_verify_20260707T023224Z/VERIFY.md
docs/evidence/runtime/runtime_governor_independent_verify_20260707T023224Z/governor_run/decision_record.json

## Existence check
OK backend/runtime_governor.py
OK scripts/runtime_governor_once.py
OK scripts/verify_runtime_governor.py
OK tests/test_runtime_governor.py
OK backend/brain/live_runtime_aggregator.py
OK docs/evidence/runtime/runtime_governor_advisory_20260706T205859Z
OK docs/evidence/runtime/runtime_governor_independent_verify_20260707T023224Z/VERIFY.md
OK docs/evidence/runtime/runtime_governor_independent_verify_20260707T023224Z/governor_run/decision_record.json

## Git status for allowlist
?? backend/runtime_governor.py
?? scripts/runtime_governor_once.py
?? scripts/verify_runtime_governor.py
?? tests/test_runtime_governor.py
 M backend/brain/live_runtime_aggregator.py
?? docs/evidence/runtime/runtime_governor_advisory_20260706T205859Z/
?? docs/evidence/runtime/runtime_governor_independent_verify_20260707T023224Z/VERIFY.md
?? docs/evidence/runtime/runtime_governor_independent_verify_20260707T023224Z/governor_run/decision_record.json

## Diff stat for tracked allowlist files
 backend/brain/live_runtime_aggregator.py | 13 +++++++++++--
 1 file changed, 11 insertions(+), 2 deletions(-)

## Verification
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
======================= 26 passed, 77 warnings in 0.50s ========================

## Containment
Containment CLEAN

## Governor decision record
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
