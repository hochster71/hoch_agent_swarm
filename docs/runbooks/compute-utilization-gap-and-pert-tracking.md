# Runbook: Compute Utilization Gap Analysis & PERT Recalibration (RC40)

This runbook documents how to run, verify, and maintain the Compute Utilization and Live PERT Recalibration engine.

## 1. Compute Stack Roles & Capabilities
Approved devices in the Tailscale private-overlay:
- **michaels-macbook-pro** (`100.103.155.4`): Primary control/runtime node. Core/Docker ceilings: 2.0 cores, 4GB RAM.
- **hoch-relay-001** (`100.87.18.15`): Private relay worker. Core/Docker ceilings: 1.0 core, 2GB RAM.
- **iphone-15-pro-max** (`100.102.221.87`): Operator mobile monitor. Strictly monitor-only, does NOT run jobs.

## 2. Dynamic Verification & Recalibration Runs
To run the compute gap analysis audit and regenerate metrics:
```bash
bash scripts/compute_gap_analysis.sh
```

This updates `has_live_project_tracker/data/compute_gap_metrics.json` which is read by `/api/pert/data`.

## 3. Running Verification Suite
To verify the full release candidate gates, including Playwright E2E and telemetry audits:
```bash
bash scripts/rc40_compute_gap_pert_verify.sh
```

## 4. Invariant Policies Enforced
- **Port Security**: Public port `3012` is blocked and closed. All traffic must route through Tailscale.
- **iPhone Policy**: The iPhone node must never appear in dispatch or run queues.
- **Docker ceilings**: Containers must be run with resource limits (`--cpus="2.0" --memory="4g"`).
