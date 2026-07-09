# HOCH NEURO — Derivation Semantics Verification

The offline derivation test suite for the neurovascular command center has been executed and verified.

## 1. Test Execution Command
```bash
node tests/test_hoch_neuro_derive.js
```

## 2. Results
- **Total Tests:** 23
- **Passed:** 23
- **Failed:** 0
- **Status:** **PASS**

## 3. Test Cases Verified
- `ok  FRESH lane => GO`
- `ok  WARNING lane => CONDITIONAL`
- `ok  STALE lane => STALE`
- `ok  EXPIRED lane => STALE`
- `ok  UNKNOWN lane => UNKNOWN`
- `ok  empty stale_status => UNKNOWN (not GO)`
- `ok  blocked_by present => BLOCKED even if FRESH`
- `ok  all-null payloads => no lane is GO`
- `ok  empty objects => factories UNKNOWN, never GO`
- `ok  fresh relay => BASILAR + MCA GO`
- `ok  epic fury WAITING_FOR_REVIEW => ACA CONDITIONAL (not GO)`
- `ok  fresh HRF => PCA GO`
- `ok  cycle number resolves to 742`
- `ok  founder_gated_execution reads human_approval_required=ON`
- `ok  provider_api_calls absent => UNKNOWN (never fabricated)`
- `ok  live provider_api_calls=OFF => OFF (post-relay-patch, truthful)`
- `ok  live founder flag overrides status fallback`
- `ok  core glows fresh when governed GO + relay live + fresh`
- `ok  stale telemetry => lanes stale, core NOT fresh`
- `ok  blocked HRF => PCA BLOCKED (clot)`
- `ok  blocked build (cycle.blocked>0) => MCA BLOCKED`
- `ok  HSF (no lane) declared-live => CONDITIONAL, never GO`
- `ok  evidence coverage = % of FRESH lanes`
