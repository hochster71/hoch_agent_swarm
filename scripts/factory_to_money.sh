#!/usr/bin/env bash
# factory_to_money.sh — the ONE reusable "factory build -> first settled dollar" pipeline.
#
# WHY THIS EXISTS (2026-07-16): Story Studio's checkout was made live by a bespoke
# story_studio_finish.sh (Keychain key -> idempotent Stripe price in the key's own
# account -> Vercel env -> guarded deploy -> checkout smoke-test). This script GENERALIZES
# that proven pattern so ANY product in coordination/products/products.json can be driven
# to a live, sellable checkout by the SAME guard-railed path — never a per-product one-off.
#
# It is the money layer wrapped around scripts/factory_deploy.sh (the deploy layer):
#   this script  = Keychain secret + idempotent Stripe product/price + Vercel env
#   factory_deploy = source-match guard + preview -> smoke -> promote -> auto-rollback
# The deploy therefore ALWAYS rides the one guard-railed pipeline (doctrine rule 4).
#
# USAGE:
#   scripts/factory_to_money.sh <product_id> [--plan|--go] [--source <dir>]
#
#   (default / --plan)  READ-ONLY DRY RUN. Resolves the product, runs the source-match
#                       guard, reports whether the per-product Keychain secret exists,
#                       what Stripe prices it WOULD create/reuse, what Vercel env it WOULD
#                       set, and what the deploy layer WOULD do. Pastes nothing, writes
#                       nothing, charges nothing, deploys NOTHING.
#   --go                ARM. Reads (or one-time-paste-captures) the live Stripe key from
#                       the macOS Keychain, validates it directly against api.stripe.com,
#                       idempotently ensures the product's Stripe product+prices exist IN
#                       THAT KEY'S OWN ACCOUNT, sets Vercel prod env, then hands off to
#                       factory_deploy.sh --go (preview -> checkout smoke -> promote ->
#                       auto-rollback). Requires the founder to be signed into Vercel.
#   --source <dir>      Override the folder checked against source_of_truth (default $PWD).
#
# SAFETY DOCTRINE (CLAUDE.md SAFE-AUTONOMY):
#   * Default is read-only; every irreversible step prints an [ACT] line first.
#   * The Stripe secret is NEVER printed, echoed, hardcoded, or written to a repo file. It
#     lives ONLY in the macOS Keychain (the OS secret vault) and in shell memory, scrubbed
#     at exit. Paste happens at a native HIDDEN prompt (read -rs) — Claude never sees it.
#   * The key is validated by curl DIRECTLY against api.stripe.com (GET /v1/account), NOT
#     via a CLI flag that a wrapper could ignore. Fail-closed: a bad key aborts before any
#     price create / env set / deploy.
#   * Prices are created idempotently via stable lookup_keys, so re-runs REUSE, never dup.
#   * NO FAKE GREEN: only real evidence (a retrievable price, a real checkout.stripe.com /
#     buy.stripe.com URL) is reported as done.
#
set -uo pipefail

# ---------------------------------------------------------------------------
# constants / helpers
# ---------------------------------------------------------------------------
REPO_ROOT="/Users/michaelhoch/hoch_agent_swarm"
MANIFEST="${FACTORY_PRODUCTS_MANIFEST:-$REPO_ROOT/coordination/products/products.json}"
FACTORY_DEPLOY="$REPO_ROOT/scripts/factory_deploy.sh"
STRIPE_API="https://api.stripe.com/v1"

log()  { printf '%s\n'  "$*"; }
act()  { printf '[ACT] %s\n' "$*"; }
die()  { printf '\n[ABORT] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }
fail() { printf '[FAIL] %s\n' "$*" >&2; }
plan() { printf '[PLAN] %s\n' "$*"; }
step() { printf '\n=== %s ===\n' "$*"; }

# canonicalize a path (resolve symlinks/.., no trailing slash); relative -> repo root.
canon() {
  local p="$1"
  case "$p" in /*) : ;; *) p="$REPO_ROOT/$p" ;; esac
  if command -v realpath >/dev/null 2>&1; then
    realpath -m -- "$p" 2>/dev/null || printf '%s' "$p"
  else
    ( cd "$p" 2>/dev/null && pwd -P ) || printf '%s' "${p%/}"
  fi
}

# lowercase helper (portable; avoids bash4 ${x,,})
lc() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
uc() { printf '%s' "$1" | tr '[:lower:]' '[:upper:]'; }

# ---------------------------------------------------------------------------
# arg parsing
# ---------------------------------------------------------------------------
PRODUCT_ID=""
MODE="plan"          # plan | go
SOURCE_DIR="$PWD"

while [ $# -gt 0 ]; do
  case "$1" in
    --plan)     MODE="plan"; shift ;;
    --go)       MODE="go"; shift ;;
    --source)   SOURCE_DIR="${2:-}"; [ -n "$SOURCE_DIR" ] || die "--source needs a directory"; shift 2 ;;
    --source=*) SOURCE_DIR="${1#*=}"; shift ;;
    -h|--help)  sed -n '2,45p' "$0"; exit 0 ;;
    -*)         die "unknown flag: $1" ;;
    *)          [ -z "$PRODUCT_ID" ] || die "unexpected extra arg: $1"; PRODUCT_ID="$1"; shift ;;
  esac
done

[ -n "$PRODUCT_ID" ] || die "usage: factory_to_money.sh <product_id> [--plan|--go] [--source <dir>]"
command -v jq   >/dev/null 2>&1 || die "jq is required but not on PATH"
command -v curl >/dev/null 2>&1 || die "curl is required but not on PATH"

MODE_LABEL="PLAN (read-only; pastes nothing, deploys nothing, charges nothing)"
[ "$MODE" = "go" ] && MODE_LABEL="GO (armed: Keychain key -> Stripe prices -> Vercel env -> guarded deploy)"

step "factory_to_money — $PRODUCT_ID"
log  "manifest : $MANIFEST"
log  "mode     : $MODE_LABEL"
log  "source   : $SOURCE_DIR"

# ---------------------------------------------------------------------------
# 1. load the product record
# ---------------------------------------------------------------------------
[ -f "$MANIFEST" ] || die "manifest not found at $MANIFEST — it is the single source of truth binding a product to its Stripe account+price and its deploy source. Create it first."

REC="$(jq -c --arg id "$PRODUCT_ID" '
  (if type=="array" then . else (.products // []) end)
  | map(select(.product_id == $id)) | first // empty
' "$MANIFEST" 2>/dev/null || true)"

[ -n "$REC" ] || die "product_id '$PRODUCT_ID' not found. Known ids: $(jq -r '(if type=="array" then . else (.products // []) end)|map(.product_id)|join(", ")' "$MANIFEST" 2>/dev/null)"

jqget() { printf '%s' "$REC" | jq -r "$1 // empty"; }

FACTORY="$(jqget '.owning_factory // .factory')"
NAME="$(jqget '.name')"
SOURCE_OF_TRUTH="$(jqget '.source_of_truth')"
SOURCE_DIR_FIELD="$(jqget '.source_dir')"          # optional clean path override in manifest
VERCEL_PROJECT="$(jqget '.vercel_project_name // .vercel_project')"
LIVE_URL="$(jqget '.live_url')"
STRIPE_ACCOUNT_ID="$(jqget '.stripe_account_id')"
STRIPE_PRODUCT_ID="$(jqget '.stripe_product_id')"
# checkout endpoint + smoke payload: manifest overrides, else the proven Story Studio defaults
CHECKOUT_ENDPOINT="$(jqget '.checkout_endpoint')"; [ -n "$CHECKOUT_ENDPOINT" ] || CHECKOUT_ENDPOINT="/api/create-checkout-session"

log ""
log "product        : $PRODUCT_ID  ($NAME)"
log "factory        : ${FACTORY:-?}"
log "vercel_project : ${VERCEL_PROJECT:-<none>}"
log "live_url       : ${LIVE_URL:-<none>}"
log "stripe_account : ${STRIPE_ACCOUNT_ID:-<none declared>}"

# tiers: array of {tier, amount_usd, interval, id}
TIERS_JSON="$(printf '%s' "$REC" | jq -c '[ (.price_ids // [])[] | {
    tier:     (.tier // "default"),
    amount:   (.amount_usd // .amount // null),
    interval: (.interval // "one_time"),
    id:       (.id // "")
} ]')"
TIER_COUNT="$(printf '%s' "$TIERS_JSON" | jq 'length')"

# ---------------------------------------------------------------------------
# 2. SOURCE-MATCH GUARD (fail-closed; this is how the live app got clobbered once)
# ---------------------------------------------------------------------------
step "source-match guard"
# resolve a clean on-disk source: prefer explicit --source, then manifest .source_dir,
# then a leading path token parsed out of the prose source_of_truth. Fail-closed if none
# points at a real directory inside the repo.
RESOLVED_SRC=""
if [ "$SOURCE_DIR" != "$PWD" ]; then
  RESOLVED_SRC="$SOURCE_DIR"
elif [ -n "$SOURCE_DIR_FIELD" ]; then
  RESOLVED_SRC="$SOURCE_DIR_FIELD"
else
  # pull the first whitespace token that looks like a repo-relative/absolute path
  CAND="$(printf '%s' "$SOURCE_OF_TRUTH" | grep -oE '(/[A-Za-z0-9._-]+)+|[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+' | head -n1 || true)"
  [ -n "$CAND" ] && RESOLVED_SRC="$CAND"
fi

log "declared source_of_truth : ${SOURCE_OF_TRUTH:0:120}"
log "resolved deploy source    : ${RESOLVED_SRC:-<none resolvable>}"

SRC_OK=0
if printf '%s' "$SOURCE_OF_TRUTH" | grep -qiE 'UNKNOWN|NOT-IN-REPO|CLOBBER'; then
  fail "source_of_truth is UNKNOWN / NOT-IN-REPO / clobber-guarded for $PRODUCT_ID."
  log  "  This product's real deploy source is not reproducibly present in this checkout."
  log  "  Refusing to treat any repo folder as its source (that is EXACTLY the story-studio clobber)."
  SRC_OK=1
elif [ -z "$RESOLVED_SRC" ]; then
  fail "no on-disk source directory could be resolved from the manifest for $PRODUCT_ID."
  SRC_OK=1
else
  ABS_SRC="$(canon "$RESOLVED_SRC")"
  if [ ! -d "$ABS_SRC" ]; then
    fail "resolved source '$ABS_SRC' is not a directory on disk."
    SRC_OK=1
  else
    case "$ABS_SRC" in
      "$REPO_ROOT"|"$REPO_ROOT"/*) pass "source resolves inside the repo: $ABS_SRC" ;;
      *) fail "resolved source '$ABS_SRC' is OUTSIDE the repo — refusing (foreign folder)"; SRC_OK=1 ;;
    esac
  fi
fi

if [ "$SRC_OK" -ne 0 ]; then
  if [ "$MODE" = "go" ]; then
    die "SOURCE-MATCH GUARD FAILED — refusing to run the money+deploy pipeline for '$PRODUCT_ID' without a verified on-disk source. Recover the exact source into the repo (or pass --source), update the manifest, then re-run."
  fi
  log ""
  plan "GUARD would BLOCK --go for '$PRODUCT_ID': no verified deploy source. This is the fail-closed path — correct and expected until the source is recovered."
fi

# ---------------------------------------------------------------------------
# 3. per-product Keychain secret
# ---------------------------------------------------------------------------
KEYCHAIN_SERVICE="helm-stripe-$(lc "$PRODUCT_ID")"
KEYCHAIN_ACCOUNT="helm"

keychain_has() { security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" >/dev/null 2>&1; }
# read the secret WITHOUT ever printing it to the terminal (goes only into a variable)
keychain_read() { security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null; }

step "Stripe secret (macOS Keychain service: $KEYCHAIN_SERVICE)"
HAS_MAC_SECURITY=0
command -v security >/dev/null 2>&1 && HAS_MAC_SECURITY=1

if [ "$HAS_MAC_SECURITY" -ne 1 ]; then
  fail "'security' (macOS Keychain CLI) not found — this pipeline's secret store is macOS-only."
  [ "$MODE" = "go" ] && die "cannot securely source the Stripe key without the macOS Keychain."
elif keychain_has; then
  pass "Keychain item EXISTS for $KEYCHAIN_SERVICE (secret not read/printed in plan mode)."
else
  fail "Keychain item MISSING for $KEYCHAIN_SERVICE."
  [ "$MODE" = "plan" ] && plan "--go would open a HIDDEN prompt for a one-time paste of this product's sk_live_ key, validate it against api.stripe.com, and store it in the Keychain (never echoed, never written to a repo file)."
fi

# ---------------------------------------------------------------------------
# validate a Stripe key DIRECTLY against api.stripe.com (no CLI flag). Returns acct id.
# arg1 = key. Prints acct_... on success (to stdout), non-zero on failure. Never prints key.
# ---------------------------------------------------------------------------
stripe_validate_key() {
  local key="$1" resp acct
  resp="$(curl -sS -m 20 -u "$key:" "$STRIPE_API/account" 2>/dev/null || true)"
  acct="$(printf '%s' "$resp" | jq -r '.id // empty' 2>/dev/null)"
  if [ -z "$acct" ]; then
    return 1
  fi
  printf '%s' "$acct"
}

# ---------------------------------------------------------------------------
# 4. plan the Stripe product/price idempotency + env mapping (both modes compute the plan)
# ---------------------------------------------------------------------------
# cache file for resolved live IDs (per product). Never contains a secret.
PRICE_CACHE="$REPO_ROOT/coordination/products/.price_ids.$(lc "$PRODUCT_ID").json"

step "Stripe product + price plan ($TIER_COUNT tier(s))"
if [ "$TIER_COUNT" -eq 0 ]; then
  fail "no price tiers declared in the manifest for $PRODUCT_ID — not sellable yet (rung < 3)."
  [ "$MODE" = "go" ] && die "cannot wire a checkout with zero declared prices. Define price_ids in the manifest first."
fi

# print the tier plan + the env var each maps to
printf '%s' "$TIERS_JSON" | jq -r '.[] | "  tier=\(.tier)  amount=$\(.amount // "?")  interval=\(.interval)  declared_id=\(.id // "-")"'
log ""
log "Stripe idempotency strategy (in the KEY'S OWN account):"
log "  * product: reuse if metadata.helm_product_id=$PRODUCT_ID already exists, else create '$NAME'."
printf '%s' "$TIERS_JSON" | jq -r --arg pid "$(lc "$PRODUCT_ID")" '.[] |
  "  * price [\(.tier)]: stable lookup_key=helm_\($pid)_\(.tier); reuse if that lookup_key resolves, else create; env var STRIPE_PRICE_\(.tier | ascii_upcase)."'
log "  resolved IDs cache -> $PRICE_CACHE"

# ---------------------------------------------------------------------------
# idempotent ensure-price (GO only). Uses curl to api.stripe.com exclusively.
# args: key product_id_stripe tier amount interval declared_id
# echoes resolved price id on stdout.
# ---------------------------------------------------------------------------
stripe_ensure_price() {
  local key="$1" sprod="$2" tier="$3" amount="$4" interval="$5" declared="$6"
  local lookup="helm_$(lc "$PRODUCT_ID")_${tier}" pid resp
  # 1) reuse by stable lookup_key
  resp="$(curl -sS -m 20 -u "$key:" -G "$STRIPE_API/prices" \
            --data-urlencode "lookup_keys[]=$lookup" --data-urlencode "active=true" 2>/dev/null || true)"
  pid="$(printf '%s' "$resp" | jq -r '.data[0].id // empty' 2>/dev/null)"
  if [ -n "$pid" ]; then printf '%s' "$pid"; return 0; fi
  # 2) reuse the manifest-declared id if it retrieves under THIS key's account
  if [ -n "$declared" ]; then
    resp="$(curl -sS -m 20 -u "$key:" "$STRIPE_API/prices/$declared" 2>/dev/null || true)"
    if [ "$(printf '%s' "$resp" | jq -r '.id // empty')" = "$declared" ]; then
      # attach the stable lookup_key for future idempotency (best-effort)
      curl -sS -m 20 -u "$key:" "$STRIPE_API/prices/$declared" \
        --data-urlencode "lookup_key=$lookup" --data-urlencode "transfer_lookup_key=true" >/dev/null 2>&1 || true
      printf '%s' "$declared"; return 0
    fi
  fi
  # 3) create fresh
  local args=( --data-urlencode "currency=usd"
               --data-urlencode "unit_amount=$(( amount * 100 ))"
               --data-urlencode "product=$sprod"
               --data-urlencode "lookup_key=$lookup"
               --data-urlencode "transfer_lookup_key=true"
               --data-urlencode "metadata[helm_product_id]=$PRODUCT_ID"
               --data-urlencode "metadata[helm_tier]=$tier" )
  case "$interval" in
    month|year|week|day) args+=( --data-urlencode "recurring[interval]=$interval" ) ;;
    *) : ;; # one_time: no recurring
  esac
  act "POST $STRIPE_API/prices  (create $tier \$$amount/$interval, lookup_key=$lookup)"
  resp="$(curl -sS -m 20 -u "$key:" "$STRIPE_API/prices" "${args[@]}" 2>/dev/null || true)"
  pid="$(printf '%s' "$resp" | jq -r '.id // empty')"
  [ -n "$pid" ] || return 1
  printf '%s' "$pid"
}

stripe_ensure_product() {
  local key="$1" resp sid
  # reuse by metadata search
  resp="$(curl -sS -m 20 -u "$key:" -G "$STRIPE_API/products/search" \
            --data-urlencode "query=metadata['helm_product_id']:'$PRODUCT_ID'" 2>/dev/null || true)"
  sid="$(printf '%s' "$resp" | jq -r '.data[0].id // empty' 2>/dev/null)"
  if [ -n "$sid" ]; then printf '%s' "$sid"; return 0; fi
  # reuse a declared product id if it retrieves
  if [ -n "$STRIPE_PRODUCT_ID" ] && printf '%s' "$STRIPE_PRODUCT_ID" | grep -qE '^prod_'; then
    resp="$(curl -sS -m 20 -u "$key:" "$STRIPE_API/products/$STRIPE_PRODUCT_ID" 2>/dev/null || true)"
    if [ "$(printf '%s' "$resp" | jq -r '.id // empty')" = "$STRIPE_PRODUCT_ID" ]; then
      printf '%s' "$STRIPE_PRODUCT_ID"; return 0
    fi
  fi
  # create
  act "POST $STRIPE_API/products  (create '$NAME')"
  resp="$(curl -sS -m 20 -u "$key:" "$STRIPE_API/products" \
            --data-urlencode "name=$NAME" \
            --data-urlencode "metadata[helm_product_id]=$PRODUCT_ID" 2>/dev/null || true)"
  sid="$(printf '%s' "$resp" | jq -r '.id // empty')"
  [ -n "$sid" ] || return 1
  printf '%s' "$sid"
}

# ---------------------------------------------------------------------------
# 5. Vercel env plan
# ---------------------------------------------------------------------------
step "Vercel prod env plan (project: ${VERCEL_PROJECT:-<none>})"
log "Would set (values from Keychain/Stripe, piped — never echoed):"
log "  STRIPE_SECRET_KEY        <- Keychain $KEYCHAIN_SERVICE"
printf '%s' "$TIERS_JSON" | jq -r '.[] | "  STRIPE_PRICE_\(.tier | ascii_upcase)   <- resolved Stripe price id"'
[ -n "$LIVE_URL" ] && log "  BASE_URL                 <- $LIVE_URL"

# ---------------------------------------------------------------------------
# 6. deploy + smoke plan (delegated to the ONE guard-railed pipeline)
# ---------------------------------------------------------------------------
step "deploy + checkout smoke (via scripts/factory_deploy.sh — the single guarded path)"
log "checkout smoke: POST ${LIVE_URL:-<live_url>}${CHECKOUT_ENDPOINT}"
log "  must return a real https://checkout.stripe.com/ or https://buy.stripe.com/ URL, else auto-rollback."
if [ -x "$FACTORY_DEPLOY" ]; then
  pass "factory_deploy.sh present + executable — deploy rides preview -> smoke -> promote -> auto-rollback."
else
  fail "scripts/factory_deploy.sh not found/executable at $FACTORY_DEPLOY."
  [ "$MODE" = "go" ] && die "the guarded deploy pipeline is missing; refusing to deploy by any other path."
fi

# ===========================================================================
# PLAN MODE — stop here. Nothing paid, set, or deployed.
# ===========================================================================
if [ "$MODE" != "go" ]; then
  step "PLAN complete — nothing was paid, set, or deployed"
  log "To arm the live path (founder must be signed into Vercel; will paste the Stripe key once if absent):"
  log "  cd <verified source dir>  &&  scripts/factory_to_money.sh $PRODUCT_ID --go"
  exit 0
fi

# ===========================================================================
# GO MODE — armed. Real Keychain read / paste, Stripe writes, Vercel env, deploy.
# ===========================================================================
step "GO — arming live pipeline for $PRODUCT_ID"

# -- obtain + validate the Stripe key -------------------------------------------------
KEY=""
scrub() { KEY=""; }
trap scrub EXIT

if keychain_has; then
  KEY="$(keychain_read)"
  [ -n "$KEY" ] || die "Keychain item exists but returned empty — inspect $KEYCHAIN_SERVICE."
else
  log "No Keychain secret for $KEYCHAIN_SERVICE yet."
  command -v open >/dev/null 2>&1 && open "https://dashboard.stripe.com/apikeys" >/dev/null 2>&1 || true
  printf 'Paste this product'\''s LIVE Stripe secret key (sk_live_…, hidden), or Enter to cancel: '
  read -rs KEY; echo
  [ -n "$KEY" ] || die "no key entered — nothing changed."
  case "$KEY" in
    sk_live_*) : ;;
    sk_test_*) scrub; die "that is a TEST key (sk_test_). Paste a LIVE key (sk_live_)." ;;
    rk_*)      scrub; die "that is a RESTRICTED key. This pipeline needs a standard secret key (sk_live_)." ;;
    *)         scrub; die "that does not look like a Stripe secret key (expected sk_live_…)." ;;
  esac
fi

step "validate key directly against api.stripe.com (GET /v1/account — no CLI flag)"
ACCT="$(stripe_validate_key "$KEY" || true)"
[ -n "$ACCT" ] || { scrub; die "the Stripe key could not authenticate against api.stripe.com — wrong/expired/restricted. Nothing changed."; }
pass "key authenticates. account = $ACCT"
if [ -n "$STRIPE_ACCOUNT_ID" ] && printf '%s' "$STRIPE_ACCOUNT_ID" | grep -qE '^acct_' && [ "$STRIPE_ACCOUNT_ID" != "$ACCT" ]; then
  scrub; die "ACCOUNT MISMATCH: key is $ACCT but the manifest binds $PRODUCT_ID to $STRIPE_ACCOUNT_ID. Refusing (this is exactly the Story Studio 'No such price' class of bug)."
fi

# store the validated key in the Keychain for next time (if it was a fresh paste)
if ! keychain_has; then
  act "security add-generic-password -s $KEYCHAIN_SERVICE -a $KEYCHAIN_ACCOUNT (store validated key; value not echoed)"
  security add-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w "$KEY" -U >/dev/null 2>&1 \
    && pass "key stored in Keychain ($KEYCHAIN_SERVICE)." || fail "could not store key in Keychain (continuing with in-memory key)."
fi

# -- ensure product + prices idempotently ---------------------------------------------
step "ensure Stripe product + prices (idempotent, in account $ACCT)"
SPROD="$(stripe_ensure_product "$KEY" || true)"
[ -n "$SPROD" ] || { scrub; die "could not resolve/create the Stripe product. Nothing deployed."; }
pass "stripe product: $SPROD"

# build a JSON map {ENVVAR: price_id} + record for cache
ENV_MAP="{}"
CACHE_TIERS="[]"
i=0
while [ "$i" -lt "$TIER_COUNT" ]; do
  T="$(printf '%s' "$TIERS_JSON" | jq -c ".[$i]")"
  tier="$(printf '%s' "$T" | jq -r '.tier')"
  amount="$(printf '%s' "$T" | jq -r '.amount // empty')"
  interval="$(printf '%s' "$T" | jq -r '.interval')"
  declared="$(printf '%s' "$T" | jq -r '.id // empty')"
  [ -n "$amount" ] || { scrub; die "tier '$tier' has no amount_usd in the manifest — cannot create a price."; }
  PID="$(stripe_ensure_price "$KEY" "$SPROD" "$tier" "$amount" "$interval" "$declared" || true)"
  [ -n "$PID" ] || { scrub; die "could not ensure the Stripe price for tier '$tier'. Nothing deployed."; }
  ENVVAR="STRIPE_PRICE_$(uc "$tier")"
  pass "price [$tier] -> $PID  ($ENVVAR)"
  ENV_MAP="$(printf '%s' "$ENV_MAP" | jq -c --arg k "$ENVVAR" --arg v "$PID" '. + {($k):$v}')"
  CACHE_TIERS="$(printf '%s' "$CACHE_TIERS" | jq -c --arg t "$tier" --arg id "$PID" --arg ev "$ENVVAR" \
                  '. + [{tier:$t, price_id:$id, env:$ev}]')"
  i=$((i+1))
done

# write cache (contains only public price/product IDs — no secret)
jq -n --arg pid "$PRODUCT_ID" --arg acct "$ACCT" --arg sprod "$SPROD" --argjson tiers "$CACHE_TIERS" \
  '{product_id:$pid, stripe_account_id:$acct, stripe_product_id:$sprod, prices:$tiers, updated_at:(now|todate)}' \
  > "$PRICE_CACHE" && pass "cached resolved IDs -> $PRICE_CACHE"

# -- set Vercel prod env --------------------------------------------------------------
step "set Vercel production env (project $VERCEL_PROJECT)"
command -v vercel >/dev/null 2>&1 || { scrub; die "--go requires the Vercel CLI on PATH + logged in (founder's auth step)."; }
vercel whoami >/dev/null 2>&1 || { scrub; die "not signed into Vercel — run 'vercel login' (founder auth), then re-run --go."; }

setenv() { # NAME VALUE  (value piped, never echoed)
  vercel env rm "$1" production -y >/dev/null 2>&1 || true
  printf '%s' "$2" | vercel env add "$1" production >/dev/null 2>&1 && pass "set $1" || fail "could not set $1"
}
act "vercel env add STRIPE_SECRET_KEY production (piped; not echoed)"
setenv STRIPE_SECRET_KEY "$KEY"
for ENVVAR in $(printf '%s' "$ENV_MAP" | jq -r 'keys[]'); do
  setenv "$ENVVAR" "$(printf '%s' "$ENV_MAP" | jq -r --arg k "$ENVVAR" '.[$k]')"
done
[ -n "$LIVE_URL" ] && setenv BASE_URL "$LIVE_URL"
scrub  # secret no longer needed in memory

# -- deploy via the ONE guarded pipeline ----------------------------------------------
step "hand off to the guarded deploy pipeline (preview -> smoke -> promote -> auto-rollback)"
act "$FACTORY_DEPLOY $PRODUCT_ID --go --source $ABS_SRC"
if "$FACTORY_DEPLOY" "$PRODUCT_ID" --go --source "$ABS_SRC"; then
  step "DONE — $PRODUCT_ID checkout wired + deployed + smoke-verified"
  log "Prices live in $ACCT; Vercel env set; production smoke saw a real Stripe checkout URL."
  log "NO FAKE GREEN: EARNING (rung 5) is only confirmed when a real charge SETTLES in Stripe."
  exit 0
else
  die "guarded deploy FAILED (and auto-rolled-back if it had promoted). Stripe prices/env are set and reusable; fix the build and re-run --go."
fi
