#!/bin/bash
# Stop daemon helper script
if [ -f has_live_project_tracker/data/ag_daemon.pid ]; then
  PID=$(cat has_live_project_tracker/data/ag_daemon.pid)
  echo "Stopping daemon process $PID..."
  kill $PID
  rm has_live_project_tracker/data/ag_daemon.pid
  echo "Daemon stopped."
else
  echo "No PID file found. Checking running processes..."
  pkill -f ag_execution_daemon.py
  echo "Completed."
fi
