# Worker Telemetry Accuracy Runbook (RC41)

This runbook outlines the operational procedures for managing, auditing, and troubleshooting the Worker Utilization Ledger telemetry.

---

## 1. Worker Telemetry Model Overview

To align with audit-grade requirements, all tailnet devices are categorized by role:
- **Build Workers** (`michaels-macbook-pro`): Allowed to run jobs. Tracked via local scheduler execution.
- **Relay Workers** (`hoch-relay-001`): Allowed to run safe relay probes. Tracked via health probes.
- **Operators / Monitors** (`iphone-15-pro-max`): Blocked from running jobs. Tracked as N/A monitor-only.

## 2. Triggering a Manual Relay Health Probe

To update the `LAST PROBE TIME` for `hoch-relay-001` on the dashboard:
1. Ensure Tailscale is active and the relay worker is visible:
   ```bash
   tailscale status
   ```
2. Run the health probe script:
   ```bash
   bash scripts/relay_health_probe.sh
   ```
3. Verify that the output evidence file is updated:
   ```bash
   cat has_live_project_tracker/data/relay_probe_evidence.json
   ```

## 3. Troubleshooting Telemetry Gaps

If a worker shows `UNKNOWN — no dispatch evidence yet`:
- Confirm that the worker has successfully registered or executed its first scheduled job.
- Verify scheduler logs to check for ID mapping errors.
- Ensure that the telemetry truth checker does not report schema violations.
