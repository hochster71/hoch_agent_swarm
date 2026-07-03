# Control Plane Status Aggregator & Verification Audit

## 1. Contract Overview
- **schema_version**: `1.0`
- **as_of**: `2026-07-03T21:26:47.507352Z`
- **expires_at**: `2026-07-03T21:27:47.507352Z`
- **max_age_seconds**: `60`
- **current contract_state**: `FRESH`

---

## 2. Section Provenance Summary
Each major section of the control plane status contract is wrapped with its respective provenance metadata:

- **authority**: Syncing from `has_live_project_tracker/data/orchestration_bridge_control.json` (HOCH-200 owned).
- **compute**: Syncing from `config/compute_assets.json`.
- **rung_state**: Syncing from `has_live_project_tracker/data/orchestration_bridge_control.json` (HOCH-200 owned).
- **has**: Syncing from `has_live_project_tracker/data/has_runtime_state.json` (HOCH-200 owned).
- **hasf**: Syncing from `has_live_project_tracker/data/hasf_runtime_state.json`.
- **agents**: Syncing from `has_live_project_tracker/data/helm_agent_registry.json`.
- **adapters**: Syncing from `has_live_project_tracker/data/helm_adapter_registry.json` (HOCH-200 owned).
- **models**: Syncing from `has_live_project_tracker/data/model_capacity_target.json`.
- **freshness**: Syncing from `has_live_project_tracker/data/live_telemetry_freshness.json`.

---

## 3. HOCH-200-Owned Sync Ages & Statuses
All HOCH-200 owned inputs have been verified.
- **Sync age of HOCH-200 sections**: ~0-20 seconds (all verified FRESH).
- **SYNC_STALE sections**: `None` (all telemetry is currently within the 600-second freshness window).

---

## 4. Reducer-Rule Compliance
The aggregator operates strictly as a reducer and not an oracle:
- Never invents a `PASS` status.
- Translates missing sources to `UNKNOWN` and expired sources to `STALE`.
- Zero-tolerance checks (secret scanning, public exposure, fake status flags, signature verification, compute billing, tag integrity) are evaluated dynamically based on underlying evidence files.

---

## 5. Schema Validation Status
- Executed `scripts/verify_control_plane_status_schema.py` which successfully validated that all top-level keys exist and structure complies with version `1.0`. Status: **PASS**.

---

## 6. Expiry Proof Status
- Executed `scripts/prove_control_plane_status_expires.sh`.
- Confirmed that a snapshot with a 2-second max age expires exactly as expected and is detected as expired/stale past its validity window. Status: **PASS**.

---

## 7. Sidecar TTL Behavior
- The sidecar at [tools/has_live_truth_sidecar.py](file:///Users/michaelhoch/hoch_agent_swarm/tools/has_live_truth_sidecar.py) automatically implements a 30-second cache TTL. It rebuilds the contract on the fly using `build_control_plane_status.py` when `/api/live` is called if the cached copy is missing or exceeds TTL.

---

## 8. Snapshot Commit Policy
- Staged and committed the static example template: `has_live_project_tracker/data/examples/control_plane_status.example.json`.
- Ignored the live runtime file `has_live_project_tracker/data/control_plane_status.json` in `.gitignore` to avoid future dirty-tree ambiguity.

---

## 9. Next UI Integration Readiness
- The system is fully ready to present the structured `control_plane_status` schema to the next-phase UI layout without risk of stale-state drift.
