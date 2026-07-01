# Evidence Proof — Live Tracker Landscape & Gap Analysis

This document outlines the validation details, metrics logs, and E2E test results for the Landscape and Gap Analysis views, including the Host Disk Pressure Guard.

## 1. Files Changed
- **[has_live_project_tracker/server.js](file:///Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/server.js)**: Integrated `/api/landscape`, `/api/gaps`, and `/api/disk` routes.
- **[has_live_project_tracker/index.html](file:///Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/index.html)**: Added navigation tabs, Landscape columns, Gap matrix tables, and Host Disk Pressure scorecard.
- **[has_live_project_tracker/README.md](file:///Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/README.md)**: Updated API endpoints and disk pressure policy docs.
- **[scripts/tracker_disk_check.sh](file:///Users/michaelhoch/hoch_agent_swarm/scripts/tracker_disk_check.sh)**: Executable check utility.
- **[scripts/tracker_gap_report.sh](file:///Users/michaelhoch/hoch_agent_swarm/scripts/tracker_gap_report.sh)**: Executable gaps listing utility.
- **[scripts/tracker_landscape_report.sh](file:///Users/michaelhoch/hoch_agent_swarm/scripts/tracker_landscape_report.sh)**: Executable landscape roadmapping utility.

## 2. API Endpoint Results
- `/api/disk` output:
  ```json
  {
    "disk_total": 926.3,
    "disk_used": 593.96,
    "disk_available": 306.43,
    "disk_capacity_percent": 66,
    "snapshot_dir_size": 0,
    "retention_policy": {
      "max_snapshot_count": 10,
      "max_snapshot_age_days": 7,
      "min_free_disk_gb_preferred": 50,
      "min_free_disk_gb_absolute": 25
    },
    "snapshot_allowed": true,
    "warning": ""
  }
  ```

## 3. Playwright E2E Results
All 4 test specs pass sequentially:
```
Running 4 tests using 1 worker

  ✓  1 [antigravity-chromium] › tests/e2e/has-hasf-live-tracker-gap-analysis.spec.ts:11:7 (1.7s)
  ✓  2 [antigravity-chromium] › tests/e2e/has-hasf-live-tracker-landscape.spec.ts:11:7 (1.1s)
  ✓  3 [antigravity-chromium] › tests/e2e/has-hasf-live-tracker-tooltips.spec.ts:11:7 (1.1s)
  ✓  4 [antigravity-chromium] › tests/e2e/has-hasf-live-tracker-truth-sources.spec.ts:11:7 (1.1s)

  4 passed (5.5s)
```

## 4. Host Disk Pressure Status
- **Capacity**: 66% used.
- **Available**: 306.43 GB free space.
- **Snapshot Status**: `ALLOWED` (above the absolute 25 GB and preferred 50 GB margins).

## 5. QA Verdict Gate
- **Status**: `CONDITIONAL GO`
- **Reason**: Live API on port 8000 is offline; operating on SQLite local backups.
