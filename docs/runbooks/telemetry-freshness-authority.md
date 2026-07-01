# Telemetry Freshness Authority Runbook

## Overview
This runbook explains how to monitor, configure, and troubleshoot the Telemetry Freshness Authority layer of the PERT Command Center.

## Architecture
The freshness authority layer checks the age of incoming telemetry points against a policy. If a telemetry metric's timestamp exceeds the threshold, the corresponding dashboard card/panel is marked `STALE` (yellow border) or `DEGRADED`/`UNKNOWN` (red border).

### Threshold Configurations
Policy is defined in [telemetry_freshness_policy.yaml](file:///Users/michaelhoch/hoch_agent_swarm/config/telemetry_freshness_policy.yaml):
- `dashboard_render_time`: 60s
- `global_last_full_verification_time`: 600s
- `worker_last_probe_time`: 600s
- `worker_last_dispatch_time`: 86400s
- `device_last_seen_time`: 300s
- `evidence_ledger_last_scan_time`: 1800s
- `playwright_scoped_spec_last_run_time`: 3600s
- `playwright_full_suite_last_run_time`: 86400s

## Audit Audits and Failures
1. **No Fake Telemetry Audit Failures**: If `fake_status_violations` exists or `no_fake_status_violations` > 0:
   - Readiness score is forced to `DEGRADED`.
   - Goal completion confidence drops to `DEGRADED (Telemetry Audit Failure)`.
   - The Executive Readiness panel glows red (degraded status).
   - **Remediation**: Run telemetry freshness remediation script.

2. **Stale Workers**: If a worker node (e.g. `iphone-15-pro-max` or `hoch-relay-001`) is offline:
   - The heartbeat is loaded from `has_live_project_tracker/data/worker_heartbeats.json`.
   - Its freshness will correctly increase over time rather than resetting to `0.0s`.

## Operations
To run a manual telemetry compliance check:
```bash
./scripts/telemetry_freshness_audit.sh
```

To run E2E verification:
```bash
./scripts/rc43_telemetry_freshness_verify.sh
```
