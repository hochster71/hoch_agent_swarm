# Task List — Phase 10: Formal Release Finalization Preview

- `[x]` Implement table `formal_release_previews` and database helpers in `backend/runtime_execution_store.py`
- `[x]` Implement API endpoints `/api/v1/release/formal-preview` (GET, GET by ID, POST) in `backend/main.py`
- `[x]` Restart backend FastAPI server to load updated endpoints and schemas
- `[x]` Update frontend template `frontend/index.html` to add formal release finalization preview panel with all required DOM IDs and texts
- `[x]` Update frontend logic `frontend/app.js` to handle preview requests, candidate dropdown updates, and preview run history rendering
- `[x]` Compile local Tailwind CSS assets (`npm run build:tailwind`)
- `[x]` Create contract validation script `scripts/qa/test-formal-release-preview-contract.ts`
- `[x]` Create Playwright E2E specification `tests/e2e/formal-release-preview.spec.ts`
- `[x]` Register run commands and update validation suites in `package.json`
- `[x]` Update documentation: `docs/mission/deep-swarm-page-audit-report.md` & `walkthrough.md`
- `[x]` Verify by building and running full QA suites: `npm run build`, `npm run qa:runtime-full`, `npm run supply:release`
- `[x]` Stage and commit changes (Feature commit and Evidence commit)

