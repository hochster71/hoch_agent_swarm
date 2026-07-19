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

load_env_safely() {
  local env_file="$1"
  [ -f "$env_file" ] || return 0

  local line_num=0
  local has_error=""

  while IFS= read -r line || [ -n "$line" ]; do
    line_num=$((line_num + 1))
    
    # Trim leading/trailing whitespace
    local trimmed
    trimmed=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

    # Ignore empty lines and comments
    [ -z "$trimmed" ] && continue
    if [[ "$trimmed" =~ ^# ]]; then
      continue
    fi

    # Check key format
    if [[ ! "$trimmed" =~ ^(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*= ]]; then
      log "ERROR: Invalid assignment format at line $line_num in $env_file (keys must be valid shell identifiers)"
      has_error=1
      continue
    fi

    # Check for executable constructs (subshells, operators, inline comments)
    local val_part="${trimmed#*=}"
    if echo "$val_part" | grep -q -E '\$\(|`|&&|\|\||[;|<>#]'; then
      log "ERROR: Unsafe construct detected at line $line_num in $env_file (contains subshell, operator, or inline comment)"
      has_error=1
      continue
    fi
  done < "$env_file"

  if [ -n "$has_error" ]; then
    log "ERROR: $env_file failed syntax validation. Skipping to protect supervisor."
    return 1
  fi

  # Safe sourcing (since it contains only strict name=value assignments)
  # shellcheck disable=SC1090
  . "$env_file"
  return 0
}

api_up() { curl -fsSk -o /dev/null --max-time 5 "https://127.0.0.1:8770/api/v1/helm/wall" 2>/dev/null; }

start_api() {
  log "API down -> starting"
  # Load gitignored voice/secrets env so ElevenLabs survives autoloop restarts
  set -a
  load_env_safely "$REPO/.env"
  load_env_safely "$REPO/.env.elevenlabs"
  load_env_safely "$HOME/.helm/helm.env"
  set +a
  # ZERO-TRUST CUTOVER (Option A, founder-approved DEC-ZT-CUTOVER-001):
  #   - bind 127.0.0.1 (loopback only) instead of 0.0.0.0      -> SC-7 / AC-4
  #   - terminate TLS with the self-signed dev cert            -> SC-8
  # Read-auth (AC-3/IA-2) is intentionally DEFERRED until the console JS carries
  # the read token; Tailscale (tailnet-only) is the authenticated external ingress.
  HELM_CERT="$HOME/.helm/dev_certs/helm_dev_cert.pem"
  HELM_KEY="$HOME/.helm/dev_certs/helm_dev_key.pem"
  nohup "$PY" -m uvicorn backend.helm_live_api:app --host 127.0.0.1 --port 8770 \
    --ssl-certfile "$HELM_CERT" --ssl-keyfile "$HELM_KEY" \
    >> /tmp/helm_api.log 2>&1 &
  sleep 6
  if api_up; then log "API up (pid $!)"; else log "API FAILED to start"; fi
}

ensure_tailscale() {
  # the founder gate must stay reachable from his phone on standard HTTPS
  if ! tailscale serve status 2>/dev/null | grep -q "127.0.0.1:8770"; then
    log "tailscale route missing -> restoring :443 -> 8770"
    tailscale serve --bg --https=443 https+insecure://127.0.0.1:8770 >/dev/null 2>&1 || true
  fi
}

# HELM builds ITSELF to GOAL — hands-off. While GOAL_HELM is not DONE, keep the autonomous
# build-to-GOAL runner alive (singleton). It loops the council (Builder → Grok audit → debug
# swarm) until GOAL or a genuine founder decision. Founder never re-runs anything. Guarded,
# cost-capped, ledgered; Builder on the flat Max plan (ANTHROPIC_API_KEY unset). Stops itself
# at GOAL. Set HELM_BUILD_TO_GOAL=0 to disable.
GOAL_PIDFILE="/tmp/helm_goal_runner.pid"
drive_to_goal() {
  [ "${HELM_BUILD_TO_GOAL:-1}" = "0" ] && return
  # done? GOAL_HELM DONE -> stop driving (no relaunch)
  if grep -q '"GOAL_HELM": *"DONE"' "$REPO/coordination/goal/helm_pert.json" 2>/dev/null; then return; fi
  # singleton: a runner already alive? leave it
  if [ -f "$GOAL_PIDFILE" ] && kill -0 "$(cat "$GOAL_PIDFILE" 2>/dev/null)" 2>/dev/null; then return; fi
  log "GOAL not reached -> launching autonomous build-to-GOAL runner (--auto)"
  ( set -a
    load_env_safely "$HOME/.helm/helm.env"
    load_env_safely "$REPO/.env"
    set +a
    unset ANTHROPIC_API_KEY   # Builder uses the flat Max plan, not per-token API billing
    cd "$REPO"
    nohup "$PY" "$REPO/scripts/helm_goal_runner.py" --auto >> /tmp/helm_build_to_goal.log 2>&1 &
    echo $! > "$GOAL_PIDFILE" )
}

log "autoloop start (interval ${INTERVAL}s)"
# Allow any terminating processes from a previous supervisor coalition to release ports
sleep 3

while true; do
  api_up || start_api
  ensure_tailscale
  drive_to_goal   # HELM builds itself to GOAL, hands-off, until done

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
