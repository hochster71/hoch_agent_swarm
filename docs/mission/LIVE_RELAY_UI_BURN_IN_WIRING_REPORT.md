# LIVE RELAY UI BURN-IN WIRING REPORT

This report documents the verification, integration, and deployment of the primary systemd burn-in state into the HOCH-200 Relay Dashboard, including refined QA parameters.

---

## 1. Deployment Details

- **Tailscale Dashboard URL**: http://100.87.18.15:3012/
- **Privacy Status**: **PRIVATE** (Bound to Tailscale interface only, public port 3012 is blocked).
- **Endpoint Status**: HTTP 200 OK for `/health` and `/api/burn-in/status`.
- **Docker Mount Structure**: The container's `/data` directory is mounted directly to the host's `/root/hoch_agent_swarm/has_live_project_tracker/data` path in **read-only** mode for security isolation. Transient dashboard files are kept in `/tmp`.

---

## 2. API Telemetry Verification & QA Refinement

Query to `http://100.87.18.15:3012/api/burn-in/status` returned the following status and explicit telemetry sources:

- `state_indicator`: `"PRIMARY_SYSTEMD_BURN_IN_ACTIVE"`
- `heartbeat_status`: `"HEARTBEAT_FRESH"`
- `real_cycles`: 40
- `simulated_cycles`: 0
- `failed_cycle_rate`: 0.00%
- `pending_task_count`: 7
- `doctrine_status`: `"GO"`
- `24h_go_status`: `"NOT_YET"`
- **Refined Telemetry Metadata**:
  - `cycle_count_source`: `"/root/hoch_agent_swarm/has_live_project_tracker/data/ag_execution_daemon_state.json"`
  - `cycle_count_timestamp`: `"2026-07-05T07:00:02.365258Z"`
  - `daemon_started_at`: `"2026-07-05T06:21:00.338037Z"`
  - `api_generated_at`: `"2026-07-05T07:00:20+00:00"`
  - `elapsed_hours`: `0.6556`
  - `telemetry_host_path`: `"/root/hoch_agent_swarm/has_live_project_tracker/data"`
  - `container_mount_mode`: `"read_only"`

---

## 3. UI Features Wired

The dashboard now dynamically displays:
1. **Autonomy Status Banner & Metric Card** (`PRIMARY_SYSTEMD_BURN_IN_ACTIVE` state check).
2. **Completed Cycles Counters** (Separating Real vs. Simulated).
3. **Elapsed Time Tracking** (Dynamic computation based on daemon start time).
4. **Daemon State & Policy Details** (Heartbeat state, hold state, last cycle status, last task ID).
5. **Autonomy Validation Checks** (Queue health, proof integrity, lease fencing, failed rate).

---

## 4. Final Verdict

### **FINAL VERDICT: LIVE_UI_BURN_IN_WIRED**

*Derivation*: The Relay Dashboard successfully reads the active primary systemd burn-in states from the shared telemetry files on `hoch-relay-001` and displays them in real-time in the browser. All refined QA telemetry metadata is populated.
