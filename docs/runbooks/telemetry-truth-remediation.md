# Runbook: Telemetry Truth Remediation (RC39)

## Purpose
This runbook guides operators on verifying Telemetry Provenance and the "No Fake Telemetry Audit" system inside the PERT Command Center cockpit.

## Cockpit Provenance Tooltips & Schema
1. Ensure the PERT cockpit is running:
   ```bash
   bash scripts/start_pert_command_center.sh
   ```
2. Navigate to `http://127.0.0.1:8765/`.
3. Hover your cursor over any major telemetry status or score widget (e.g. Goal Completion, Tests Passing/Failing, Evidence Coverage, Accountability Score, Tailnet Worker Status, or compliance flags).
4. A tooltip will appear showing the provenance details:
   - **Source**: the underlying sensor, file, database, or API queried.
   - **Freshness**: elapsed time in seconds since the last measurement.
   - **Confidence**: high/medium/low trust indicator.

## Running Verification Check
To run the automated verification script:
```bash
bash scripts/rc39_telemetry_truth_verify.sh
```
