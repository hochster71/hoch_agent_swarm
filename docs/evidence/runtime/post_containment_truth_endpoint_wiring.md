# Post-Containment Truth Endpoint Wiring Evidence

This document provides verification and proof of wiring the missing live truth endpoints to the FastAPI backend following post-containment system auditing.

## 1. Verified Endpoint Mappings

The following table summarizes the HTTP response and verified status of the 7 wired endpoints under the **PRIME DIRECTIVE** (no fake-green):

| Endpoint Path | Status Code | Returned Status | Rationale / Evidence |
|---|---|---|---|
| `GET /api/pert/data` | 200 | `N/A` | Passes through raw PERT/CPM calculations from the calculations server at `:8765`. |
| `GET /api/brain/runtime-truth` | 200 | `LIVE` | The immutable usage ledger contains verified execution `usage_id: "c49c0bc24df30937"` with `fallback_used: false` on surface `agent_runner` linked to a successful `COMPLETED` outcome in the feedback ledger. |
| `GET /api/brain/factory-runtime-truth` | 200 | `GO` | Dynamically tracks and compiles convergence states from HASF, HMF, and HRF. |
| `GET /api/brain/reasoning-graph` | 200 | `NO_GO` | Mapped reasoning pathway network. Marked `NO_GO` due to source authority staleness. |
| `GET /api/brain/source-authority` | 200 | `STALE` | Correctly detects that the local census/O*NET source manifest file age exceeds 30 minutes. |
| `GET /api/brain/champion-runtime-usage` | 200 | `N/A` | Dynamically serves the list of recorded operating prompt resolutions. |
| `GET /api/brain/champion-outcome-feedback` | 200 | `N/A` | Dynamically serves the linked execution outcomes. |

## 2. Test Verification

All 5 required tests passed successfully:
- `tests/test_live_runtime_truth_validator.py`
- `tests/test_brain_truth_endpoints.py`
- `tests/test_factory_runtime_truth.py`
- `tests/test_reasoning_graph.py`
- `tests/test_no_fake_green_truth_endpoints.py`

### Test Exec Log:
```text
tests/test_live_runtime_truth_validator.py ......                        [ 40%]
tests/test_brain_truth_endpoints.py ...                                  [ 60%]
tests/test_factory_runtime_truth.py .                                    [ 66%]
tests/test_reasoning_graph.py .                                          [ 73%]
tests/test_no_fake_green_truth_endpoints.py ....                         [100%]

======================= 15 passed, 77 warnings in 10.27s =======================
```

## 3. Dynamic Compilation
The aggregator dynamically writes compiled state files to the live project tracker directory on every request:
- `has_live_project_tracker/data/source_authority_manifest.json`
- `has_live_project_tracker/data/brain_runtime_truth.json`
- `has_live_project_tracker/data/factory_runtime_truth.json`
- `has_live_project_tracker/data/reasoning_graph.json`
