# Runbook: Goal Completion Forecast & Monetization Readiness (RC38)

## Purpose
This runbook guides operators on monitoring Goal Completion Forecast and Monetization Readiness inside the PERT Command Center cockpit.

## Cockpit Goal Completion & Monetization Interfaces
1. Ensure the PERT cockpit is running:
   ```bash
   bash scripts/start_pert_command_center.sh
   ```
2. Navigate to `http://127.0.0.1:8765/`.
3. Locate the new cards at the bottom:
   - **Goal Completion Forecast**: displays projected minutes remaining, the Remaining Work Ledger, and the Safe Next Actions Queue.
   - **Monetization Readiness Sidecar**: displays readiness score based on required evidence logs, the Evidence Gap Matrix, and compliance guardrails.

## Running Verification Check
To run the automated verification script:
```bash
bash scripts/rc38_goal_readiness_verify.sh
```
