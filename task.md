# Task List — Phase 8: Operator Approval Ledger + Governance Command Center

- `[x]` Harden test bypass check in `backend/main.py` using `TEST_MODE` global constant
- `[x]` Add GET `/api/v1/governance/summary` REST endpoint in `backend/main.py`
- `[x]` Update `.github/workflows/nav-contract-qa.yml` to set `TEST_MODE=true`
- `[x]` Update `scripts/qa/run-ci-pipeline.py` to set `TEST_MODE=true` uvicorn launch environment
- `[x]` Add Governance Cockpit navigation item HTML in `frontend/index.html`
- `[x]` Add Governance Cockpit main panel HTML in `frontend/index.html`
- `[x]` Add JavaScript mapping and tab switching logic in `frontend/app.js`
- `[x]` Implement `fetchAndRenderGovernanceSummary()` rendering logic in `frontend/app.js`
- `[x]` Add list status check for `nav-governance` in `updateNavStatuses()` in `frontend/app.js`
- `[x]` Create contract validation script `scripts/qa/test-operator-governance-cockpit.ts`
- `[x]` Create Playwright E2E spec `tests/e2e/operator-governance-cockpit.spec.ts`
- `[x]` Register scripts in `package.json` (`qa:operator-governance`, `e2e:operator-governance`)
- `[x]` Update `docs/mission/deep-swarm-page-audit-report.md`
- `[x]` Update `walkthrough.md`
- `[x]` Run full verification suite and verify PASS status
- `[x]` Commit the Phase 8 changes and refresh release evidence
