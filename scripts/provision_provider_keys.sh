#!/usr/bin/env bash
# =============================================================================
# provision_provider_keys.sh  —  R1: guided provider API-key provisioning
# =============================================================================
# FOUNDER-ONLY. Un-gates Rung-2 provider execution (the first domino to /GOAL).
#
# What it does, one service at a time:
#   1. Opens the service login + the EXACT "create new API key" page in your browser.
#   2. Waits for you to paste the key (hidden input — never shown or logged).
#   3. Validates the key prefix, then writes it to .env (chmod 600, git-ignored).
#   4. Repeats for the next service until all are provisioned.
#
# No key is ever echoed, committed, or sent anywhere. Storage is local .env only.
# Run it in your own terminal:   bash scripts/provision_provider_keys.sh
# =============================================================================
set -uo pipefail

# Always operate from the repo root (so .env is the one the backend reads)
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
ENV_FILE=".env"

# Safety: refuse to run if .env is not git-ignored (prevents committing secrets)
if git check-ignore -q "$ENV_FILE" 2>/dev/null; then :; else
  echo "⚠  REFUSING TO RUN: $ENV_FILE is not git-ignored — add it to .gitignore first so keys can't be committed."
  exit 1
fi

# service | ENV_VAR | create-key URL | expected prefix | on-page instruction
SERVICES=(
  "OpenAI|OPENAI_API_KEY|https://platform.openai.com/api-keys|sk-|Log in, click 'Create new secret key', name it hoch-r1, copy the value."
  "Anthropic|ANTHROPIC_API_KEY|https://console.anthropic.com/settings/keys|sk-ant-|Log in, click 'Create Key', name it hoch-r1, copy the value."
)

open_url() {
  if command -v open >/dev/null 2>&1; then open "$1" >/dev/null 2>&1
  else echo "   (open this URL manually): $1"; fi
}

upsert_env() {  # $1=KEY_NAME  $2=VALUE  — idempotent replace-or-append, perms locked
  touch "$ENV_FILE"; chmod 600 "$ENV_FILE"
  if grep -q "^$1=" "$ENV_FILE" 2>/dev/null; then
    grep -v "^$1=" "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
  fi
  printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"
  chmod 600 "$ENV_FILE"
}

echo "==============================================================="
echo " R1 — Provider API key provisioning (OpenAI + Anthropic)"
echo " Keys are stored ONLY in $ENV_FILE (chmod 600, git-ignored)."
echo "==============================================================="
if [ -f "$ENV_FILE" ]; then
  BK=".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"; cp "$ENV_FILE" "$BK"; chmod 600 "$BK"
  echo "Backup of current .env → $BK"
fi

TOTAL=${#SERVICES[@]}; i=0; DONE=0
for row in "${SERVICES[@]}"; do
  i=$((i+1))
  IFS='|' read -r NAME VAR URL PREFIX HINT <<< "$row"
  echo
  echo "──────────── [$i/$TOTAL] $NAME ────────────"
  echo "Opening $NAME key page (log in if prompted)…"
  open_url "$URL"
  echo "   → $HINT"
  while true; do
    printf "   Paste %s key (hidden), or type 's' to skip: " "$NAME"
    read -rs KEY; echo
    if [ "$KEY" = "s" ]; then echo "   ↷ skipped $NAME (you can rerun later)."; break; fi
    if [ -z "$KEY" ]; then echo "   empty — try again."; continue; fi
    if [ "${KEY#"$PREFIX"}" = "$KEY" ]; then
      printf "   ⚠ key doesn't start with '%s'. Use it anyway? (y/N): " "$PREFIX"
      read -r YN; case "$YN" in [Yy]*) ;; *) echo "   re-enter."; continue;; esac
    fi
    upsert_env "$VAR" "$KEY"
    echo "   ✅ $VAR stored (ends …${KEY: -4})."
    DONE=$((DONE+1))
    break
  done
done

echo
echo "──────────── result ────────────"
grep -E "^(OPENAI_API_KEY|ANTHROPIC_API_KEY)=" "$ENV_FILE" 2>/dev/null \
  | sed -E 's/^([A-Z_]+)=.*(.{4})$/\1=…\2/' || echo "(none stored)"
echo
echo "$DONE / $TOTAL keys provisioned."
if [ "$DONE" -eq "$TOTAL" ]; then
  echo
  echo "R1 COMPLETE. Next steps to activate provider execution:"
  echo "  1) Load the keys into the backend:"
  echo "       launchctl kickstart -k gui/\$(id -u)/com.hoch.api.server"
  echo "  2) (DOORSTEP revenue gate — do this consciously when ready to let real"
  echo "      provider missions run) flip allow_provider_api_calls to true in:"
  echo "       has_live_project_tracker/data/orchestration_bridge_control.json"
  echo "  3) Re-run the change board:  python3 scripts/baseline_guard.py"
else
  echo "Some keys skipped — rerun this script to finish."
fi
