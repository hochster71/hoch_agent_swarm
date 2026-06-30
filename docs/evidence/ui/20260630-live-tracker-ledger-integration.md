# HAS/HASF Live Project Tracker Ledger Integration Evidence — 2026-06-30

This document records the verification, E2E testing, and schema discovery for the truth ledger integration in the HAS/HASF Live Project Tracker.

## Files Changed
- `has_live_project_tracker/server.js` (Implemented findSqliteLedgers, readSqliteLedgerTruth, normalizeTruth, computeTruth, /api/truth-sources endpoint)
- `has_live_project_tracker/index.html` (Added truth source badge header rendering, fallback warning banners, badge tooltip, and details drawer integration)
- `has_live_project_tracker/README.md` (Documented WAL mode details, fallback chain priorities, and execution instructions)
- `scripts/tracker_healthcheck.sh` (Upgraded to verify health, truth, truth-sources, status, and tasks endpoints)
- `scripts/tracker_truth_sources.sh` (Created JSON formatter tool for checking active source configurations)
- `scripts/tracker_snapshot_sqlite.sh` (Created safe SQLite backup tool utilizing online backup API)
- `tests/e2e/has-hasf-live-tracker-truth-sources.spec.ts` (Playwright E2E integration test spec)
- `tests/e2e/has-hasf-live-tracker-tooltips.spec.ts` (Playwright E2E tooltip test spec - resolved hover mouse race conditions)

## DB Files Found
1. `backend/swarm_ledger.db` (Primary Immutable Ledger, size: 7.3 MB, 70 tables)
2. `backend/db/swarm_ledger.db` (Secondary / Run Database, size: 204 KB, 23 tables)
3. `backend/runtime_truth/state.db` (Empty SQLite database)
4. `hoch_skill_audit.db` (Offline agent skill audits)
5. `cybersecurity_diagrams.db` (System flow diagrams)
6. `data/brain_evidence.db` (Semantic graph linkages)

## Schema Mappings & Tables Used
- **swarm_agents** -> mapped to `agents`
- **swarm_tasks** -> mapped to `tasks`
- **qa_runs** -> mapped to `builds`
- **ledger_blocks** -> mapped to `events` (Parsed from event JSON block structure)

For details, see [20260630-live-tracker-ledger-schema-map.md](file:///Users/michaelhoch/hoch_agent_swarm/docs/evidence/ui/20260630-live-tracker-ledger-schema-map.md).

## Chosen Truth Source
- **Selected Source**: `SQLITE_LEDGER_TRUTH`
- **Reason**: Live API on Port 8000 is currently offline. The server successfully scanned for local databases and established a read-only, defensive connection to `backend/swarm_ledger.db` as the primary database source.
- **Fallback Status**: Fallback inactive (using database truth).

## Healthcheck Result
Running `./scripts/tracker_healthcheck.sh`:
```
==================================================
RUNNING FULL TRACKER HEALTH CHECK
==================================================
Checking /api/health... [PASS] (200)
Checking /api/truth... [PASS] (200)
Checking /api/truth-sources... [PASS] (200)
Checking /api/status... [PASS] (200)
Checking /api/tasks... [PASS] (200)
==================================================
[PASS] All tracker endpoints healthy.
==================================================
```

## E2E Tests Run
Running `npx playwright test`:
```
Running 2 tests using 1 worker

  ✓  1 [antigravity-chromium] › tests/e2e/has-hasf-live-tracker-tooltips.spec.ts:11:7 › HAS/HASF Live Project Tracker Tooltips & Drawer E2E › verifies tooltips and detail drawer interactions (1.1s)
  ✓  2 [antigravity-chromium] › tests/e2e/has-hasf-live-tracker-truth-sources.spec.ts:11:7 › HAS/HASF Live Project Tracker Truth Sources E2E › verifies truth source badges, tooltips, and drawer cockpit integration (1.1s)

  2 passed (2.5s)
```

## QA Verdict
- **Verdict**: GO
- **Reason**: The tracker successfully connects to the SQLite ledger database read-only, maps all agent, task, build, and event fields dynamically, adds task `T032` to the checklist, and falls back cleanly to local JSON files if the database is removed. The full suite of E2E tests passed with 100% success.

## Remaining Gaps
- The live HTTP API (`has-api` on Port 8000) is currently offline, so the tracker is operating on `SQLITE_LEDGER_TRUTH` database mode instead of `LIVE_API_TRUTH` mode.
