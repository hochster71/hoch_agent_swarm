#!/usr/bin/env bash
# uninstall_launchd_supervisor.sh - Unloads and deletes the launchd agent and stops the watchdog
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Uninstalling launchd supervisor..."

PLIST_NAME="com.hoch.agent.swarm.runtime.plist"
TARGET_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [ -f "$TARGET_PATH" ]; then
    launchctl unload "$TARGET_PATH" 2>/dev/null || true
    rm -f "$TARGET_PATH"
    echo "[PASS] launchd plist agent removed."
else
    echo "[INFO] No plist agent found to remove."
fi

# Stop watchdog loop
pkill -f watchdog_loop.sh 2>/dev/null || true
echo "[PASS] Watchdog process terminated."
