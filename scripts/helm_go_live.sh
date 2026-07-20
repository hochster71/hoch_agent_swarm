#!/usr/bin/env bash
# HELM go-live — flip the whole council to READY, WITHOUT re-pasting keys you already set.
#
# Idempotent + presence-aware:
#   · Keys already in ~/.helm/helm.env are KEPT — you are NOT asked to paste them again.
#   · Only a genuinely MISSING provider triggers a hidden paste prompt (Enter to skip).
#   · The founder money-gate (HELM_DISPATCH_ENABLED=1) is set for you.
#   · Every configured key is validated live against its provider (fail-closed).
#   · Finishes by printing per-lane readiness (READY / GATED / BLOCKED).
#
# Secrets are entered hidden, stored ONLY in ~/.helm/helm.env (chmod 600, gitignored),
# and NEVER printed, echoed, logged, or sent to Claude.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVDIR="$HOME/.helm"; ENVFILE="$ENVDIR/helm.env"
mkdir -p "$ENVDIR"; touch "$ENVFILE"; chmod 600 "$ENVFILE"

echo "▸ HELM go-live  ·  env: $ENVFILE"
echo "  Keys already present are kept — you will only be asked for ones that are missing."
echo

has_key() { grep -q "^${1}=" "$ENVFILE" 2>/dev/null; }

validate() {                    # $1=provider $2=value  → rc 0 valid
  local prov="$1" val="$2"
  case "$prov" in
    xai)       curl -fsS -o /dev/null -H "Authorization: Bearer $val" https://api.x.ai/v1/models ;;
    openai)    curl -fsS -o /dev/null -H "Authorization: Bearer $val" https://api.openai.com/v1/models ;;
    anthropic) curl -fsS -o /dev/null -H "x-api-key: $val" -H "anthropic-version: 2023-06-01" https://api.anthropic.com/v1/models ;;
    *)         return 0 ;;
  esac
}

ensure_key() {                  # $1=VAR $2=label $3=provider
  local var="$1" label="$2" prov="$3" val rc
  if has_key "$var"; then
    # Already set — validate what's there, never reprint it.
    val="$(grep "^${var}=" "$ENVFILE" | tail -1 | cut -d= -f2-)"
    if validate "$prov" "$val"; then echo "  ✓ $label — already configured, key valid"
    else echo "  ⚠ $label — configured but provider REJECTED it; re-paste below or Enter to keep"; else_prompt=1; fi
    unset val
    [ "${else_prompt:-0}" = 1 ] || return 0
  fi
  printf "  Paste %s (hidden — Enter to skip): " "$label"
  read -rs val; echo
  [ -z "${val:-}" ] && { echo "    · skipped (lane stays BLOCKED)"; return 0; }
  if ! validate "$prov" "$val"; then echo "    ✗ provider rejected the key — NOT saved"; unset val; return 1; fi
  grep -v "^${var}=" "$ENVFILE" > "$ENVFILE.tmp" 2>/dev/null || true
  mv "$ENVFILE.tmp" "$ENVFILE"; chmod 600 "$ENVFILE"
  printf '%s=%s\n' "$var" "$val" >> "$ENVFILE"; unset val
  echo "    ✓ validated + stored"
}

# Three frontier lanes (all optional — skip any you don't want live yet).
ensure_key OPENAI_API_KEY    "OpenAI key  (Orchestrator / planning)"  openai    || true
ensure_key ANTHROPIC_API_KEY "Anthropic key (Builder / engineering)"  anthropic || true
ensure_key XAI_API_KEY       "xAI / Grok key (Auditor / verification)" xai       || true

# Local brain (private-data lane) — auto-detect Ollama, else accept a URL, else skip.
setup_local() {
  local url val tags
  if has_key HELM_LOCAL_MODEL_URL; then
    url="$(grep '^HELM_LOCAL_MODEL_URL=' "$ENVFILE" | tail -1 | cut -d= -f2-)"
    if curl -fsS -o /dev/null "${url%/}/api/tags"; then echo "  ✓ Local brain — already configured & reachable ($url)"; return 0
    else echo "  ⚠ Local brain — configured URL unreachable ($url); re-enter or Enter to keep"; fi
  else
    # Probe the common Ollama default so you don't have to type anything.
    if curl -fsS -o /dev/null http://localhost:11434/api/tags; then
      url="http://localhost:11434"
      grep -v '^HELM_LOCAL_MODEL_URL=' "$ENVFILE" > "$ENVFILE.tmp" 2>/dev/null || true
      mv "$ENVFILE.tmp" "$ENVFILE"; chmod 600 "$ENVFILE"
      printf 'HELM_LOCAL_MODEL_URL=%s\n' "$url" >> "$ENVFILE"
      echo "  ✓ Local brain — auto-detected Ollama at $url"; return 0
    fi
  fi
  printf "  Local model URL (e.g. http://localhost:11434 — Enter to skip): "
  read -r val
  [ -z "${val:-}" ] && { echo "    · skipped (Local lane stays BLOCKED)"; return 0; }
  if ! curl -fsS -o /dev/null "${val%/}/api/tags"; then echo "    ✗ no local runtime reachable at $val — NOT saved"; return 1; fi
  grep -v '^HELM_LOCAL_MODEL_URL=' "$ENVFILE" > "$ENVFILE.tmp" 2>/dev/null || true
  mv "$ENVFILE.tmp" "$ENVFILE"; chmod 600 "$ENVFILE"
  printf 'HELM_LOCAL_MODEL_URL=%s\n' "$val" >> "$ENVFILE"
  echo "    ✓ reachable + stored"
}
setup_local || true

# Founder money-gate ON (idempotent).
if has_key HELM_DISPATCH_ENABLED; then
  grep -v "^HELM_DISPATCH_ENABLED=" "$ENVFILE" > "$ENVFILE.tmp" 2>/dev/null || true
  mv "$ENVFILE.tmp" "$ENVFILE"; chmod 600 "$ENVFILE"
fi
echo "HELM_DISPATCH_ENABLED=1" >> "$ENVFILE"; chmod 600 "$ENVFILE"
echo
echo "▸ Money-gate: HELM_DISPATCH_ENABLED=1  (council may now fire)"

echo
set -a; . "$ENVFILE"; set +a
if [ -n "${HELM_LOCAL_MODEL_URL:-}" ]; then
  echo "▸ Local brain inventory:"
  cd "$ROOT" && python3 scripts/helm_local_discover.py 2>/dev/null | sed 's/^/   /' || true
  echo
fi
echo "▸ Council readiness (presence only — no key value is ever shown):"
cd "$ROOT" && python3 - <<'PY' 2>/dev/null || echo "  (run from repo root to see live status)"
import sys; sys.path.insert(0,".")
from backend.dispatch.council_router import council_status
d=council_status()
for m in d["members"]:
    tag={"READY":"✓ READY","GATED":"· GATED","BLOCKED_EXTERNAL":"· BLOCKED"}.get(m["status"],m["status"])
    print(f"   {tag:11s} {m['display_name']:12s} {m['role']:12s} ({m['provider']})")
print(f"\n   {d['ready_count']}/{d['total']} lanes READY · money_gate={d['money_gate_enabled']}")
PY

echo
echo "▸ Open the Council Control Plane:  https://127.0.0.1:8770/council"
echo "  Hand it a mission — HELM routes it to the lane that owns it and fires the model live."
