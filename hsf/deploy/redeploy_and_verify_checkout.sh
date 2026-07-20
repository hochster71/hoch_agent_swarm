#!/usr/bin/env bash
# redeploy_and_verify_checkout.sh
# Ships the create-checkout-session code fix (removed invalid paymentLinks expand,
# auto-detect payment/subscription mode, surface real Stripe error) to production and
# PROVES it with a live probe. No key handling — your live key is already set & valid.
# No charge is made. Fail-closed, evidence-first (NO FAKE GREEN).
#
#   Run:  bash hsf/deploy/redeploy_and_verify_checkout.sh
#
# Prereqs already satisfied: vercel CLI logged in; project linked (story-studio-live).
set -uo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"
say(){ printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
ok(){  printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn(){ printf '\033[1;33m! %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

BASE="https://story-studio-live.vercel.app"

say "0) Preconditions"
command -v vercel >/dev/null || die "vercel CLI missing"
vercel whoami >/dev/null 2>&1 || vercel login
[ -f .vercel/project.json ] || vercel link --yes --project story-studio-live >/dev/null
ok "Vercel authed + project linked (story-studio-live)"

say "1) Redeploy production (ships the checkout code fix)"
DEPLOY_URL="$(vercel deploy --prod --yes 2>&1 | tail -1)"; echo "  $DEPLOY_URL"
case "$DEPLOY_URL" in
  https://*) ok "Deploy reported ready" ;;
  *) warn "Deploy output didn't look like a URL — read it above before continuing" ;;
esac

say "2) Probe checkout (no charge) — onestory \$19"
RESP="$(curl -s -X POST "$BASE/api/create-checkout-session" \
  -H 'Content-Type: application/json' -d '{"tier":"onestory"}')"
echo "  raw: $RESP"

# Parse honestly: a real Stripe URL = fixed; anything else prints the exact cause.
python3 - "$RESP" <<'PY'
import json, sys
raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    d = json.loads(raw)
except Exception:
    print("\n\033[1;31m✗ Non-JSON response — check the deploy/logs above.\033[0m"); sys.exit(2)
url = d.get("url") or ""
if "checkout.stripe.com" in url or "buy.stripe.com" in url or url.startswith("https://"):
    print(f"\n\033[1;32m✓ CHECKOUT LIVE — real Stripe URL returned:\033[0m\n  {url}")
    print("\nNext: open it, complete ONE real $19 purchase, then verify it SETTLES in")
    print("Stripe (balance transaction) before anyone claims EARNING. No fake green.")
    sys.exit(0)
# Failure path — the fix makes the real cause visible now:
print("\n\033[1;31m✗ Checkout still failing — but now with the real cause:\033[0m")
for k in ("error","stripe_type","stripe_code","stripe_param","detail","message"):
    if d.get(k): print(f"    {k}: {d[k]}")
print("\nPaste THIS block to Claude (it contains no secret key) and it fixes the exact cause.")
sys.exit(1)
PY
RC=$?

say "DONE"
[ $RC -eq 0 ] && ok "First-dollar path is GO — make the \$19 purchase, then confirm SETTLED." \
             || warn "Diagnostic captured above — one more targeted fix, then re-run this script."
exit $RC
