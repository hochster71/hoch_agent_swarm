# HAS v2 Disaster Recovery Runbook
# Operational Recovery Procedures for the 5 Core Failure Classes

This runbook guides the operator on troubleshooting and resolving failure conditions in the HAS v2 environment.

---

## 🛑 Failure Class 1: Pod Misbehavior
### Symptoms
* Tasks remain in `PENDING` or `RETRY_PENDING` status indefinitely.
* Remote runner logs show continuous loop execution errors.

### Resolution Steps
1. **Check Daemon Logs**: Connect to the VPS and view the log files:
   ```bash
   tail -n 100 /root/hoch_agent_swarm/has_live_project_tracker/data/ag_daemon.log
   ```
2. **Identify Failed Task**: Inspect the task queue to locate the stuck task ID:
   ```bash
   cat /root/hoch_agent_swarm/has_live_project_tracker/data/helm_task_queue.json
   ```
3. **Surgical Recovery**: Force recover the task's state or mark it as `FAILED` to unblock the runner queue.

---

## 🔒 Failure Class 2: Fault Injection / Operator Hold Detected
### Symptoms
* The verifier output flags `[CADENCE WARNING]`, or status changes to `BLOCKED_BY_POLICY`.
* Automation execution is suspended globally.

### Resolution Steps
1. **Verify Operator Hold Status**: Check if the hold is active:
   ```bash
   cat /Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/data/ag_operator_hold.json
   ```
2. **Release the Hold**: Reset the active flag to allow execution:
   ```bash
   python3 scripts/ag_operator_hold.py --disable
   ```
3. **Clear Injection Results**: Clear the injection result ledger:
   ```bash
   echo "" > /Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/data/ag_execution_injection_results.jsonl
   ```

---

## 🔑 Failure Class 3: Stale Lease / Zombie Lock
### Symptoms
* Executor fails to acquire task locks with message `[-] Active lease exists`.
* Process sleep or connection loss has orphaned the lock on a task.

### Resolution Steps
1. **Find Orphaned Lease ID**: Check the lock file:
   ```bash
   cat /Users/michaelhoch/hoch_agent_swarm/has_live_project_tracker/data/ag_execution_lock.json
   ```
2. **Evict the Lock**: Run the Lease Manager to clean up stale locks:
   ```bash
   python3 -c "from scripts.ag_execution_lease_manager import LeaseManager; LeaseManager().check_stale_leases()"
   ```
3. **Forced Recovery**: If a lease remains locked, manually force recovery:
   ```bash
   python3 -c "from scripts.ag_execution_lease_manager import LeaseManager; LeaseManager().recover_failed_lease('<LEASE_ID>')"
   ```

---

## 📁 Failure Class 4: Ledger Corruption / Restore Procedure
### Symptoms
* SQLite errors `database disk image is malformed`.
* Critical corruption of the project tracker state databases.

### Resolution Steps
1. **Locate Latest Verified Backup**:
   ```bash
   ls -la /Users/michaelhoch/hoch_agent_swarm/data/backups/remote_vps/
   ```
2. **Execute Restoration Script**:
   ```bash
   bash deploy/remote-relay/restore.sh /Users/michaelhoch/hoch_agent_swarm/data/backups/remote_vps/hoch_backup_<timestamp>.tar.gz
   ```
3. **Verify Integrity**: Run the database check to confirm restore success:
   ```bash
   python3 -c "import sqlite3; conn = sqlite3.connect('backend/swarm_ledger.db'); print('Tables:', len(conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()))"
   ```

---

## 🧠 Failure Class 5: Control Plane (Brain) Restart
### Symptoms
* Port `8000` is unresponsive or returning HTTP connection refused.
* Cockpit UI shows the control plane as `OFFLINE`.

### Resolution Steps
1. **Identify and Kill Stale Processes**:
   ```bash
   lsof -t -i :8000 | xargs kill -9
   ```
2. **Restart the Backend Core**: Run the FastAPI/Uvicorn server:
   ```bash
   uv run uvicorn backend.main:app --port 8000 --reload
   ```
3. **Check Liveness**: Verify the liveness probe returns HTTP 200:
   ```bash
   curl -I http://127.0.0.1:8000/health
   ```
