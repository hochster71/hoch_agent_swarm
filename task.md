# Task List — Phase 7: Immutable Release Channel + Tag Governance

- `[x]` Add release channel policy model in `backend/main.py`
- `[x]` Add REST endpoint `GET /api/v1/release/channel-governance` in `backend/main.py`
- `[x]` Add REST endpoint `POST /api/v1/release/channel-decision` in `backend/main.py`
- `[x]` Update `scripts/supply-chain/generate-release-manifest.ts` to embed channel and tag fields in the manifest
- `[x]` Update `scripts/supply-chain/verify-release-artifacts.ts` to enforce release channel and tag policies
- `[x]` Add Release Channel Governance panel HTML in `frontend/index.html`
- `[x]` Add JavaScript rendering and decision handler logic in `frontend/app.js`
- `[x]` Create contract validation script `scripts/qa/test-release-channel-governance-contract.ts`
- `[x]` Create Playwright E2E spec `tests/e2e/release-channel-governance.spec.ts`
- `[x]` Register scripts in `package.json` (`qa:release-channel-governance`, `e2e:release-channel-governance`)
- `[x]` Update `docs/mission/deep-swarm-page-audit-report.md`
- `[x]` Update `walkthrough.md`
- `[x]` Run full verification suite and verify PASS status
- `[x]` Commit the Phase 7 changes and refresh release evidence
