# PROTO-1 — HOCH Mesh Sentinel Map

## Mission
Spin up the first Kimi-style HOCH prototype using the HOCH theme, but enforce:

LIVE RUNTIME OR DELETE / QUARANTINE.

## Checklist
- [x] Create backend Mesh Sentinel map aggregator
- [x] Add custom CSS classes and `@keyframes led-pulse` to `frontend/index.html` style section
- [x] Update layout of `#view-clawde` card to add `#clawde-phase-cards-container` and `#clawde-selected-status-light` in `frontend/index.html`
- [x] Add `#clawde-gate-lockout-notice` in Gated Execution Control inside `frontend/index.html`
- [x] Update build version headers and app script tag to `UX2` in `frontend/index.html`
- [x] Implement `selectedPhase` state and card selection controller logic in `frontend/app.js`:ui-contract
- [x] Run E2E runtime checks
- [x] Run CI pipeline
- [x] Commit and retag
- [x] Add fail-closed guard checks in `backend/prompt_registry.py`
- [x] Update `@app.post("/api/prompts/{prompt_id}/run")` in `backend/main.py` to check guards and append to run ledger
- [x] Implement backend EvidenceOps endpoints in `backend/main.py`
- [x] Build exportable bundle routines (zip, markdown, csv, json) in `backend/main.py`
- [x] Add EvidenceOps View elements in `frontend/index.html` (sidebar tab, telemetry cards, ledger table, snap panel, download options)
- [x] Wire up views navigation and telemetry fetch bindings in `frontend/app.js`
- [x] Write automated Phase 6 integration tests in `tests/test_evidenceops_v6.py`
- [x] Run unit tests and contract suites to ensure no regressions
- [x] Generate v6 validation evidencetag
- [x] Initialize local tool registry files (`tool_registry.json` and `toolops_state.json`)
- [x] Create `backend/toolops_manager.py` with registry management, action policy engine, host filtering, and parameters check
- [x] Update `backend/main.py` with ToolOps REST endpoints (tools, policies, authorize, audit-log, blocked, approve, ci-gate)
- [x] Integrate ToolOps checks into `/api/prompts/{prompt_id}/run`
- [x] Add ToolOps sidebar link and dashboard view in `frontend/index.html`
- [x] Wire up dashboard selectors, metrics, tables, override buttons, and audit trail in `frontend/app.js`
- [x] Write automated tests in `tests/test_toolops_v8.py`
- [x] Run full unit tests and contract suites to ensure no regressions
- [x] Generate v8 validation evidencetag
