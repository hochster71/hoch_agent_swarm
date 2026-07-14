#!/usr/bin/env bash
# HELM autoloop — the thing that makes 24/7 mean 24/7.
#
# THIS FILE DID NOT EXIST. com.hoch.helm-autoloop.plist has been pointing at it since it was
# installed, failing with exit 127 (command not found) on every single boot, silently. "HELM
# survives reboot" was never true. A supervisor that supervises nothing is worse than none:
# it makes you believe you are covered.
#
# What it keeps alive, forever, without Michael:
#   * the HELM live API (:8770)  -> the PERT wall and the founder dashboard
#   * the Tailscale HTTPS route  -> so the founder gate is reachable from his iPhone
#   * escalation delivery        -> HELM reaches HIM; he stops polling dashboards
#
# It does NOT dispatch work, spend money, or take any FOUNDER_ONLY action. It keeps the lights
# on and it carries messages. Everything else goes through the authority gate.
set -uo pipefail

REPO="/Users/michaelhoch/hoch_agent_swarm"
PY="$REPO/.venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"
LOG="/tmp/hoch-helm-autoloop.log"
INTERVAL="${HELM_AUTOLOOP_INTERVAL:-60}"

cd "$REPO" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

log() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG"; }

api_up() { curl -fsS -o /dev/null --max-time 5 "http://127.0.0.1:8770/api/v1/helm/wall" 2>/dev/null; }

start_api() {
  log "API down -> starting"
  nohup "$PY" -m uvicorn backend.helm_live_api:app --host 0.0.0.0 --port 8770 \
    >> /tmp/helm_api.log 2>&1 &
  sleep 6
  if api_up; then log "API up (pid $!)"; else log "API FAILED to start"; fi
}

ensure_tailscale() {
  # the founder gate must stay reachable from his phone on standard HTTPS
  if ! tailscale serve status 2>/dev/null | grep -q "127.0.0.1:8770"; then
    log "tailscale route missing -> restoring :443 -> 8770"
    tailscale serve --bg --https=443 http://127.0.0.1:8770 >/dev/null 2>&1 || true
  fi
}

log "autoloop start (interval ${INTERVAL}s)"
while true; do
  api_up || start_api
  ensure_tailscale

  # HELM reaches Michael. Deduped, sanitised, credential-free.
  # If it can prove the answer it must not ask -- so only real escalations get here.
  if out="$("$PY" -m backend.council.notify_founder 2>&1)"; then
    n="$(printf '%s' "$out" | grep -o '"notified": [0-9]*' | grep -o '[0-9]*' || echo 0)"
    [ "${n:-0}" -gt 0 ] && log "notified founder of $n escalation(s)"
  else
    log "notify failed: $(printf '%s' "$out" | head -c 120)"
  fi

  sleep "$INTERVAL"
done
