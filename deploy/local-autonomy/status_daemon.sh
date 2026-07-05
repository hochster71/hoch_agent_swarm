#!/bin/bash
# Status daemon helper script
if [ -f has_live_project_tracker/data/ag_daemon.pid ]; then
  PID=$(cat has_live_project_tracker/data/ag_daemon.pid)
  if ps -p $PID > /dev/null; then
    echo "Daemon is running (PID: $PID)"
    exit 0
  fi
fi

# Fallback check
if pgrep -f ag_execution_daemon.py > /dev/null; then
  echo "Daemon is running in background."
  exit 0
fi

echo "Daemon is NOT running."
exit 1
