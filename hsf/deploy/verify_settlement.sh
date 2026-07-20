#!/usr/bin/env bash
# verify_settlement.sh
# Evidence-gated proof of the SETTLED hop for the first $19. Reports SETTLED only when
# Stripe itself marks the funds `available`. NO FAKE GREEN. Read-only: no charge, no money moved.
#
# NO PASTE NEEDED — resolves credentials itself, in this order, and never prints them:
#   1) Stripe CLI (already logged in)     — zero key handling at all
#   2) local secret stores (~/.helm/helm.env, project .env files) — read, never written
#   3) Vercel production env               — pulled to a temp file, shredded immediately
#   4) hidden paste                        — last resort only
#
#   Run:  bash hsf/deploy/verify_settlement.sh            # $19, 30-day window
#         bash hsf/deploy/verify_settlement.sh 1900 60    # cents, days
set -uo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"
say(){ printf '\n\033[1m▸ %s\033[0m\n' "$*"; }
ok(){  printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
warn(){ printf '\033[1;33m! %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

AMOUNT_CENTS="${1:-1900}"
DAYS="${2:-30}"
command -v python3 >/dev/null || die "python3 missing"
if GTE="$(date -v-"${DAYS}"d +%s 2>/dev/null)"; then :; else GTE="$(date -d "-${DAYS} days" +%s)"; fi

BT=""; SRC=""

say "1) Resolve credentials (no paste unless nothing else works)"

# --- 1) Stripe CLI: already logged in, handles no secret key on our side ----------
if command -v stripe >/dev/null 2>&1; then
  if OUT="$(stripe balance_transactions list --live --limit 100 -d "created[gte]=${GTE}" 2>/dev/null)" \
     && printf '%s' "$OUT" | grep -q '"object"'; then
    BT="$OUT"; SRC="Stripe CLI (logged in — no key handled)"; ok "$SRC"
  fi
fi

# --- 2/3/4) Fall back to a key source, then curl ----------------------------------
if [ -z "$BT" ]; then
  KEY=""
  # 2) local secret stores — read only, never created/printed
  for f in "$HOME/.helm/helm.env" "hsf/deploy/.env" "hsf/deploy/.env.local" ".env.local" ".vercel/.env.production.local"; do
    [ -f "$f" ] || continue
    v="$(grep -E '^(export[[:space:]]+)?STRIPE_(SECRET_KEY|LIVE_SECRET_KEY)=' "$f" 2>/dev/null | tail -1 | sed -E 's/^[^=]*=//; s/^["'"'"']//; s/["'"'"']$//')"
    case "$v" in sk_live_*) KEY="$v"; SRC="key from $f (not printed)"; break;; esac
  done
  # 3) Vercel production env — transient pull, shredded immediately
  if [ -z "$KEY" ] && command -v vercel >/dev/null 2>&1; then
    TMP="$(mktemp)"; vercel env pull "$TMP" --environment=production --yes >/dev/null 2>&1 || true
    v="$(grep -E '^STRIPE_SECRET_KEY=' "$TMP" 2>/dev/null | tail -1 | sed -E 's/^[^=]*=//; s/^["'"'"']//; s/["'"'"']$//')"
    command -v shred >/dev/null 2>&1 && shred -u "$TMP" 2>/dev/null || rm -f "$TMP"
    case "$v" in sk_live_*) KEY="$v"; SRC="key from Vercel prod env (pulled to temp, shredded)";; esac
  fi
  # 4) last resort: hidden paste
  if [ -z "$KEY" ]; then
    warn "No stored key found via CLI/helm.env/Vercel."
    printf '  Paste sk_live_ key (hidden, not stored): '; read -rs KEY; echo
    case "$KEY" in sk_live_*) SRC="key from paste";; *) die "no valid key";; esac
  fi
  ok "$SRC"
  BT="$(curl -s -G 'https://api.stripe.com/v1/balance_transactions' \
          --data-urlencode 'limit=100' --data-urlencode "created[gte]=${GTE}" \
          --data-urlencode 'expand[]=data.source' -u "$KEY:")"
  unset KEY
fi

say "2) Settlement verdict (last ${DAYS} days, target \$$(python3 -c "print(${AMOUNT_CENTS}/100)"))"
printf '%s' "$BT" | AMT="$AMOUNT_CENTS" python3 - <<'PY'
import json, os, sys, datetime
raw = sys.stdin.read()
want = int(os.environ.get("AMT", "1900"))
try:
    d = json.loads(raw)
except Exception:
    print("\033[1;31m✗ Could not parse Stripe response.\033[0m"); sys.exit(2)
if isinstance(d, dict) and d.get("error"):
    print("\033[1;31m✗ Stripe error:\033[0m", d["error"].get("message")); sys.exit(2)
txns = d.get("data", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
def when(ts):
    try: return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M UTC")
    except Exception: return str(ts)
charges = [t for t in txns if t.get("type") == "charge"]
matches = [t for t in charges if int(t.get("amount", 0)) == want]
print(f"  charge transactions found: {len(charges)}")
for t in charges[:15]:
    flag = "  <-- MATCH" if int(t.get("amount",0)) == want else ""
    print(f"    ${int(t.get('amount',0))/100:>7.2f} {str(t.get('currency','')).upper():<4} "
          f"status={t.get('status','?'):<9} net=${int(t.get('net',0))/100:.2f} "
          f"{when(t.get('created'))}{flag}")
settled = [t for t in matches if t.get("status") == "available"]
pending = [t for t in matches if t.get("status") == "pending"]
print()
if settled:
    t = settled[0]
    print(f"\033[1;32m✓ SETTLED — Stripe reports ${want/100:.2f} funds AVAILABLE.\033[0m")
    print(f"  net after fees: ${int(t.get('net',0))/100:.2f} {str(t.get('currency','')).upper()} · fee ${int(t.get('fee',0))/100:.2f} · {when(t.get('created'))}")
    print("\n  REVENUE_VERIFIED — first real dollar has settled. This is the honest green.")
    sys.exit(0)
elif pending:
    print("\033[1;33m! CAPTURED, NOT YET SETTLED — charge exists but funds still `pending`.\033[0m")
    print("  State: PAYMENT_AUTHORIZED ✓ → SETTLED pending. No revenue claimed.")
    sys.exit(3)
else:
    print(f"\033[1;33m! No ${want/100:.2f} charge in the window. Widen it: add a day count, e.g. `... {want} 90`.\033[0m")
    sys.exit(4)
PY
RC=$?
say "DONE"; exit $RC
