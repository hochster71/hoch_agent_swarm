# OMEGA R1 Remediation Campaign — 2026-07-17

**Separate from audit.** Audit package remains frozen at  
`audits/HELM_OMEGA_ASSURANCE_AUDIT_v1.0_20260717/`.  
This campaign remediates fixable findings only; founder-gated items are explicitly out of scope.

| Field | Value |
|---|---|
| Campaign ID | OMEGA_R1 |
| Date | 2026-07-17 |
| Branch | `helm/h1b-r2-remediation` |
| Doctrine | reproduce → root cause → fix → +/− tests → evidence → partial scorecard only |

---

## Scope

### In scope (code-fixable)

| Finding | Title | Status |
|---|---|---|
| R-02 / SEC-02 | CORS `allow_origins=["*"]` | **FIXED** |
| R-01 / SEC-01 | Read-auth not mounted | **FIXED (mounted; enable opt-in)** |
| R-18 | Non-atomic mission_state write | **FIXED** |
| R-06 | Mission truth missing on :8000 | **FIXED (routes added)** |
| R-03 / R-04 | Posture 100% / CM-3 fake clean | **FIXED (honesty + CM-3 dirty)** |
| R-05 | Factory registry READY overclaim | **FIXED (reconcile from products)** |
| R-13 | Stale sources `allowed_for_live_ui=true` | **FIXED** |
| GOV-03 | Voice sign/submit/revenue imprecise | **FIXED** |

### Out of scope (founder / external / not claimed fixed)

| Finding | Why not fixed this campaign |
|---|---|
| REQ-GOV-002 | Founder authorization binding |
| Apple TestFlight / ASC | Founder credentials |
| Settled revenue | External Stripe settlement |
| Full 24h soak citable PASS | Requires multi-hour controlled run |
| Production deploy / read-auth ENABLE | Founder env token cutover |
| Full CVE / load tests | Separate campaigns |

---

## Per-finding record

### 1. R-02 CORS wildcard

| Step | Detail |
|---|---|
| **Reproduce** | `backend/helm_live_api.py` and `backend/main.py` used `allow_origins=["*"]` |
| **Root cause** | Dev convenience left as production default |
| **Fix** | Explicit local-origin allowlists; override via `HELM_CORS_ORIGINS` |
| **Tests** | `test_helm_live_api_cors_not_wildcard`, `test_main_api_cors_not_wildcard` |
| **Evidence** | pytest OMEGA R1 17/17 |

### 2. R-01 Read-auth unmounted

| Step | Detail |
|---|---|
| **Reproduce** | NIST matrix PARTIAL: middleware staged, not in ASGI stack |
| **Root cause** | Deliberate non-cutover left stack without mount |
| **Fix** | Mount `ReadAuthMiddleware` with `HardenedConfig.from_env()`; default **disabled** so phone/soak keep working; enable via `HELM_READ_AUTH_ENABLED=1` + `HELM_READ_TOKEN` (founder) |
| **Tests** | mount present; disabled passthrough; enabled 401/200 |
| **Evidence** | nist assessor now PARTIAL “mounted but disabled” not “not mounted”; COVERED only when enabled+token |
| **Residual** | GETs still open until founder enables token |

### 3. R-18 Torn mission_state write

| Step | Detail |
|---|---|
| **Reproduce** | `OUT.write_text(...)` non-atomic under multi-writer |
| **Root cause** | Last-writer race + non-atomic replace |
| **Fix** | temp file + `os.fsync` + `os.replace` |
| **Tests** | `test_mission_state_write_atomic` |
| **Evidence** | unit pass |

### 4. R-06 Dual API surface

| Step | Detail |
|---|---|
| **Reproduce** | `:8000/api/mission/state` → 404; mission only on `:8770` |
| **Root cause** | Mission engine only registered on helm_live_api |
| **Fix** | `backend/mission_control/mission_api_router.py` included in `main.py` — same `write_mission_state()` |
| **Tests** | router schema test; main.py import present |
| **Evidence** | TestClient 200 + HELM_MISSION_STATE |
| **Residual** | Live LaunchAgent process must be restarted to serve new routes without TestClient |

### 5. R-03/R-04 Control posture honesty

| Step | Detail |
|---|---|
| **Reproduce** | `posture_percent: 100.0` on 13 controls; CM-3 claimed 0 uncommitted while tree dirty |
| **Root cause** | Sample percent read as full catalog; CM-3 ignored untracked + non-code dirty |
| **Fix** | `full_nist_800_53_coverage: false`, `posture_percent_scope: SAMPLED_CONTROLS_ONLY`, catalog note; CM-3 counts all code + any dirty tree |
| **Tests** | `test_posture_schema_denies_full_catalog_claim`, `test_cm03_fails_on_dirty_tree` |
| **Evidence** | Live conmon after: **84.6% (11/13)**; CM-3 GAP “36 uncommitted CODE files (306 dirty paths)”; open findings 2 |

### 6. R-05 Factory READY overclaim

| Step | Detail |
|---|---|
| **Reproduce** | HSF/HMF/HRF/HCF registry ACTIVE/READY vs board rung 1–3 |
| **Root cause** | Liveness producer re-stamped identity without operational readiness |
| **Fix** | Reconcile readiness from `products.json` rungs + on-disk source; update product `source_dir` for HFF/HMF/HRF |
| **Tests** | `test_factory_readiness_reconcile_no_fake_ready` |
| **Evidence** | After run: HSF NOT_READY; HMF/HRF/HCF/HFF DEGRADED; HASF READY (rung 4 + live_url); HHF/HPF NOT_READY |

### 7. R-13 Stale source authority UI allow

| Step | Detail |
|---|---|
| **Reproduce** | STALE sources with `allowed_for_live_ui: true` |
| **Root cause** | Validator always set allow true when path existed |
| **Fix** | Fail-closed: STALE/UNKNOWN/MALFORMED → `allowed_for_live_ui=false` |
| **Tests** | `test_stale_source_not_allowed_for_live_ui` |
| **Evidence** | Regenerated manifest: all three sources STALE, allow=false |

### 8. GOV-03 Voice doorstep verbs

| Step | Detail |
|---|---|
| **Reproduce** | “sign the release” → runtime_health READ_ONLY |
| **Root cause** | Missing DOORSTEP command patterns |
| **Fix** | `sign_release`, `submit_store`, `clear_apple_gate`, `mark_revenue` DOORSTEP commands |
| **Tests** | parametrized utterance tests |
| **Evidence** | resolve: sign/mark/submit/deploy → DOORSTEP |

---

## Test summary

```
tests/test_omega_r1_remediation.py  →  17 passed
(+ prior suites: security_hardening, mission_state, capability_gate remain green when run)
```

Artifacts under this directory:

- `pytest_omega_r1_final.txt`
- `conmon_after.txt`
- `liveness_producer.txt`
- `source_authority_regen.txt`
- `inprocess_api_checks.txt`
- `SCORECARD_DELTA.md`

---

## Scorecard delta (affected sections only)

See `SCORECARD_DELTA.md`. System-level verdict remains **NOT READY** (mission still BLOCKED_EXTERNAL; revenue $0 settled; Apple UNKNOWN; read-auth not enabled). Remediation improves specific domain scores without laundering the overall verdict.
