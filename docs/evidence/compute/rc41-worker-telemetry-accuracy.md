# RC41 Worker Telemetry Accuracy Evidence Log

**Target Release**: `v0.1.8-accuracy`  
**Date**: 2026-07-01  
**Category**: Compute / Worker Telemetry Accuracy  
**Auditor**: Antigravity (QA Auditor Agent)  

---

## 1. Schema Validation Compliance
Every telemetry key inside `/api/pert/data` carries a complete 6-field schema (`value`, `source`, `last_updated`, `freshness`, `confidence`, `fallback_state`).

Additionally, for every worker under `tailnet_workers`, we have expanded to the 11-field telemetry-wrapped model:
* `worker_id`
* `role`
* `online_status`
* `last_heartbeat`
* `last_job_time`
* `last_probe_time`
* `last_evidence_file`
* `data_source`
* `freshness`
* `confidence`
* `unknown_reason` (or `not_applicable_reason` when appropriate)

## 2. Worker Utilization Ledger Resolution Table

| Worker ID | Role | Status | Last Job Time | Last Probe Time | Unknown Reason |
| --- | --- | --- | --- | --- | --- |
| `michaels-macbook-pro` | `build_worker` | `ONLINE` | `<timestamp>` | `N/A — build worker` | `None` |
| `hoch-relay-001` | `relay_worker` | `ONLINE` | `UNKNOWN — no dispatch evidence yet` | `<timestamp>` | `no dispatch evidence yet` |
| `iphone-15-pro-max` | `operator_mobile_monitor` | `ONLINE` | `N/A — monitor-only` | `N/A — no CLI support on iOS / monitor-only` | `None` |

---

## 3. Evidence Gathering Verification
The `relay_health_probe.sh` script successfully probes the Tailscale IP of the relay worker and logs evidence locally at:
* `has_live_project_tracker/data/relay_probe_evidence.json`

This evidence-backed probe timestamp is dynamically rendered in the cockpit under `LAST PROBE TIME` for `hoch-relay-001`.
