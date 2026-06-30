# HAS/HASF Control Plane Real Event Producers & SQLite Snapshot Scheduler

Evidence of integration, verification results, and E2E validation for real event producers and the T043 SQLite snapshot scheduler.

---

## 1. Real Event Producers (T058–T061)
We have successfully decoupled live visual flow overlays from fake telemetry by writing real, authenticated event producers:
- **T058 (Agent Heartbeat)**: Script `scripts/tracker_emit_agent_heartbeat.sh` queries active agents in `data/status.json` and POSTs heartbeats to `/api/event`.
- **T059 (Build/Test/Scan)**: Script `scripts/tracker_emit_build_event.sh` queries builds in `data/status.json` and POSTs events to `/api/event`.
- **T060 (Registry & Evidence)**: 
  - `scripts/tracker_emit_registry_event.sh` indexes items from `global_project_registry.json`.
  - `scripts/tracker_emit_evidence_event.sh` posts events for completed tasks with valid evidence paths.
- **T061 (DORA Commit/Deploy)**: `scripts/tracker_emit_dora_event.sh` tails `dora_events.ndjson`. (Reports `NO DATA` when empty).

All scripts connect via Basic Authentication credentials loaded from `~/.hoch-secrets/has-tracker.env`.

---

## 2. Safe SQLite Snapshot Scheduler (T043)
The utility `scripts/tracker_run_snapshot_scheduler.sh` executes safe database snapshots under strict disk guards:
- **Disk Guard**: Checks `/api/disk` to verify `snapshot_allowed` is `true` and host free space > 50 GB.
- **Online Backup**: Executes `Connection.backup()` via Python's standard `sqlite3` library to create a zero-lock read-only backup file inside `has_live_project_tracker/backups/`.
- **Permissions**: Snapshot files are explicitly set to read-only (`chmod 444`).
- **Retention**: Max 10 snapshots are kept; snapshots older than 7 days are automatically pruned.

---

## 3. Playwright E2E Verification
All 11 tests pass successfully:
- `tests/e2e/has-hasf-live-flows.spec.ts` -> **PASS**
- `tests/e2e/has-hasf-control-plane-v2.spec.ts` -> **PASS**
- `tests/e2e/has-hasf-live-tracker-truth-sources.spec.ts` -> **PASS**
