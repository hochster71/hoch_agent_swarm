# Real 24H Burn-In Launch Packet

This packet details the commands, preflight verifications, and rollback steps for the 24h burn-in launch on `HOCH-200`.

## Target Host

- **Selected Host**: `HOCH-200`
- **Orchestration Harness**: systemd (`hoch-ag-execution-daemon.service`)

---

## Command Registry

### 1. Preflight Verification
Verify launch readiness before starting the daemon:
```bash
python3 scripts/verify_burn_in_launch_readiness.py
python3 scripts/verify_private_first_doctrine.py
```

### 2. Daemon Launch (Start)
Start the 24h burn-in daemon wrapped under `caffeinate` to prevent system sleep:
```bash
caffeinate -i -s -d python3 scripts/ag_execution_daemon.py
```

### 3. Heartbeat & Queue Audits
Observe daemon heartbeats and task queues:
```bash
python3 scripts/verify_daemon_heartbeat.py
python3 scripts/verify_ag_execution_queue.py
```

### 4. Lease Fencing & Proof Audits
Verify lease token monotonicity and task proof matchings:
```bash
python3 scripts/verify_ag_execution_fencing.py
python3 scripts/verify_ag_execution_proofs.py
```

### 5. master Burn-In Validator
Run the validator script to assess elapsed wall-clock hours:
```bash
python3 scripts/verify_ag_execution_burn_in.py
```

### 6. Emergency Hold & Stop Commands
Trigger an operator hold to pause execution:
```bash
python3 scripts/ag_operator_hold.py --hold
```

### 7. Rollback
In case of critical failures, clean target workspace:
```bash
git checkout main && git clean -fdx
```

---

## Approval Status

- **Status**: **PENDING_FOUNDER_APPROVAL**
- **Approval Signature Required**: Michael (founder authority)
