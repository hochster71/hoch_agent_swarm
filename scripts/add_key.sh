#!/usr/bin/env bash
# add_key.sh ENV_VAR URL [PREFIX] — open the key page in SAFARI, capture ONE key (hidden)
# into .env. Use when you just need to add/replace a single provider (no full re-run).
#   e.g.  bash scripts/add_key.sh ANTHROPIC_API_KEY https://console.anthropic.com/settings/keys sk-ant-
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
VAR="${1:?usage: add_key.sh ENV_VAR URL [PREFIX]}"
URL="${2:?usage: add_key.sh ENV_VAR URL [PREFIX]}"
PREFIX="${3:-}"
ENV_FILE=".env"

git check-ignore -q "$ENV_FILE" 2>/dev/null || { echo "⚠ .env is not git-ignored; aborting."; exit 1; }
command -v open >/dev/null 2>&1 && open -a Safari "$URL" >/dev/null 2>&1 || echo "open manually: $URL"

printf "Paste %s (hidden), or Enter to cancel: " "$VAR"
read -rs KEY; echo
[ -z "$KEY" ] && { echo "cancelled — nothing stored."; exit 0; }
if [ -n "$PREFIX" ] && [ "${KEY#"$PREFIX"}" = "$KEY" ]; then
  printf "⚠ doesn't start with '%s'. Use anyway? (y/N): " "$PREFIX"; read -r YN
  case "$YN" in [Yy]*) ;; *) echo "aborted."; exit 0;; esac
fi
touch "$ENV_FILE"; chmod 600 "$ENV_FILE"
grep -q "^$VAR=" "$ENV_FILE" 2>/dev/null && { grep -v "^$VAR=" "$ENV_FILE" > "$ENV_FILE.t" && mv "$ENV_FILE.t" "$ENV_FILE"; }
printf '%s=%s\n' "$VAR" "$KEY" >> "$ENV_FILE"; chmod 600 "$ENV_FILE"
echo "✅ $VAR stored (ends …${KEY: -4})."
