#!/usr/bin/env bash
# rotate_stripe_and_redeploy.sh
# Story Studio (story-studio-live) is fully deployed and live EXCEPT the Stripe live
# secret key expired ("Expired API Key ...rrfU" in the Vercel logs). This script does
# 100% of the fix and pauses for exactly ONE thing only you can do: paste a fresh
# live secret key. Claude never sees it — you paste it at a silent local prompt; it
# is never printed, never written to disk, and cleared from memory at the end.
#
#   Run:  bash hsf/deploy/rotate_stripe_and_redeploy.sh
#
# Prereqs already satisfied: vercel + stripe CLIs are logged in; project is linked
# (.vercel/project.json -> story-studio-live). No other logins needed.
set -uo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"
say(){ printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
ok(){ printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

ONESTORY="price_1TqjVNDINF9KNAICvsZ4Kl3t"   # verified live
CREATORS="price_1TqjVNDINF9KNAICsqE8sy0G"   # verified live
BASE="https://story-studio-live.vercel.app"

say "0) Preconditions"
command -v vercel >/dev/null || die "vercel CLI missing"
vercel whoami >/dev/null 2>&1 || vercel login
[ -f .vercel/project.json ] || vercel link --yes --project story-studio-live >/dev/null
ok "Vercel authed + project linked (story-studio-live)"

say "1) Generate a fresh LIVE secret key"
echo "  Opening your Stripe API keys page. Create/reveal a LIVE secret key (starts sk_live_)."
open "https://dashboard.stripe.com/apikeys" 2>/dev/null || echo "  -> https://dashboard.stripe.com/apikeys"

say "2) Paste the new live secret key (input hidden; never shown, logged, or saved)"
printf "  sk_live_ key: "
read -rs NEWKEY; echo
[ -n "${NEWKEY:-}" ] || die "no key entered"
case "$NEWKEY" in
  sk_live_*) : ;;
  sk_test_*) die "that's a TEST key (sk_test_). Paste a LIVE key (sk_live_)." ;;
  rk_live_*) die "that's a RESTRICTED key (rk_live_). The app needs a standard secret key (sk_live_)." ;;
  *) die "that doesn't look like a Stripe secret key (expected sk_live_...)." ;;
esac

say "2b) Validate the key against Stripe BEFORE deploying (fail-closed)"
if ! stripe prices retrieve "$ONESTORY" --api-key "$NEWKEY" >/dev/null 2>&1; then
  NEWKEY=""; die "the pasted key could not read the live price $ONESTORY — it may be wrong/restricted/expired. Nothing changed."
fi
ok "Key is valid and can see the live \$19 price."

say "3) Write env vars to Vercel production (key value piped, not echoed)"
setenv(){ # NAME VALUE
  vercel env rm "$1" production -y >/dev/null 2>&1 || true
  printf '%s' "$2" | vercel env add "$1" production >/dev/null 2>&1 && ok "set $1"
}
setenv STRIPE_SECRET_KEY "$NEWKEY"
setenv STRIPE_PRICE_ONESTORY "$ONESTORY"
setenv STRIPE_PRICE_CREATORS "$CREATORS"
setenv BASE_URL "$BASE"
NEWKEY=""   # scrub from memory

say "4) Redeploy production"
DEPLOY_URL="$(vercel deploy --prod --yes 2>&1 | tail -1)"; echo "  $DEPLOY_URL"

say "5) Verify the checkout now creates a REAL Stripe session (no charge)"
sleep 4
RESP="$(curl -s -X POST "$BASE/api/create-checkout-session" -H 'Content-Type: application/json' -d '{"tier":"onestory"}')"
if echo "$RESP" | grep -qiE 'checkout.stripe.com|"url"\s*:\s*"https'; then
  ok "CHECKOUT LIVE — a stranger can now buy. Story Studio is SELLABLE."
  echo "$RESP" | grep -oE 'https://checkout.stripe.com[^"]*' | head -1
elif echo "$RESP" | grep -qi 'Expired API Key'; then
  die "still 'Expired API Key' — the env may not have propagated yet; re-run in ~30s, or the key is already expired."
else
  echo "  response: $(echo "$RESP" | head -c 300)"
  echo "  (if this isn't a Stripe URL, tell Claude and paste this line — do NOT paste your key.)"
fi
say "DONE. First real \$19 purchase → verify it SETTLES in Stripe before claiming EARNING (no fake green)."
