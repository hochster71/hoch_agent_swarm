# Task List — Phase 11: Formal Release Approval Simulator

- `[x]` Implement API route `POST /api/v1/release/formal-preview/{formal_preview_id}/approve-request` in `backend/main.py`
- `[x]` Update decision handler `POST /api/approval/requests/{approval_id}/decisions` to write simulation reports for preview gates
- `[x]` Update frontend template `frontend/index.html` to add request button and simulation report display
- `[/]` Update frontend logic `frontend/app.js` to support approval requests, update statuses, and display reports
- `[x]` Compile local Tailwind CSS assets (`npm run build`)
- `[x]` Create contract validation script `scripts/qa/test-formal-release-approval-contract.ts`
- `[x]` Create Playwright E2E specification `tests/e2e/formal-release-approval.spec.ts`
- `[x]` Register run commands and update validation suites in `package.json`
- `[x]` Update documentation: `docs/mission/deep-swarm-page-audit-report.md` & `walkthrough.md`
- `[x]` Verify by building and running full QA suites: `npm run build`, `npm run qa:runtime-full`, `npm run supply:release`
- `[x]` Stage and commit changes (Feature commit and Evidence commit)
