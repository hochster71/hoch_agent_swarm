# Autonomy Daemon Local Deployment (HOCH-200 / macOS)

This directory contains systemd unit files and launchd plist profiles to deploy `ag_execution_daemon.py` under process supervision.

## systemd (HOCH-200)

1. Copy service unit:
   ```bash
   sudo cp deploy/local-autonomy/hoch-ag-execution-daemon.service /etc/systemd/system/
   ```
2. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable hoch-ag-execution-daemon.service
   sudo systemctl start hoch-ag-execution-daemon.service
   ```

## launchd (macOS Local Venue)

1. Copy plist profile:
   ```bash
   cp deploy/local-autonomy/com.hoch.ag.execution-daemon.plist ~/Library/LaunchAgents/
   ```
2. Load agent:
   ```bash
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.hoch.ag.execution-daemon.plist
   ```
