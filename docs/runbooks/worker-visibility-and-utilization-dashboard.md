# Runbook: Worker Visibility & Utilization Dashboard (RC36)

## Purpose
This runbook guides operators on utilizing and monitoring Tailnet worker states and allowed/blocked job types via the PERT cockpit.

## Cockpit Workers Interface
1. Start the cockpit dashboard:
   ```bash
   bash scripts/start_pert_command_center.sh
   ```
2. Open the dashboard at `http://127.0.0.1:8765/`.
3. Locate the **Active Workers** and **Cores/Memory** metric cards at the top.
4. The Workers Table displays each Tailnet node (`michaels-macbook-pro`, `hoch-relay-001`, and `iphone-15-pro-max`), including:
   - Dynamic connection status (ONLINE/OFFLINE parsed from `tailscale status` command).
   - Machine role and Tailscale IP.
   - Core and memory resource capacities.
   - Granular allowed/blocked job permissions to enforce lease-privilege.

## Running Verification Check
To run the automated verification suite for RC36:
```bash
bash scripts/rc36_dashboard_verify.sh
```
