#!/usr/bin/env bash
# HELM API supervised restart.
#
# Canonical lifecycle owner:
#   launchd -> com.hoch.helm-autoloop -> helm_autoloop.sh -> uvicorn :8770
#
# This script never launches a competing Uvicorn process.

set -uo pipefail

REPO="/Users/michaelhoch/hoch_agent_swarm"
LABEL="com.hoch.helm-autoloop"
DOMAIN="gui/$(id -u)"
SERVICE="${DOMAIN}/${LABEL}"
LOG="/tmp/helm_api.log"

cd "$REPO" || exit 1

listener_pids() {
  lsof -tiTCP:8770 -sTCP:LISTEN 2>/dev/null | sort -u
}

api_up() {
  curl -fsSk \
    -o /dev/null \
    --max-time 5 \
    "https://127.0.0.1:8770/api/v1/helm/wall"
}

echo "▸ HELM supervised API restart"

if ! launchctl print "$SERVICE" >/dev/null 2>&1; then
  echo "  ✗ launchd service is not loaded: $SERVICE"
  echo "    Expected plist:"
  echo "    $HOME/Library/LaunchAgents/${LABEL}.plist"
  exit 1
fi

echo "▸ Current listener:"
before="$(listener_pids || true)"
if [ -n "$before" ]; then
  while IFS= read -r pid; do
    [ -n "$pid" ] || continue
    ps -o pid=,ppid=,etime=,command= -p "$pid" || true
  done <<< "$before"
else
  echo "  · none"
fi

echo "▸ Restarting canonical launchd supervisor..."
if ! launchctl kickstart -k "$SERVICE"; then
  echo "  ✗ launchctl kickstart failed"
  exit 1
fi

if [ -n "$before" ]; then
  echo "▸ Waiting for the old listener to release the port..."
  for _ in $(seq 1 20); do
    current="$(listener_pids || true)"
    still_alive=""
    while IFS= read -r b_pid; do
      [ -n "$b_pid" ] || continue
      if echo "$current" | grep -q -w "$b_pid"; then
        still_alive=1
      fi
    done <<< "$before"
    if [ -z "$still_alive" ]; then
      break
    fi
    sleep 0.5
  done
fi

echo "▸ Waiting for a healthy replacement..."
ok=""
for _ in $(seq 1 30); do
  # Ensure the listener has actually changed (it is not the old pid)
  current="$(listener_pids || true)"
  is_new=""
  if [ -n "$current" ]; then
    is_new=1
    while IFS= read -r b_pid; do
      [ -n "$b_pid" ] || continue
      if echo "$current" | grep -q -w "$b_pid"; then
        is_new=""
      fi
    done <<< "$before"
  fi
  if [ -n "$is_new" ] && api_up; then
    ok=1
    break
  fi
  sleep 1
done

if [ -z "$ok" ]; then
  echo "  ✗ HELM API did not become healthy."
  echo
  echo "Launchd state:"
  launchctl print "$SERVICE" 2>/dev/null | tail -60 || true
  echo
  echo "API log:"
  tail -40 "$LOG" 2>/dev/null || true
  exit 1
fi

after="$(listener_pids || true)"
count="$(printf '%s\n' "$after" | awk 'NF {n++} END {print n+0}')"

echo "▸ Replacement listener:"
while IFS= read -r pid; do
  [ -n "$pid" ] || continue
  ps -o pid=,ppid=,etime=,command= -p "$pid" || true
done <<< "$after"

if [ "$count" -ne 1 ]; then
  echo "  ✗ Expected exactly one :8770 listener; found $count."
  exit 1
fi

cc="$(curl -fsSk -o /dev/null -w '%{http_code}' \
  https://127.0.0.1:8770/council 2>/dev/null)"

cs="$(curl -fsSk -o /dev/null -w '%{http_code}' \
  https://127.0.0.1:8770/api/v1/helm/council/status 2>/dev/null)"

echo
echo "   /council                     -> $cc"
echo "   /api/v1/helm/council/status  -> $cs"

if [ "$cc" != "200" ] || [ "$cs" != "200" ]; then
  echo "  ✗ Route verification failed."
  exit 1
fi

echo
echo "✓ HELM API restarted under its canonical supervisor."
echo "  Listener count: 1"
echo "  Open: https://127.0.0.1:8770/council"
