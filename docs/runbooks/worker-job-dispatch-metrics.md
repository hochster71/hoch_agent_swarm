# Runbook: Worker Job Dispatch & Goal Contribution Metrics (RC37)

## Purpose
This runbook guides operators on utilizing the new Job Dispatch & Goal Contribution Metrics card inside the PERT cockpit.

## Cockpit Job Dispatch Interface
1. Verify the cockpit dashboard is active:
   ```bash
   bash scripts/start_pert_command_center.sh
   ```
2. Open `http://127.0.0.1:8765/`.
3. Scroll to the bottom to view the **Job Dispatch & Goal Contribution** card.
4. The table displays the latest 10 executed tasks dispatched to workers, showing:
   - Worker Node (e.g. `Live Tracker Runtime Agent`, `michaels-macbook-pro`, `hoch-relay-001`).
   - Task / Command name and exact shell invocation statement.
   - Live execution status (Green `COMPLETED` or Red `FAILED`).
   - Goal Impact percentage score contribution (e.g. `+0.5%` or `+0.3%`).

## Running Verification Check
To run the automated verification script:
```bash
bash scripts/rc37_dispatch_verify.sh
```
