#!/usr/bin/env bash
set -e

UID_NUM="$(id -u)"

for LABEL in \
  com.hoch.daemon \
  com.hoch.brain.cadence \
  com.hoch.phase56.burnin
do
  PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
  if [ -f "$PLIST" ]; then
    echo "bootin gui/${UID_NUM} $PLIST"
    launchctl bootin "gui/${UID_NUM}" "$PLIST" 2>&1 || true
  fi

  echo "enable gui/${UID_NUM}/${LABEL}"
  launchctl enable "gui/${UID_NUM}/${LABEL}" 2>&1 || true
done

echo "Rollback bootin complete. Start labels manually only if explicitly approved."
