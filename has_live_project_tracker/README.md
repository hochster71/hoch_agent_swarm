# HAS/HASF Live Project Tracker

An autonomous, always-running project tracker and cockpit dashboard for the Hoch Agent Swarm (HAS) and Hoch Application Software Factory (HASF). 

It aggregates real-time metrics, computes critical path schedules, projects delivery milestones, and tracks agent and build lifecycles using event logs.

## Port and Authentication
- **Port**: `3001` (configurable via `TRACKER_PORT` environment variable)
- **Local Authentication**: Basic Auth (configurable via `UI_USER` and `UI_PASS`)
  - Default Username: `admin`
  - Default Password: `change-this-password`

## Key UI Components
1. **QA Verdict Status Gate**: Displays GO / CONDITIONAL GO / NO-GO status with reasoning.
2. **Next Suggested Safe Action**: Recommends the next task that is runnable and has the shortest remaining runtime.
3. **Project Progress Checklist**: 100% truth-bound task checklist with actual/expected runtime analytics and variance.
4. **Swarm Projections**: Estimated completion dates mapped to 8h/day, 12h/day, 16h/day, and 24h/day workload profiles.
5. **Critical Path Chain**: The longest remaining expected-hours chain, pinpointing tasks that dynamically block delivery.
6. **Top Unlocks**: Next 3 tasks that unlock the highest number of downstream tasks.
7. **Landscape Map Tab**: A wide, kanban-style domain lane workspace displaying HAS Core, HAS Personal, HAS Business, HAS Hobbies, Software Factory, AG Bootstrap, Data Consolidation, DevSecOps, and Monetization. Visualizes agent cards, builds strip, and PERT critical paths.
8. **Gap Analysis Tab**: Lists project gaps (P0/P1/P2), matrix capability coverages, missing telemetry data, risk registers, and production speed/QA bottleneck lists.

## UI Intelligence Layer
The dashboard includes an accessible, interactive intelligence layer:
- **Hover/Focus Tooltips**: Custom dark-themed card components styled with blue borders and colored risk/verdict tags. Triggered by either mouse hover or keyboard tab focus. Dismissible using the `Escape` key.
- **Click Detail Drawer**: Clicking any agent, task, domain lane, risk, or build row opens a right-side cockpit panel showing full object states, linked evidence, log file paths, artifact outputs, and copy-to-clipboard JSON capabilities.

---

## Data Model Extensions
### PERT Analysis Fields
Each task dynamically calculates or consumes:
- `optimistic_hours`: Minimum optimistic timeframe (default: `0.7 * expected_hours`).
- `most_likely_hours`: Expected typical timeframe.
- `pessimistic_hours`: Maximum pessimistic timeframe (default: `1.5 * expected_hours`).
- `pert_expected_hours`: Computed expected hours: `(optimistic + 4*likely + pessimistic) / 6`.
- `slack_hours`: Slack time before task delays the critical path.
- `critical_path_flag`: Boolean indicating whether task sits on the longest path.
- `path_drag_hours`: Time the task adds to the critical path length.

### DORA Performance Fields
Tracks throughput and stability parameters:
- `change_lead_time_hours`: Lead time for changes (marked `UNKNOWN` if telemetry lacks git webhook events).
- `deployment_frequency_7d`: Frequency of production releases.
- `failed_deployment_recovery_time_hours`: Time to restore service after a failed deployment.
- `change_fail_rate_percent`: Proportion of deployments causing failure.
- `deployment_rework_rate_percent`: Rework percentage due to bugfixes.

---

## Truth Ledger Integration & Fallback Chain
The tracker binds dynamically to real runtime truth sources using a failover chain:

1. **LIVE_API_TRUTH** (Primary):
   - Hits the HAS API endpoints:
     - State: `http://127.0.0.1:8000/api/v1/runtime-truth/state`
     - Verdict: `http://127.0.0.1:8000/api/v1/final-verifier/verdict`
   - Active when the `has-api` container is running and healthy on Port 8000.
2. **SQLITE_LEDGER_TRUTH** (Local Database):
   - Scans the repository for available SQLite ledger files (e.g., `backend/swarm_ledger.db`).
   - Uses Node's native `node:sqlite` `DatabaseSync` in `readOnly: true` and `enableDefensive: true` mode.
   - Map agents, tasks, builds, and event logs into the tracker models.
3. **FILE_BASED_TRUTH** (Local Fallback):
   - Reads directly from local state files:
     - `has_live_project_tracker/data/status.json`
     - `has_live_project_tracker/data/tasks.json`
     - `has_live_project_tracker/data/events.ndjson`
4. **SIMULATED** (Bootstrap Standalone):
   - Used when no data files exist, displaying simulated mock states.

### Stale Warnings and Fallback Badges
- **Active Badge**: Displays `LIVE_API_TRUTH`, `SQLITE_LEDGER_TRUTH`, or `FILE_BASED_TRUTH` at the top right of the page. Clicking it opens a detail drawer showing active files, health, and fallback sequences.
- **Fallback Warning**: If the tracker falls back to files due to API and DB unreachability, a top warning banner is visible.
- **Stale Check**: Displays `STALE DATA` if the last refresh timestamp exceeds `stale_after_seconds` (default: 300s).

### WAL (Write-Ahead Logging) Notes
When reading SQLite databases concurrently with active worker writes:
- Readers do not lock out writers, and writers do not lock out readers when WAL mode is active.
- Connections use a `busy_timeout = 5000` to prevent blocking during temporary database locks.

### Disk Pressure & Snapshot Retention Policy
To ensure stable host execution under disk pressure, the tracker implements the following gates:
- **Absolute Limit (25 GB)**: If available host free disk space falls below 25 GB, automatic database snapshots are blocked, a `NO SNAPSHOT` warning is displayed, and a P0 gap is raised.
- **Preferred Limit (50 GB)**: If available disk space is between 25 GB and 50 GB, snapshots are permitted but a `WARNING` banner is rendered.
- **Retention Count (10)**: The backups folder stores a maximum of 10 database snapshot backups.
- **Retention Age (7 days)**: Snapshot backups older than 7 days are automatically flagged for removal.

---

## API Endpoints
All endpoints are protected by Basic Auth.
- `GET /` or `/index.html`: Serve the dark-themed cockpit UI.
- `GET /api/truth`: Returns normalized truth state: agents, builds, tasks, events, and projections.
- `GET /api/landscape`: Returns domain lanes, builds, and critical path data for Landscape tab.
- `GET /api/gaps`: Returns severity gap registers, risk profiles, capability matrices, and missing DORA metrics.
- `GET /api/disk`: Returns host disk utilization statistics, backup directory sizes, and snapshot permission flags.
- `GET /api/truth-sources`: Returns state info on detected API health and SQLite databases.
- `GET /api/status`: Returns raw local agent statuses and build states.
- `GET /api/tasks`: Returns raw checklist items.
- `GET /api/events`: Returns the last 100 event ledger blocks.
- `GET /api/health`: Basic service status.
- `POST /api/mark`: Accepts JSON payload to update task status in tasks.json.

---

## Operator Management Scripts
All scripts are located in the `scripts/` directory:
- `scripts/start_live_tracker.sh`: Starts the background Node.js server.
- `scripts/stop_live_tracker.sh`: Terminates the running port 3001 server safely.
- `scripts/tracker_healthcheck.sh`: Verifies all HTTP endpoints (/health, /truth, /truth-sources, /status, /tasks, /landscape, /gaps).
- `scripts/tracker_truth_sources.sh`: Queries the active truth sources configuration and prints formatted JSON.
- `scripts/tracker_snapshot_sqlite.sh`: Creates a safe read-only backup snapshot of a live database without blocking concurrent transactions.

---

## E2E Testing
E2E integration tests are run via Playwright. Verify tooltips, drawer components, Escape keys, and API endpoints using:
```bash
# Run all E2E test files
npx playwright test tests/e2e/has-hasf-live-tracker-tooltips.spec.ts tests/e2e/has-hasf-live-tracker-truth-sources.spec.ts tests/e2e/has-hasf-live-tracker-landscape.spec.ts tests/e2e/has-hasf-live-tracker-gap-analysis.spec.ts --workers=1
```
