# Operations Runbook: 24/7 Control & Self-Healing

## 1. Starting the Reliability Stack
To start all services under the HA-lite compose profile:
```bash
bash scripts/start_24_7.sh
```

---

## 2. Stopping or Restarting Services
To stop services safely (maintaining Redis volume logs and SQLite databases):
```bash
bash scripts/stop_24_7.sh
```

To perform a safe rolling restart:
```bash
bash scripts/restart_24_7.sh
```

---

## 3. Telemetry and Health Checks
To run the automated telemetry check manually:
```bash
bash scripts/healthcheck_24_7.sh
```
This script updates the telemetry cockpit state file at `frontend/data/runtime_reliability.json`.

---

## 4. Watchdog & Auto-Healing
The watchdog runs continuously via cron (every minute) or as a system service:
```bash
# Add to crontab for automatic recovery check
* * * * * /bin/bash /Users/michaelhoch/hoch_agent_swarm/scripts/watchdog_24_7.sh >> /var/log/watchdog.log 2>&1
```
If the local API is unresponsive for > 60 seconds, the watchdog automatically issues a restart command for `hoch-app`.

---

## 5. Automated Backups & Restoration
Backups are performed hourly. To execute a manual snapshot:
```bash
bash scripts/backup_state.sh
```

To restore from a backup tarball:
```bash
bash scripts/restore_state.sh <backup_file_path>
```
To dry-run test a restoration:
```bash
bash scripts/restore_state.sh <backup_file_path> true
```
