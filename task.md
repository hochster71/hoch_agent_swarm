# Execution Checklist — Phase 27, Batch PR-5, Batch PR-6 & Batch PR-7

## Phase 27: Release Evidence Archive Preview
- [x] Register `GET /api/v1/release/evidence/archive/preview` endpoint in `backend/main.py`
- [x] Add `#release-evidence-archive-preview-panel` UI section in `frontend/index.html`
- [x] Add archive preview loading, rendering, and export handlers in `frontend/app.js`
- [x] Write contract test `scripts/qa/test-release-evidence-archive-preview-contract.ts`
- [x] Write E2E test `tests/e2e/release-evidence-archive-preview.spec.ts`
- [x] Register new scripts in `package.json`
- [x] Execute localized and pipeline validation tests
- [x] Complete walkthrough report

## Batch PR-5: P5 QA Evidence Matrix Integration
- [x] Add 4 current production-readiness controls and 8 test specifications to `config/qa_evidence_matrix.json` (Phase 27, 28, 29, 30)
- [x] Add 4 imported historical audit controls (`CREWAI-ADAPTER-001`, `ENV-PREFLIGHT-001`, `MANIFEST-ALIGN-001`, `QUALITY-GATE-001`) and 8 tests mapping G01-G20 findings to `config/qa_evidence_matrix.json`
- [x] Verify summary metrics exposed by `/api/v1/production-readiness` (24 total controls, 46 tests, 37 passes, 21 evidence present)
- [x] Execute contract checks `npm run qa:ui-contract` to ensure static contract validation passes
- [x] Run local CI integration pipeline `python3 scripts/qa/run-ci-pipeline.py` to ensure clean execution and report re-generation
- [x] Add `tests/e2e/dast-unsigned-ui-negative.spec.ts` to git tracking
- [x] Commit all matrix updates, codebase adaptations, and generated release reports to branch `release/v0.1.6-error-budget-aware-autonomy`
- [x] Sync and finalize artifacts in the brain directory (updated `walkthrough.md` and `task.md`)

## Batch PR-6: Final E2E Production Readiness Audit Run
- [x] Run full production-readiness endpoint probe (`/api/v1/production-readiness`)
- [x] Run prompt governance probes (risk classification, test-state isolation, and TTL gating)
- [x] Run skill gate probes (SQLite logging and fail-closed logic)
- [x] Run QA matrix probe (`/api/v1/qa/evidence-matrix` matches 24-control schema)
- [x] Run release archive preview contract and E2E specs
- [x] Run Playwright E2E smoke tests (`npm run qa:e2e-runtime`)
- [x] Verify remaining host port findings (7 ports bound to `*` on MacBook Pro)
- [x] Generate final `production_readiness_audit.md` report
- [x] Compute final Go/No-Go posture (NO-GO due to 4 remaining blockers)
- [x] Commit sealed audit evidence to branch `release/v0.1.6-error-budget-aware-autonomy`

## Batch PR-7: Production Blocker Burn-Down
- [x] Identify and disposition 7 LAN-exposed ports in `config/port_hardening_audit.json`
- [x] Implement runtime agent execution TTL/timeout policy in `backend/agent_runner.py`
- [x] Implement dynamic node TTL lookup and propagate TTL in `backend/main.py`
- [x] Intercept task execution and enforce Skill Gate checks in `backend/main.py`
- [x] Dynamically resolve `gap001_status`, `gap003_status`, `gap008_status` in `backend/main.py`
- [x] Recalibrate test results and control statuses in `config/qa_evidence_matrix.json`
- [x] Rerun local CI integration pipeline and verification tests
- [x] Update and finalize walkthrough reports and task check-offs

## Batch PR-8 & PR-9: Final E2E Release Audit Run & Sealing
- [x] Integrate dynamic `GAP-010` (E2E Audit Run) resolution in `backend/main.py`
- [x] Transition `T-EV-003`, `T-E2E-001`, and `T-GNG-001` to `PASS` in `config/qa_evidence_matrix.json`
- [x] Update summary metrics and complete matrix status in `config/qa_evidence_matrix.json`
- [x] Generate candidate release packet (`npm run candidate:release-packet`)
- [x] Run E2E release seal Playwright test (`npm run e2e:release-seal-attestation`)
- [x] Verify operational readiness scorecard has 100/100 rating (`npm run qa:readiness`)
- [x] Align release git tag `v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY` to the final HEAD commit
- [x] Commit release configurations and finalize checklist

## Batch PR-7A & UI-AUDIT-1: Local-First Model Router & Theme Audit
- [x] Create local model configurations `config/models.yaml` and `config/escalation.yaml`
- [x] Register `SKILL-MODEL-ROUTE` in `config/skill_registry.json`
- [x] Implement backend model router modules in `backend/model_router/`
- [x] Integrate model router endpoints and readiness metrics in `backend/main.py`
- [x] Implement Kimi multi-color CSS accent themes in `frontend/styles.css`
- [x] Add Kimi Theme Selector and Local-First Model Router panel to `frontend/index.html`
- [x] Wire model router panel data-binding and theme manager in `frontend/app.js`
- [x] Add model router tests (`tests/test_model_registry.py`, `tests/test_escalation_policy.py`, `tests/test_model_router_policy.py`)
- [x] Update QA matrix in `config/qa_evidence_matrix.json` with new controls/tests
- [x] Write doctrine in `docs/mission/local_first_ai_doctrine.md`
- [x] Compile visual system theme audit report in `artifacts/qa/ui_theme_audit/multi_color_kimi_baseline_audit.md`
- [x] Verify all tests pass and commit changes with the required message

## Batch PR-10: Operator Final Release Authorization
- [x] Ingest final operator release authorization in `backend/main.py`
- [x] Create authorization configuration `config/release_authorization.json`
- [x] Create authorization document `docs/mission/final_release_authorization.md`
- [x] Update QA matrix test T-GNG-001 in `config/qa_evidence_matrix.json`
- [x] Create pytest suite `tests/test_release_authorization_gate.py`
- [x] Verify all unit, contract, and CI tests pass
- [x] Commit changes with the required message

## Batch UI-KOI-1: Koi Animation Layer
- `[x]` Add `#koi-pond-layer` background element to `frontend/index.html`
- `[x]` Implement `.koi-fish`, `.koi-ripple`, and `.koi-orbit` styling in `frontend/styles.css`
- `[x]` Implement reduced-motion behavior in `frontend/styles.css`
- `[x]` Implement Koi animation initialization in `frontend/app.js`
- `[x]` Create contract test `scripts/qa/test-koi-animation-contract.ts`
- `[x]` Register script and update contract runner in `package.json`
- `[x]` Run contract verification and CI pipeline successfully
- `[x]` Stage and commit changes with the required message

