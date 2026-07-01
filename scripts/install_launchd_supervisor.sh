#!/usr/bin/env bash
# install_launchd_supervisor.sh - Installs and loads com.hoch.agent.swarm.runtime.plist
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Installing launchd supervisor..."

PLIST_NAME="com.hoch.agent.swarm.runtime.plist"
TARGET_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$TARGET_DIR"

cp "$PLIST_NAME" "$TARGET_DIR/"
chmod 644 "$TARGET_DIR/$PLIST_NAME"

# Force unload before loading to apply changes
launchctl unload "$TARGET_DIR/$PLIST_NAME" 2>/dev/null || true
launchctl load "$TARGET_DIR/$PLIST_NAME"

echo "[PASS] launchd plist agent loaded successfully."

# Kill existing watchdog loops before launching
pkill -f watchdog_loop.sh 2>/dev/null || true

# Start watchdog loop in background
nohup /bin/bash "$PROJECT_ROOT/scripts/watchdog_loop.sh" > /dev/null 2>&1 &
echo "[PASS] Watchdog loop launched in background."
