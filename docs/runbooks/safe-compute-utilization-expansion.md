# Runbook: Safe Compute Utilization Expansion (RC35)

## Purpose
This runbook guides operators on executing safe local jobs using the **Swarm Scheduler** under the rules enforced by the RC34 Usage Budget and Secure Build Guardrails policy.

## Job Dispatch Flow
1. Pending jobs/tasks are stored in the SQLite `backend/swarm_ledger.db`.
2. Run the scheduler:
   ```bash
   python3 backend/mission_control/swarm_scheduler.py
   ```
3. The scheduler maps safe jobs to local shell scripts and runs them using Python's `subprocess` module, capturing stdout/stderr and verifying the exit status.
4. Compliance-safety rules prevent any high-risk task from executing without operator approval (such tasks are marked `WAITING_FOR_APPROVAL`).

## Operational Commands
To trigger the automated verification suite for RC35:
```bash
bash scripts/rc35_compute_expansion_verify.sh
```
