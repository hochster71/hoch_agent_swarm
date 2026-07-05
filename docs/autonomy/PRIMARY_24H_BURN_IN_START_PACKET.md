# Primary 24H Burn-In Start Packet

This packet details systemd administration commands, verification checks, and rollbacks for the primary run on `HOCH-200`.

## Selected Host

- **Host Name**: `HOCH-200`
- **Orchestrator**: `systemd`

---

## Administration Commands

### 1. Start Service
```bash
sudo systemctl start hoch-ag-execution-daemon.service
```

### 2. Stop Service
```bash
sudo systemctl stop hoch-ag-execution-daemon.service
```

### 3. Check Service Status
```bash
sudo systemctl status hoch-ag-execution-daemon.service
```

### 4. Stream Daemon Logs (journald)
```bash
journalctl -u hoch-ag-execution-daemon.service -f
```

---

## Verification & Telemetry Checks

### 1. Heartbeat Monitor
```bash
python3 scripts/verify_daemon_heartbeat.py
```

### 2. master Burn-In Validator
```bash
python3 scripts/verify_ag_execution_burn_in.py
```

### 3. E2E Checks (Queue/Proofs/Fencing)
```bash
python3 scripts/verify_ag_execution_queue.py
python3 scripts/verify_ag_execution_proofs.py
python3 scripts/verify_ag_execution_fencing.py
```

---

## Emergency Control & Rollback

### 1. Enable Operator Hold (Emergency Switch)
```bash
python3 scripts/ag_operator_hold.py --enable
```

### 2. Disable Service and Clean Workspace
```bash
sudo systemctl disable hoch-ag-execution-daemon.service
git checkout main && git clean -fdx
```

---

## Approval Status

- **Founder Authorization Signature**: **APPROVED** (Sync'd in approval ledger)
