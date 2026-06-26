# HOCH Agent Swarm — QA Test Strategy
**Author:** QA Test Strategy Architect  
**Date:** 2026-06-26  
**Version:** 1.0  
**Scope:** Major app at `/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm`  
**Release target:** `0.1.6-ERROR-BUDGET-AWARE-AUTONOMY` (blocked)  
**Basis:** Audit findings from 2026-06-26 read-only QA scan  

---

> [!IMPORTANT]
> This strategy assumes production-grade standards. All release-blocking risks are documented.
> No undocumented risk is acceptable at the release gate.

---

## 1. Product Context

| Item | Value |
|---|---|
| App | HOCH Agent Swarm — enterprise agentic AI command center |
| Frontend | Vanilla JS + Vite (port 3000) — 11 nav pages |
| Backend | FastAPI + SQLite (port 8000) — 132 API endpoints |
| Agent engine | Ollama (local LLM) + premium fallback templates |
| Governance | DoD ZTA + CDAO RAI aligned |
| Release chain | CrewAI harness → ingestion bridge → FastAPI backend → Release Provenance UI |
| Current gate | BLOCKED: `dirty_working_tree`, `STALE_TAG`, `policy_status: BLOCK` |

---

## 2. Critical User Journeys (CUJs)

| # | Journey | Pages Touched | Current Status |
|---|---|---|---|
| **CUJ-01** | Submit a task → agent executes → artifact produced | Swarm Control, HOCHSTER Runtime | ⚠️ PARTIAL — execution works, agent stays "idle" |
| **CUJ-02** | View live mesh topology → click node → inspect tasks | HOCHSTER Runtime | ⚠️ PARTIAL — topology renders, node data is synthetic |
| **CUJ-03** | Review readiness gate → confirm all SLOs green → approve | Readiness Autopilot, Error Budget | ✅ LIVE — freshness-tagged data |
| **CUJ-04** | Trigger security audit → view control posture → initiate remediation | Cybersecurity Factory, Remediation Safety | ⚠️ PARTIAL — control results semi-static |
| **CUJ-05** | Browse candidate packets → approve formal preview → generate attestation | Release Provenance | ✅ LIVE — deep pipeline working |
| **CUJ-06** | Review pending approval gates → decide approve/deny | Governance Cockpit | ✅ LIVE — 71 real pending gates |
| **CUJ-07** | Replay timeline event → trace to originating agent and task | Timeline Replay | ✅ LIVE — 6996 ledger blocks |
| **CUJ-08** | Ingest CrewAI artifacts → view in release provenance context | Release Provenance | ❌ BROKEN — ingest works, UI does not surface it |
| **CUJ-09** | Detect new network device → approve for service → register | HOCHSTER Runtime, device discovery | ⚠️ PARTIAL — 37 real ARP devices; approval flow exists |
| **CUJ-10** | Mission Intel: receive anomaly insight → route to agent for resolution | Mission Intel | ❌ BROKEN — 1 static fixture, no live intelligence |

---

## 3. Quality Attributes

| Attribute | Current Level | Target |
|---|---|---|
| **Data Honesty** | 40% real | ≥ 90% real or labeled |
| **Availability** | 100% (manual start) | 100% with health check |
| **Correctness** | High | ≥ 95% verified by contract tests |
| **Auditability** | 6996 blocks, partial coverage | 100% of state-changing actions |
| **Release Integrity** | Gating is CORRECT | Maintain |
| **Agent Truthfulness** | 0% (all idle) | ≥ 80% accurate on last known state |
| **Asset Truthfulness** | ~15% | ≥ 70% |
| **Performance** | Unknown | < 200ms p95 |
| **Security** | Open CORS (`*`) | Operator auth on POST/DELETE |
| **Stability** | Unknown | DB state survives restart cleanly |

---

## 4. Test Levels

### Level 1 — Unit Tests (Backend Python)

**Framework:** pytest  
**Coverage target:** ≥ 80% line coverage on business logic modules  
**Owner:** Backend Platform Agent  
**Status: ❌ Missing — no pytest suite exists in the major repo**

Priority modules to cover:

| Module | Key Functions |
|---|---|
| `backend/runtime_execution_store.py` | persist/list functions, state transitions |
| `backend/ledger_manager.py` | hash chain integrity, block creation |
| `backend/security_auditor.py` | control evaluation logic |
| `backend/crewai_ingestion_bridge.py` | file scan, SHA-256 hash, metadata parse |
| `backend/readiness_daemon.py` | SLO computation, burn rate |
| `backend/remediation_safety.py` | guardrail checks |
| `backend/capability_router.py` | routing decision logic |

**Gate:** All Level 1 tests pass with 0 failures before Level 2 proceeds.

---

### Level 2 — API Contract Tests (TypeScript / Playwright)

**Framework:** Playwright API testing + `scripts/qa/*.ts`  
**Coverage target:** 100% of 132 endpoints  
**Owner:** QA automation  

**Existing coverage — 38 scripts ✅**

Key existing scripts:
- `test-backend-runtime-api-contract.ts` — core API shape
- `test-runtime-ledger-db-contract.ts` — ledger integrity
- `test-operator-governance-cockpit.ts` — governance
- `test-candidate-release-packet-contract.ts` — RC packets
- `test-crewai-ingestion-bridge-contract.ts` — ingestion bridge
- `test-agent-capability-enforcement-contract.ts` — capability enforcement
- `test-evidence-graph.ts` — evidence graph
- `test-runtime-event-schema-contract.ts` — WebSocket schema

**Missing contract tests (6 required for Gate 3):**

| New Script | Tests | Priority |
|---|---|---|
| `test-agent-state-contract.ts` | Agents return valid state schema; can reach non-idle state | HIGH |
| `test-run-state-machine-contract.ts` | Runs can reach "completed"; no permanent "running" | HIGH |
| `test-intel-insights-contract.ts` | Insights are non-empty, non-stale (< 24h) | HIGH |
| `test-crewai-release-provenance-contract.ts` | Ingested artifacts visible in release UI response | HIGH |
| `test-asset-discovery-contract.ts` | Discovered devices count > 0; `active_assets` ≥ 1 | MEDIUM |
| `test-freshness-tag-contract.ts` | All freshness-tagged endpoints have `observed_at` within TTL | MEDIUM |

---

### Level 3 — End-to-End Tests (Playwright)

**Framework:** Playwright v1.61.1  
**Coverage target:** All 10 CUJs have ≥ 1 E2E spec  
**Owner:** QA automation  

**Existing E2E specs — 19 specs ✅**

Mapped to CUJs:
- CUJ-02: `antigravity-runtime.spec.ts`, `topology-agent-overlay.spec.ts` ✅
- CUJ-04: `cybersecurity-factory.spec.ts` ✅
- CUJ-05: `candidate-release-packet.spec.ts`, `formal-release-*.spec.ts`, `release-seal-attestation-bundle.spec.ts` ✅
- CUJ-06: `operator-governance-cockpit.spec.ts`, `release-channel-governance.spec.ts` ✅
- CUJ-07: `evidence-graph.spec.ts`, `release-evidence-*.spec.ts` ✅
- Security: `dast-unsigned-ui-negative.spec.ts` ✅
- Capability: `capability-enforcement.spec.ts` ✅

**Missing E2E specs (5 required for Gate 4):**

| New Spec | CUJ | Priority |
|---|---|---|
| `task-submit-and-complete.spec.ts` | CUJ-01 | BLOCKER |
| `agent-state-transition.spec.ts` | CUJ-01 | BLOCKER |
| `mission-intel-live.spec.ts` | CUJ-10 | HIGH |
| `crewai-artifacts-in-release-provenance.spec.ts` | CUJ-08 | HIGH |
| `device-discovery-to-approval.spec.ts` | CUJ-09 | MEDIUM |

---

### Level 4 — Manual Exploratory Testing

**Owner:** Operator (Michael Hoch)

| Area | What to Test | Acceptance |
|---|---|---|
| Mesh topology visual | Node positions, animation, click-to-inspect | Correct node data on click |
| Launch Swarm button | Real prompt → task routing → ledger entry | Ledger entry created |
| Approval gate UX | Approve/deny gate; verify ledger update | Decision recorded in governance summary |
| WebSocket resilience | Kill backend; reconnect frontend | No data loss; reconnects cleanly |
| Real device telemetry | L1 psutil values match `htop` on machine | Within 5% |
| Ollama routing | Start Ollama; run task; verify non-fallback response | `inference_runs` row with real model response |
| Timeline replay scrub | Scrub to timestamp; verify state matches ledger | State consistent with ledger at that timestamp |

---

## 5. Nonfunctional Test Needs

### Performance Targets

| Endpoint | Target | Method |
|---|---|---|
| All GET endpoints | p95 < 200ms at 100 concurrent | k6 |
| SQLite write throughput | 100 writes/sec no lock contention | k6 benchmark |
| WebSocket broadcast | < 500ms lag at 10 clients | Playwright multi-page |
| Frontend bundle | < 2s first contentful paint | Lighthouse |

### Security Checks

| Check | Gate |
|---|---|
| CORS locked to `localhost` in non-dev mode | Must not be `["*"]` in deployment |
| No secrets in API response bodies | 0 secret-pattern matches |
| DAST unsigned UI rejection | `dast-unsigned-ui-negative.spec.ts` PASS |
| POST/DELETE require operator context | 100% |
| Capability enforcement active | Contract test PASS |

### Resilience Scenarios

| Scenario | Expected |
|---|---|
| Backend restart | DB state preserved; in-memory state rebuilds |
| Ollama unavailable | Fallback runs; no crash |
| SQLite concurrent writes | No corruption; queue or 503 |
| Network scan fails | 0 results gracefully; no 500 |
| WebSocket client drops | Server cleans up without crash |

### Accessibility

| Check | Target |
|---|---|
| Keyboard nav through all 11 pages | All reachable without mouse |
| Screen reader labels | 0 critical aXe violations |
| Dark theme contrast | ≥ 4.5:1 ratio |

---

## 6. Automation Stack

| Layer | Tool | Status |
|---|---|---|
| API contract tests | Playwright API (`npx tsx`) | ✅ 38 scripts exist |
| E2E browser tests | Playwright v1.61.1 | ✅ 19 specs exist |
| Backend unit tests | **pytest** | ❌ Missing |
| Performance | **k6** | ❌ Missing |
| Static analysis | tsc + ESLint | ✅ |
| CSS compliance | `test-no-tailwind-cdn.ts` | ✅ |
| CI orchestration | `scripts/qa/run-ci-pipeline.py` | ✅ |
| Coverage | pytest-cov | ❌ Missing |
| Accessibility | @axe-core/playwright | ❌ Missing |

**Stack additions required:**
```bash
uv add --dev pytest pytest-cov pytest-asyncio httpx
brew install k6
npm install --save-dev @axe-core/playwright
```

---

## 7. Traceability Matrix

| Requirement | Test | Gap |
|---|---|---|
| Agents execute tasks | CUJ-01 E2E | ❌ Spec missing |
| Agent state changes on task | Unit + E2E | ❌ Both missing |
| Assets reflect real network | Contract test | ❌ Missing |
| All 132 API endpoints correct schema | 38 of 132 contracted | ⚠️ 94 gaps |
| Ledger hash chain integrity | `test-runtime-ledger-db-contract.ts` | ✅ |
| Approval gates enforce policy | `test-agent-capability-enforcement-contract.ts` | ✅ |
| RC cannot be packaged without gate | CrewAI harness gate tests | ✅ |
| CrewAI artifacts visible in provenance UI | Contract test | ❌ Missing |
| DoD ZTA controls evaluated live | Unit test | ❌ Missing |
| WebSocket broadcasts correct schema | `test-runtime-event-schema-contract.ts` | ✅ |
| Mission Intel produces live insights | Contract + E2E | ❌ Both missing |
| Per-page freshness badge | N/A — feature not built | ❌ Feature + test missing |
| Backend restart preserves state | Resilience test | ❌ Missing |
| CORS locked in production mode | Security test | ❌ Missing |

**10 requirements have zero test coverage.**

---

## 8. Evidence Artifacts Required at Release Gate

| Artifact | Source | Required |
|---|---|---|
| pytest report (0 failures) | `pytest --json-report` | ✅ REQUIRED |
| Playwright E2E HTML report | `npx playwright test --reporter=html` | ✅ REQUIRED |
| API contract test reports (all) | `npm run qa:ui-contract` | ✅ REQUIRED |
| pytest coverage ≥ 80% | pytest-cov LCOV | ✅ REQUIRED |
| QA scorecard | `artifacts/qa/app_audit/qa_scorecard.md` | ✅ REQUIRED |
| Per-page screenshots (11) | Playwright capture | ✅ REQUIRED |
| Security audit JSON | `/api/security/audit` | ✅ REQUIRED |
| Governance summary JSON | `/api/v1/governance/summary` | ✅ REQUIRED |
| CrewAI quality gate report | `quality_gate_report.json` | ✅ REQUIRED |
| Ledger verification proof | `/api/ledger/verify` | ✅ REQUIRED |
| Release candidate manifest | `release_candidate.json` | ✅ REQUIRED |
| Attestation bundle | DB: `release_seal_attestation_bundles` | ✅ REQUIRED |
| DAST report | E2E spec result | ✅ REQUIRED |
| Performance baseline | k6 summary | REQUIRED before 1.0 |
| Accessibility audit | Lighthouse + axe | REQUIRED before 1.0 |

---

## 9. Exit Criteria — 7 Sequential Release Gates

### Gate 1 — Code Quality
| Check | Tool | Pass Condition |
|---|---|---|
| No TypeScript compile errors | `tsc --noEmit` | Exit 0 |
| No CDN Tailwind | `test-no-tailwind-cdn.ts` | PASS |
| No Python import errors | `python3 -c "from backend.main import app"` | Exit 0 |
| Git working tree clean | `git status --short` | Empty output |

### Gate 2 — Unit Tests
| Check | Pass Condition |
|---|---|
| pytest exit 0 | 0 failures, 0 errors |
| Line coverage ≥ 80% (business logic) | pytest-cov report |
| No flaky tests | Same result × 3 consecutive runs |

### Gate 3 — API Contract
| Check | Pass Condition |
|---|---|
| All 38 existing contract scripts pass | `npm run qa:ui-contract` exit 0 |
| 6 new required contracts pass | See §4 Level 2 gaps |
| Freshness tag contract passes | `test-freshness-tag-contract.ts` PASS |
| Agent state contract passes | `test-agent-state-contract.ts` PASS |

### Gate 4 — E2E
| Check | Pass Condition |
|---|---|
| `npm run qa:e2e-runtime` exits 0 | All existing E2E pass |
| CUJ-01 spec passes | Task submits, runs, artifact produced |
| CUJ-08 spec passes | CrewAI artifacts visible in Release Provenance |
| CUJ-10 spec passes | Intel insights show non-static data |
| No visual regression | Screenshots match baseline |

### Gate 5 — Data Integrity
| Check | Pass Condition |
|---|---|
| 0 zombie runs (status="running" age > 24h) | DB query |
| `active_assets` derived from `discovered_devices` | API probe |
| Intel insights `timestamp` within 24h | API probe |
| No hardcoded seed entries in audit trail | Grep check |
| `total_agents` matches agent list length | API comparison |

### Gate 6 — Security
| Check | Pass Condition |
|---|---|
| DAST unsigned UI rejected | `dast-unsigned-ui-negative.spec.ts` PASS |
| Capability enforcement | `test-agent-capability-enforcement-contract.ts` PASS |
| No secrets in response bodies | Automated scan: 0 hits |
| Compliance score ≥ 70% | `/api/security/audit` |

### Gate 7 — Governance / Release
| Check | Pass Condition |
|---|---|
| `policy_status: ALLOW` | Governance summary |
| `formal_release_blockers: []` | No blockers |
| `tag_alignment_status: ALIGNED` | Git tag = package.json version |
| Git working tree clean | `git status --short` empty |
| CrewAI quality gate verdict: PASS | `quality_gate_report.json` |
| Attestation bundle present | DB count > 0 |
| All required evidence artifacts present | Manifest check |

> [!CAUTION]
> **Gates are sequential and non-negotiable.** Gate 7 cannot be entered unless Gates 1–6 all pass with zero failures. A single gate failure blocks the release.

---

## 10. Owner Roles

| Role | Responsible For |
|---|---|
| **Operator (Michael Hoch)** | Gate 7 final approval; manual exploratory; governance decisions |
| **QA Automation** | Gates 1–6; maintaining test scripts; writing missing specs |
| **Backend Platform Agent** | Unit test authorship; backend contract correctness |
| **Frontend Swarm UI Agent** | Per-page LIVE/STALE/MOCK badge; screenshot regression baseline |
| **Capt. Guardrail** | Policy enforcement tests; capability manifest correctness |
| **Prof. Ledger** | Ledger integrity tests; audit trail cleanliness |
| **Ms. Checkmark** | E2E CUJ coverage; contract test completeness |

---

## 11. Release-Blocking Risks

| # | Risk | Current State | Mitigation |
|---|---|---|---|
| RB-01 | Agent state machine absent | All agents idle permanently | Implement minimal state update in AgentRunner |
| RB-02 | 192 zombie runs | Corrupt Swarm Control | Run reaper on startup |
| RB-03 | CORS open (`*`) | Security risk on non-local deploy | Lock to `localhost` origin |
| RB-04 | Intel insights static | Misleading MI page | Bind to run history or Ollama |
| RB-05 | CrewAI RC not in UI | Cross-repo evidence gap | Wire ingestion bridge to provenance panel |
| RB-06 | Dirty working tree | Blocks formal release | Commit or stash before gate run |
| RB-07 | STALE_TAG | Blocks tag alignment | Create matching git tag |
| RB-08 | No pytest suite | Gate 2 cannot pass | Write unit tests (Sprint 5) |
| RB-09 | Security compliance 60% | Below 70% Gate 6 threshold | Fix AU-12 and CM-7 controls |
| RB-10 | Evidence graph sparse | 12 links for 181 packets | Auto-generate on packet creation |

---

## 12. Repair + Test Sequence (6 Sprints)

```
Sprint 1 — Data Integrity (1 day)
  Fix  A1  Zombie run reaper
  Fix  A2  active_assets from live discovery
  Fix  B1  Remove audit trail seed entries
  Fix  B2  Clear task_history.json
  Fix  C1  total_agents = 14 (real count)
  Fix  C2  confidence = integer type
  Test     npm run qa:ui-contract → still PASS

Sprint 2 — Agent Reality (1 day)
  Fix  A3  Agent state machine (idle → working → complete)
  New      test-agent-state-contract.ts
  New      task-submit-and-complete.spec.ts
  New      agent-state-transition.spec.ts
  Gate     CUJ-01 E2E must PASS

Sprint 3 — Data Honesty (1 day)
  Fix  A5  Remove synthetic CPU/RAM or clearly label
  Fix  A4  Intel insights from run history
  New      test-intel-insights-contract.ts
  New      mission-intel-live.spec.ts
  New      test-freshness-tag-contract.ts
  Gate     CUJ-10 E2E must PASS

Sprint 4 — Cross-Repo Integration (1 day)
  Fix  A6  CrewAI artifacts panel in Release Provenance
  New      test-crewai-release-provenance-contract.ts
  New      crewai-artifacts-in-release-provenance.spec.ts
  Gate     CUJ-08 E2E must PASS

Sprint 5 — Test Foundation (1 day)
  New      pytest unit test suite (≥ 80% coverage)
  New      k6 performance baseline
  New      axe accessibility baseline
  Fix  B3  Real security control evaluations (→ ≥ 70%)
  Fix  B4  Auto evidence graph links on packet creation
  Gate     All 7 gates pass in sequence

Sprint 6 — Release
  Clean git working tree
  Create git tag = package.json version
  npm run qa:runtime-full (full gate run)
  uv run package_release_candidate (CrewAI harness)
  Generate attestation bundle
  Operator Gate 7 approval
  Release
```

---

## 13. Missing Test Files — Complete List

| File to Create | Type | Gate | Priority |
|---|---|---|---|
| `tests/unit/test_runtime_execution_store.py` | pytest | Gate 2 | HIGH |
| `tests/unit/test_ledger_manager.py` | pytest | Gate 2 | HIGH |
| `tests/unit/test_security_auditor.py` | pytest | Gate 2 | HIGH |
| `tests/unit/test_crewai_bridge.py` | pytest | Gate 2 | HIGH |
| `tests/unit/test_readiness_daemon.py` | pytest | Gate 2 | MEDIUM |
| `tests/unit/test_agent_runner.py` | pytest | Gate 2 | MEDIUM |
| `scripts/qa/test-agent-state-contract.ts` | Playwright API | Gate 3 | HIGH |
| `scripts/qa/test-run-state-machine-contract.ts` | Playwright API | Gate 3 | HIGH |
| `scripts/qa/test-intel-insights-contract.ts` | Playwright API | Gate 3 | HIGH |
| `scripts/qa/test-crewai-release-provenance-contract.ts` | Playwright API | Gate 3 | HIGH |
| `scripts/qa/test-asset-discovery-contract.ts` | Playwright API | Gate 3 | MEDIUM |
| `scripts/qa/test-freshness-tag-contract.ts` | Playwright API | Gate 3 | MEDIUM |
| `tests/e2e/task-submit-and-complete.spec.ts` | Playwright E2E | Gate 4 | BLOCKER |
| `tests/e2e/agent-state-transition.spec.ts` | Playwright E2E | Gate 4 | BLOCKER |
| `tests/e2e/mission-intel-live.spec.ts` | Playwright E2E | Gate 4 | HIGH |
| `tests/e2e/crewai-artifacts-in-release-provenance.spec.ts` | Playwright E2E | Gate 4 | HIGH |
| `tests/e2e/device-discovery-to-approval.spec.ts` | Playwright E2E | Gate 4 | MEDIUM |
| `scripts/perf/load_test.js` | k6 | Gate 5 | MEDIUM |
| `scripts/qa/test-accessibility.ts` | Playwright + axe | Gate 6 | MEDIUM |
| `tests/resilience/test_restart_recovery.py` | pytest + httpx | Gate 5 | MEDIUM |

**18 new test files required for a clean production release.**

---

## Addendum: Prompt Library Governance (2026-06-26)

### REQ-PROMPT-01 — Prompt Library Governance

> Agents may access `michaelhoch/hoch_agent_swarm_prompt_library` only through a read-only, hash-tracked, risk-classified prompt library adapter. High-risk prompts require human approval. Prompt use must be logged with prompt path, hash, category, agent, mission, and timestamp.

**Authority:** HOCH QA Test Strategy Architect  
**Evidence base:** `artifacts/qa/app_audit/prompt_library_review.md`  
**Policy status:** ACTIVE — no automatic execution permitted until PL-01 through PL-05 are complete

#### Library Facts

| Metric | Value |
|---|---|
| Total prompts | 103 |
| Risk: LOW | 83 |
| Risk: MEDIUM | 7 |
| Risk: HIGH (approval required) | 13 |
| Risk: BLOCKED (hard) | 0 |
| Source files hashed | 5 |
| False positives in initial grep scan | 4 (DAN as substring) |
| Actual jailbreak instructions found | 0 |

#### New Tests Required (6)

| File | Type | Gate | Priority |
|---|---|---|---|
| `tests/unit/test_prompt_library_inventory.py` | pytest | Gate 2 | HIGH |
| `tests/unit/test_prompt_library_hashes.py` | pytest | Gate 2 | HIGH |
| `tests/unit/test_prompt_library_classification.py` | pytest | Gate 2 | HIGH |
| `scripts/qa/test-prompt-library-governance-contract.ts` | Playwright API | Gate 3 | HIGH |
| `tests/unit/test_prompt_approval_policy.py` | pytest | Gate 2 | HIGH |
| `tests/e2e/prompt-approval-workflow.spec.ts` | Playwright E2E | Gate 4 | HIGH |

#### Test Requirements

**`test_prompt_library_inventory.py`**
- All 103 prompts load from `backend/prompt_library.json`
- All required fields present: `id`, `category`, `industry`, `title`, `mission`, `outputs`, `prompt`
- No duplicate IDs

**`test_prompt_library_hashes.py`**
- SHA-256 of `backend/prompt_library.json` matches recorded provenance hash
- Per-prompt hash stable across restarts
- Hash mismatch on modified file raises integrity error

**`test_prompt_library_classification.py`**
- All 103 prompts receive a risk classification
- 13 HIGH-risk prompts correctly identified (by ID)
- 7 MEDIUM-risk prompts correctly identified
- 83 LOW-risk prompts correctly identified
- Word-boundary analysis applied (not substring grep)

**`test-prompt-library-governance-contract.ts`**
- `GET /api/v1/prompt-library` returns `count: 103`
- `GET /api/v1/prompt-library/categories` returns 20 categories, 16 industries
- `GET /api/v1/prompt-library/AIRT-016` returns `risk_level: HIGH` (after PL-01)
- `POST /api/v1/prompts/select` with HIGH-risk prompt returns status `PENDING_APPROVAL`
- `POST /api/v1/prompts/select` with LOW-risk prompt returns status `ALLOWED`

**`test_prompt_approval_policy.py`**
- LOW-risk prompt execution → `ALLOWED` without approval
- MEDIUM-risk prompt execution → `ALLOWED` + rationale logged
- HIGH-risk prompt execution → `PENDING_APPROVAL` without prior operator approval
- HIGH-risk prompt with approval → `ALLOWED` + ledger entry created
- BLOCKED prompt → `REJECTED` + alert generated

**`prompt-approval-workflow.spec.ts`**
- Navigate to Governance Cockpit
- HIGH-risk prompt request appears in approval queue
- Operator approves → status transitions to APPROVED
- Approved prompt visible in usage ledger
- Denied prompt logged as DENIED in ledger

#### Updated Missing Test File Count

**Original:** 18 new test files  
**Addendum adds:** 6 new test files  
**Total:** **24 new test files required for a clean production release.**

#### Gate Impact

| Gate | New Check |
|---|---|
| Gate 2 — Unit Tests | 5 new prompt library pytest modules |
| Gate 3 — API Contract | `test-prompt-library-governance-contract.ts` |
| Gate 4 — E2E | `prompt-approval-workflow.spec.ts` |
| Gate 5 — Data Integrity | Prompt hash provenance verified |
| Gate 7 — Governance | Prompt library adapter PL-01 through PL-05 must be COMPLETE |

