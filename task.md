# Task List — Phase 4: Core Runtime Build and Hardening

- `[x]` Initialize SQLite persistent database schema inside `swarm_ledger.db`
- `[x]` Implement frontend runs dropdown selector fetching from `GET /api/v1/runs`
- `[x]` Implement frontend task state flow grid updating from `GET /api/v1/runs/{run_id}/tasks`
- `[x]` Implement pending operator approvals queue fetching from `GET /api/approval/requests`
- `[x]` Bind approval actions to send operator decisions to `POST /api/approval/requests/{approval_id}/decisions`
- `[x]` Resolve browser console error in topology agent overlay animation
- `[x]` Run full E2E and readiness validation suites with 100/100 pass score
- `[x]` Finalize Phase 4 build report in `docs/mission/phase-4-runtime-build-report.md`
- `[x]` Update system walkthrough.md
- `[x]` Design and implement agent capability manifest authorization model
- `[x]` Implement approval-gate replay protection (prevent double decisions)
- `[x]` Expand SQLite artifacts table to store key provenance fields
- `[x]` Stream runtime execution events (delta events) over WebSockets
- `[x]` Add browser-based E2E test verifying full chain execution and DB state transitions
