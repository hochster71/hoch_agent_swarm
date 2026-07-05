#!/bin/bash
# Start daemon helper script
echo "Starting daemon..."
export DAEMON_TEST_MODE=true
export DAEMON_INTERVAL_SECONDS=5
export DAEMON_MAX_CYCLES=5
nohup python3 scripts/ag_execution_daemon.py > has_live_project_tracker/data/ag_daemon.log 2>&1 &
echo $! > has_live_project_tracker/data/ag_daemon.pid
echo "Daemon started in background (PID: $(cat has_live_project_tracker/data/ag_daemon.pid))"
