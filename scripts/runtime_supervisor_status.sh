#!/usr/bin/env bash
# runtime_supervisor_status.sh - Reports status of supervisor, watchdog, and backend port
set -euo pipefail

echo "=== HAS Supervisor Status Report ==="

if launchctl list | grep -q "com.hoch.agent.swarm.runtime"; then
    echo "Supervisor Service (launchd): LOADED/ACTIVE"
else
    echo "Supervisor Service (launchd): STOPPED"
fi

if pgrep -f watchdog_loop.sh > /dev/null; then
    echo "Watchdog Process: RUNNING"
else
    echo "Watchdog Process: NOT RUNNING"
fi

if nc -z 127.0.0.1 8000; then
    echo "FastAPI Port 8000: OPEN"
else
    echo "FastAPI Port 8000: CLOSED"
fi
