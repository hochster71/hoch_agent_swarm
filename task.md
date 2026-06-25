# Task List — Deep Swarm Page Audit

- `[ ]` Audit repository state (branch, HEAD, commits, Cosign status)
- `[ ]` Verify build & asset integrity (`npm run build`, check CSS files)
- `[ ]` Create and run `scripts/qa/test-full-page-swarm-audit.ts` (view/nav checks)
- `[ ]` Create and run `tests/e2e/full-page-swarm-audit.spec.ts` (Playwright screenshots & traversal)
- `[ ]` Create and run `scripts/qa/test-backend-runtime-api-contract.ts` (API contracts)
- `[ ]` Create and run `scripts/qa/test-runtime-ledger-db-contract.ts` (SQLite contracts)
- `[ ]` Create and run `scripts/qa/test-runtime-event-schema-contract.ts` (WebSocket metrics events)
- `[ ]` Audit Capability Manifest enforcement gap
- `[ ]` Audit Accessibility details (headings, close buttons, zero-width text debt)
- `[ ]` Audit Security details (replay checks, tailwind CDN, browser sandbox constraints)
- `[ ]` Audit Release Evidence (`npm run supply:release` and signing verification)
- `[ ]` Configure package.json scripts (`qa:full-page-swarm-audit`, `qa:backend-runtime-api`, etc.)
- `[ ]` Write full audit report `docs/mission/deep-swarm-page-audit-report.md`
- `[ ]` Run final pipeline validation (full QA tests, release evidence refresh)
- `[ ]` Commit the audit scripts, tests, reports, and evidence packages
