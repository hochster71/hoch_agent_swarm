#!/usr/bin/env bash
# =============================================================================
# hoch_setup.sh — one-stop login + key setup for the whole HAS build
# =============================================================================
# Part 1  AI BRAINS  : opens each provider's key page, captures the key (hidden), stores
#                      it in .env (chmod 600, git-ignored). FREE Gemini first so the loop
#                      runs at $0. Nothing is echoed, logged, or committed.
# Part 2  SERVICES   : opens the login/console for each GOAL service so you can sign in /
#                      set up (no keys captured there — just gets you to the right page).
#
# Accounts: everything uses michael.b.hoch@gmail.com  EXCEPT Apple = hochster_71@mac.com
# Run in your terminal:   bash scripts/hoch_setup.sh
# =============================================================================
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1
ENV_FILE=".env"

if ! git check-ignore -q "$ENV_FILE" 2>/dev/null; then
  echo "⚠  REFUSING TO RUN: $ENV_FILE is not git-ignored. Add it to .gitignore first."; exit 1
fi

open_url() { command -v open >/dev/null 2>&1 && open "$1" >/dev/null 2>&1 || echo "   open manually: $1"; }
upsert_env() {
  touch "$ENV_FILE"; chmod 600 "$ENV_FILE"
  grep -q "^$1=" "$ENV_FILE" 2>/dev/null && { grep -v "^$1=" "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"; }
  printf '%s=%s\n' "$1" "$2" >> "$ENV_FILE"; chmod 600 "$ENV_FILE"
}

# name | ENV_VAR | key-page URL | prefix | account | instruction
BRAINS=(
  "Google Gemini (FREE)|GOOGLE_API_KEY|https://aistudio.google.com/apikey|AIza|michael.b.hoch@gmail.com|Click 'Create API key'. FREE, no billing. This is your $0 default brain."
  "OpenAI (funded)|OPENAI_API_KEY|https://platform.openai.com/api-keys|sk-|michael.b.hoch@gmail.com|'Create new secret key' — you already have this; press 's' to keep existing."
  "Anthropic (needs credits)|ANTHROPIC_API_KEY|https://console.anthropic.com/settings/keys|sk-ant-|michael.b.hoch@gmail.com|Best for code, but the account needs credits added to actually run. 's' to skip."
  "xAI Grok (optional, cheapest)|XAI_API_KEY|https://console.x.ai/|xai-|michael.b.hoch@gmail.com|Cheapest tokens. Create a key, or 's' to skip."
)

# name | login/console URL | account
SERVICES=(
  "Apple Developer|https://developer.apple.com/account|hochster_71@mac.com"
  "App Store Connect|https://appstoreconnect.apple.com|hochster_71@mac.com"
  "Stripe Dashboard|https://dashboard.stripe.com|michael.b.hoch@gmail.com"
  "GitHub|https://github.com/login|michael.b.hoch@gmail.com"
)

echo "==================== HOCH SETUP ===================="
[ -f "$ENV_FILE" ] && { BK=".env.bak.$(date -u +%Y%m%dT%H%M%SZ)"; git check-ignore -q "$BK" && cp "$ENV_FILE" "$BK" && chmod 600 "$BK" && echo "backup: $BK"; }

echo; echo "──── PART 1: AI BRAINS (keys → .env) ────"
for row in "${BRAINS[@]}"; do
  IFS='|' read -r NAME VAR URL PREFIX ACCT HINT <<< "$row"
  echo; echo "• $NAME   [account: $ACCT]"
  echo "  $HINT"
  open_url "$URL"
  printf "  Paste key (hidden), or 's' to skip: "; read -rs KEY; echo
  [ "$KEY" = "s" ] || [ -z "$KEY" ] && { echo "  ↷ skipped."; continue; }
  if [ "${KEY#"$PREFIX"}" = "$KEY" ]; then
    printf "  ⚠ doesn't start with '%s'. Use anyway? (y/N): " "$PREFIX"; read -r YN
    case "$YN" in [Yy]*) ;; *) echo "  skipped."; continue;; esac
  fi
  upsert_env "$VAR" "$KEY"; echo "  ✅ $VAR stored."
done

echo; echo "──── PART 2: SERVICE LOGINS (opens the page — sign in there) ────"
for row in "${SERVICES[@]}"; do
  IFS='|' read -r NAME URL ACCT <<< "$row"
  echo "• $NAME   → sign in as $ACCT"
  open_url "$URL"
  read -r -p "  press Enter when signed in (or Ctrl-C to stop)… " _ || true
done

echo; echo "──── stored brains ────"
grep -E "^(GOOGLE_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|XAI_API_KEY)=" "$ENV_FILE" 2>/dev/null \
  | sed -E 's/^([A-Z_]+)=.*(.{4})$/\1=…\2/' || echo "(none)"
echo
echo "Done. The loop defaults to FREE Gemini, then falls over to whatever else is keyed."
echo "Tell the orchestrator 'run the loop' and it grinds the queue at \$0 on Gemini."
