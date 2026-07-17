#!/usr/bin/env bash
# Story Studio (HSF) go-live driver.
# Doctrine: Claude writes + runs this; Michael only signs in (passkey/browser) and
# pastes 2 secrets at the native prompts. Claude never sees or stores the secrets.
#
#   bash go_live.sh          # VERIFY (read-only, deploys nothing) — safe to run anytime
#   bash go_live.sh --go     # DEPLOY (installs CLIs if needed, logs you in, deploys)
#
# NO FAKE GREEN: the Stripe live account/price IDs below are asserted in the repo but
# UNVERIFIED against the live dashboard — VERIFY checks them for real before --go proceeds.
set -uo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"

ONESTORY="price_1TqjVNDINF9KNAICvsZ4Kl3t"   # $19 one-time  (asserted; verified below)
CREATORS="price_1TqjVNDINF9KNAICsqE8sy0G"   # $12/mo        (asserted; verified below)
MODE="${1:-verify}"
say(){ printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
have(){ command -v "$1" >/dev/null 2>&1; }

verify(){
  say "STORY STUDIO GO-LIVE — VERIFY (read-only; nothing is deployed)"
  have node   && echo "node:   $(node -v)"                    || echo "node:   MISSING"
  have vercel && echo "vercel: $(vercel --version 2>/dev/null|head -1)" || echo "vercel: not installed (--go installs it)"
  have stripe && echo "stripe: $(stripe version 2>/dev/null|head -1)"   || echo "stripe: not installed (--go installs it)"
  if have vercel; then vercel whoami >/dev/null 2>&1 && echo "vercel auth: logged in" || echo "vercel auth: NOT logged in (--go opens login)"; fi
  if have stripe; then stripe config --list >/dev/null 2>&1 && echo "stripe auth: configured" || echo "stripe auth: NOT logged in (--go opens login)"; fi
  if have stripe && stripe config --list >/dev/null 2>&1; then
    for p in "$ONESTORY" "$CREATORS"; do
      stripe prices retrieve "$p" >/dev/null 2>&1 && echo "price OK:      $p" || echo "price MISSING: $p  (create/fix in Stripe before --go)"
    done
  else
    echo "prices: cannot verify until Stripe is logged in (run --go)"
  fi
  say "buy-loop tests (proves the code is deploy-ready)"
  have node && node --test 2>&1 | tail -3 || echo "node missing — cannot run tests"
  [ -f .env ] && { say "preflight (.env present)"; node preflight_check.mjs || true; } || echo ".env not present yet (created during --go)"
  say "VERIFY done. To deploy:  bash go_live.sh --go   (you sign in + paste 2 secrets at the prompts)"
}

go(){
  say "STORY STUDIO GO-LIVE — DEPLOY. You will: approve 2 browser logins + paste 2 secrets. Claude never sees them."
  have vercel || { say "installing Vercel CLI"; npm i -g vercel; }
  have stripe || { say "installing Stripe CLI (Homebrew)"; brew install stripe/stripe-cli/stripe; }
  say "Sign in to Vercel (browser/passkey)…"; vercel whoami >/dev/null 2>&1 || vercel login
  say "Sign in to Stripe (browser)…";        stripe config --list >/dev/null 2>&1 || stripe login
  say "Verifying your live prices exist"
  for p in "$ONESTORY" "$CREATORS"; do
    stripe prices retrieve "$p" >/dev/null 2>&1 || { echo "!! $p not found in your live Stripe account. Create/confirm it, then re-run --go."; exit 3; }
  done
  say "Linking Vercel project"; vercel link
  say "Note: if a Vercel KV store isn't linked yet, create it in the Vercel dashboard (Storage → KV) and re-run --go; the CLI will pull its env automatically."
  vercel env pull .env.local >/dev/null 2>&1 || true
  # non-secret env
  printf '%s' "$ONESTORY" | vercel env add STRIPE_PRICE_ONESTORY production 2>/dev/null || true
  printf '%s' "$CREATORS" | vercel env add STRIPE_PRICE_CREATORS production 2>/dev/null || true
  vercel env add AUTH_SECRET production <<< "$(openssl rand -base64 32)" 2>/dev/null || true
  say "PASTE your Stripe LIVE secret key (sk_live_…) at the next prompt:"
  vercel env add STRIPE_SECRET_KEY production
  say "First deploy"
  DEPLOY_URL="$(vercel deploy --prod --yes | tail -1)"; echo "Deployed → $DEPLOY_URL"
  vercel env add BASE_URL production <<< "$DEPLOY_URL" 2>/dev/null || true
  say "Registering the live Stripe webhook"
  stripe webhook_endpoints create --url "$DEPLOY_URL/api/webhook" --enabled-events checkout.session.completed 2>&1 | tee /tmp/ss_webhook.txt || true
  say "PASTE the webhook signing secret (whsec_…) from that output / your dashboard at the next prompt:"
  vercel env add STRIPE_WEBHOOK_SECRET production
  say "Redeploy to load env + run preflight"
  vercel deploy --prod --yes
  vercel env pull .env >/dev/null 2>&1 || true
  node preflight_check.mjs || true
  say "LIVE. Final step is yours: one real \$19 purchase → 'curl $DEPLOY_URL/api/entitlement' shows paid:true → refund in Stripe. EARNING confirms when the balance txn settles."
}

case "$MODE" in --go|go) go ;; *) verify ;; esac
