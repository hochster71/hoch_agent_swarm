#!/usr/bin/env bash
# HELM dispatch enablement — you paste your key at a HIDDEN prompt in YOUR terminal.
# The key is validated against the provider, stored only in ~/.helm/helm.env (chmod 600,
# outside the repo, gitignored), and NEVER printed, echoed, logged, or sent to Claude.
# After enabling, HELM fires the independent verification (Grok) itself.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVDIR="$HOME/.helm"; ENVFILE="$ENVDIR/helm.env"
mkdir -p "$ENVDIR"; touch "$ENVFILE"; chmod 600 "$ENVFILE"

echo "▸ HELM dispatch enablement"
echo "  Keys are entered hidden, validated with the provider, and stored ONLY in:"
echo "    $ENVFILE   (chmod 600, gitignored, never shown to Claude)"
echo

put_key() {                     # $1=VAR  $2=label  $3=provider
  local var="$1" label="$2" prov="$3" val rc
  printf "  Paste %s (hidden — press Enter to skip): " "$label"
  read -rs val; echo
  [ -z "${val:-}" ] && { echo "    · skipped"; return 0; }

  # Validate BEFORE saving (fail-closed). Response body is discarded.
  case "$prov" in
    xai)       curl -fsS -o /dev/null -H "Authorization: Bearer $val" https://api.x.ai/v1/models; rc=$? ;;
    openai)    curl -fsS -o /dev/null -H "Authorization: Bearer $val" https://api.openai.com/v1/models; rc=$? ;;
    anthropic) curl -fsS -o /dev/null -H "x-api-key: $val" -H "anthropic-version: 2023-06-01" https://api.anthropic.com/v1/models; rc=$? ;;
    *)         rc=0 ;;
  esac
  if [ "$rc" -ne 0 ]; then echo "    ✗ provider rejected the key — NOT saved"; unset val; return 1; fi

  # Rewrite the var without ever echoing the value.
  grep -v "^${var}=" "$ENVFILE" > "$ENVFILE.tmp" 2>/dev/null || true
  mv "$ENVFILE.tmp" "$ENVFILE"; chmod 600 "$ENVFILE"
  printf '%s=%s\n' "$var" "$val" >> "$ENVFILE"
  unset val
  echo "    ✓ validated + stored"
}

put_key XAI_API_KEY       "xAI / Grok key (auditor)"        xai       || { echo "  xAI key required to fire verification. Aborting."; exit 1; }
put_key OPENAI_API_KEY    "OpenAI key (orchestrator)"       openai    || true
put_key ANTHROPIC_API_KEY "Anthropic key (builder)"         anthropic || true

# Master money-gate switch.
grep -v "^HELM_DISPATCH_ENABLED=" "$ENVFILE" > "$ENVFILE.tmp" 2>/dev/null || true
mv "$ENVFILE.tmp" "$ENVFILE"; chmod 600 "$ENVFILE"
echo "HELM_DISPATCH_ENABLED=1" >> "$ENVFILE"

echo
echo "▸ Loading env + confirming (presence only, no values):"
set -a; . "$ENVFILE"; set +a
python3 "$ROOT/scripts/helm_validate_credentials.py" 2>/dev/null | python3 - <<'PY' 2>/dev/null || true
import sys,json
d=json.load(sys.stdin)
print("   configured:", d["configured_count"], "| present:", [r["provider"] for r in d["detail"] if r["present"]])
PY

echo
echo "▸ HELM firing the independent verification (Grok)…"
python3 "$ROOT/scripts/helm_fire_verification.py"
