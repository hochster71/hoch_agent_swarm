# Production Roadmap

This roadmap outlines the multi-phase deployment of the Prompt Control Plane.

## Phase 0: Baseline Inventory and Safety
- **Objective**: Verify existing repository status and index assets without affecting runtime execution.
- **Scope**: Code base files, endpoints, prompt library directory, evidence logs.
- **Exit Criteria**: Full list of available files and routes indexed.
- **Evidence Required**: Git tree check and API status logs.
- **Release Gate**: Local verification check pass.
- **Rollback Condition**: Disruption of uvicorn start.

## Phase 1: Governance Doctrine and Config
- **Objective**: Seed the governance documentation, configuration files, and QA contract checking.
- **Scope**: Doc markdown files, JSON config, contract test script, and package scripts.
- **Exit Criteria**: Contract test passes and configuration validated.
- **Evidence Required**: `test-prompt-control-plane-contract.ts` execution output.
- **Release Gate**: CONDITIONAL GO (no runtime execution modifications).
- **Rollback Condition**: Verification script failure.

## Phase 2: Prompt Registry Loader
- **Objective**: Load prompt library JSON and build indices by ID/Category/Industry/Title.
- **Scope**: Backend prompt parser, `/api/v1/prompts/registry` endpoint.
- **Exit Criteria**: API returns list of 103 valid prompts with metadata.
- **Evidence Required**: Registry API 2xx curl output.
- **Release Gate**: Test environment passing contract tests.
- **Rollback Condition**: Internal server errors on backend loading.

## Phase 3: Prompt Router
- **Objective**: Select prompt chains and wrap them with the Universal Agent Contract.
- **Scope**: Router service, selected_prompts.json generation.
- **Exit Criteria**: Dynamic prompt selection based on task category.
- **Evidence Required**: Generated selected_prompts.json trace.
- **Release Gate**: Simulated task routing validation pass.
- **Rollback Condition**: Prompt structure distortion or execution failure.

## Phase 4: Approval Gate
- **Objective**: Intercept material actions and stage them for manual approval.
- **Scope**: Middlewares, database approval state ledger, cockpit queue UI.
- **Exit Criteria**: Blocked actions staged in approval queue.
- **Evidence Required**: HTTP 202 staging trace logs.
- **Release Gate**: Human review audit verify.
- **Rollback Condition**: Autonomous execution bypasses approval gate.

## Phase 5: Evidence Collector
- **Objective**: Automate evidence manifest creation for every task execution loop.
- **Scope**: Evidence logging module, SHA-256 calculator, file storage.
- **Exit Criteria**: Manifest generated and written to audit ledger.
- **Evidence Required**: Cryptographically signed `evidence_manifest.json` logs.
- **Release Gate**: Integration verification pass.
- **Rollback Condition**: Write failures or missing manifest items.

## Phase 6: Dashboard Integration
- **Objective**: Build cockpit cards for metrics, registry, routing, approval, and red-team tests.
- **Scope**: Frontend index.html, app.js, dashboard style bundles.
- **Exit Criteria**: All cards render correctly and update telemetry on poll.
- **Evidence Required**: Screenshot and HTML page contract pass.
- **Release Gate**: UI end-to-end test pass.
- **Rollback Condition**: Dashboard loading states stuck or HTTP 404s.

## Phase 7: Cybersecurity and ConMon Integration
- **Objective**: Wire continuous monitoring task runners and safety scan hooks.
- **Scope**: ConMon cron/schedulers, prompt injection test suite, secrets scanner.
- **Exit Criteria**: Automated security audits reporting.
- **Evidence Required**: ConMon compliance reports.
- **Release Gate**: Cyber audit pass.
- **Rollback Condition**: High risk findings ignored or scanner performance impact.

## Phase 8: Ephemeral Pipeline Executor
- **Objective**: Execute agent tasks in temporary isolated workspaces.
- **Scope**: Workspace isolation module, dynamic env creation, automated teardown.
- **Exit Criteria**: Temporary directory destroyed, evidence preserved.
- **Evidence Required**: Clean directory lists and validation reports.
- **Release Gate**: Safe mode validation.
- **Rollback Condition**: Orphan directories left behind or code changes leaking outside.

## Phase 9: App Factory Runtime
- **Objective**: Establish the Idea-to-Package app creation lifecycle.
- **Scope**: Software Factory build scripts, signing, packaging helpers.
- **Exit Criteria**: Automated compilation of verified app binaries.
- **Evidence Required**: Signed installer package output.
- **Release Gate**: Signature policy check pass.
- **Rollback Condition**: Unapproved build modifications.

## Phase 10: Final Production
- **Objective**: Full integration of all components into the HOCH AI OS.
- **Scope**: Complete codebase, UI dashboard, model pools, known assets registry.
- **Exit Criteria**: 100% QA contract passing, continuous monitoring live.
- **Evidence Required**: Full audit matrix passing.
- **Release Gate**: GO decision.
- **Rollback Condition**: Unresolved high-risk safety or performance anomalies.
