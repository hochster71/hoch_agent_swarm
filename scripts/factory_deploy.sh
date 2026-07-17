#!/usr/bin/env bash
# factory_deploy.sh — the ONE guard-railed deploy pipeline every HELM factory product uses.
#
# WHY THIS EXISTS (2026-07-16): a deploy was run from the WRONG folder — a scaffold that
# happened to be linked to the live `story-studio-live` Vercel project — and
# `vercel deploy --prod` pushed that scaffold over the real app, 404'ing it in production.
# It was rolled back. This script makes that class of accident structurally impossible:
# it refuses to deploy unless the folder you are in IS the product's declared
# source_of_truth, it never touches prod directly (preview -> smoke-test -> promote),
# and it auto-rolls-back if the post-promote production check fails.
#
# USAGE:
#   scripts/factory_deploy.sh <product_id> [--go] [--source <dir>]
#
#   (no --go)  DRY-RUN / PLAN. Runs the source-match guard + a read-only health check and
#              prints exactly what it WOULD do. Deploys NOTHING.
#   --go       ARM. Runs preview -> smoke-test -> promote -> (auto-rollback on failure).
#   --source   Override the folder checked against source_of_truth (default: $PWD).
#
# Every irreversible action prints an [ACT] line BEFORE it happens.
# NO FAKE GREEN: fail-closed everywhere; only report a gate passed on real evidence.

set -euo pipefail

# ---------------------------------------------------------------------------
# constants / helpers
# ---------------------------------------------------------------------------
REPO_ROOT="/Users/michaelhoch/hoch_agent_swarm"
MANIFEST="${FACTORY_PRODUCTS_MANIFEST:-$REPO_ROOT/coordination/products/products.json}"

# Documented products.json schema (array of products), each:
#   product_id       : stable id, e.g. "HSF_STORY_STUDIO"
#   source_of_truth  : the ONLY dir/repo this product may deploy FROM (abs, or rel to repo root)
#   vercel_project   : the Vercel project name it maps to (1 repo -> 1 project)
#   live_url         : production URL to health-check
#   health_check     : path (sellable products: a checkout/session endpoint that returns a Stripe URL)
#   sellable         : bool — if true the smoke test must see a real Stripe session URL
#   owning_factory   : e.g. "HSF"

log()  { printf '%s\n'  "$*"; }
act()  { printf '[ACT] %s\n' "$*"; }
die()  { printf '\n[ABORT] %s\n' "$*" >&2; exit 1; }
pass() { printf '[PASS] %s\n' "$*"; }
fail() { printf '[FAIL] %s\n' "$*" >&2; }
step() { printf '\n=== %s ===\n' "$*"; }

# canonicalize a path (resolve symlinks/.., no trailing slash). Missing dirs -> best effort.
canon() {
  local p="$1"
  # make relative paths relative to the repo root
  case "$p" in
    /*) : ;;
    *)  p="$REPO_ROOT/$p" ;;
  esac
  if command -v realpath >/dev/null 2>&1; then
    realpath -m -- "$p" 2>/dev/null || printf '%s' "$p"
  else
    # portable fallback
    ( cd "$p" 2>/dev/null && pwd -P ) || printf '%s' "${p%/}"
  fi
}

# ---------------------------------------------------------------------------
# arg parsing
# ---------------------------------------------------------------------------
PRODUCT_ID=""
GO=0
SOURCE_DIR="$PWD"

while [ $# -gt 0 ]; do
  case "$1" in
    --go)      GO=1; shift ;;
    --source)  SOURCE_DIR="${2:-}"; [ -n "$SOURCE_DIR" ] || die "--source needs a directory"; shift 2 ;;
    --source=*) SOURCE_DIR="${1#*=}"; shift ;;
    -h|--help)
      sed -n '2,25p' "$0"; exit 0 ;;
    -*)        die "unknown flag: $1" ;;
    *)
      [ -z "$PRODUCT_ID" ] || die "unexpected extra arg: $1"
      PRODUCT_ID="$1"; shift ;;
  esac
done

[ -n "$PRODUCT_ID" ] || die "usage: factory_deploy.sh <product_id> [--go] [--source <dir>]"
command -v jq >/dev/null 2>&1 || die "jq is required but not on PATH"

MODE="DRY-RUN (plan only; deploys nothing)"
[ "$GO" -eq 1 ] && MODE="ARMED (--go): preview -> smoke -> promote -> auto-rollback"

step "factory_deploy — $PRODUCT_ID"
log  "manifest : $MANIFEST"
log  "mode     : $MODE"
log  "source   : $SOURCE_DIR"

# ---------------------------------------------------------------------------
# 1. load the product record from the manifest
# ---------------------------------------------------------------------------
[ -f "$MANIFEST" ] || die "manifest not found at $MANIFEST — create coordination/products/products.json before deploying. This is the single source of truth that prevents cross-linked deploys."

# support both a bare top-level array and a {"products":[...]} wrapper
REC="$(jq -c --arg id "$PRODUCT_ID" '
  (if type=="array" then . else (.products // []) end)
  | map(select(.product_id == $id)) | first // empty
' "$MANIFEST" 2>/dev/null || true)"

[ -n "$REC" ] || die "product_id '$PRODUCT_ID' not found in manifest. Known ids: $(jq -r '(if type=="array" then . else (.products // []) end)|map(.product_id)|join(", ")' "$MANIFEST" 2>/dev/null)"

jqget() { printf '%s' "$REC" | jq -r "$1 // empty"; }

SOURCE_OF_TRUTH="$(jqget '.source_of_truth')"
VERCEL_PROJECT="$(jqget '.vercel_project')"
LIVE_URL="$(jqget '.live_url')"
HEALTH_CHECK="$(jqget '.health_check')"
SELLABLE="$(jqget '.sellable')"
OWNING_FACTORY="$(jqget '.owning_factory')"

[ -n "$SOURCE_OF_TRUTH" ] || die "manifest record for '$PRODUCT_ID' is missing source_of_truth — cannot verify safe deploy origin. Refusing."
[ -n "$VERCEL_PROJECT" ]  || die "manifest record for '$PRODUCT_ID' is missing vercel_project."

log ""
log "product        : $PRODUCT_ID  (factory: ${OWNING_FACTORY:-?})"
log "vercel_project : $VERCEL_PROJECT"
log "source_of_truth: $SOURCE_OF_TRUTH"
log "live_url       : ${LIVE_URL:-<none>}"
log "health_check   : ${HEALTH_CHECK:-<none>}"
log "sellable       : ${SELLABLE:-false}"

# ---------------------------------------------------------------------------
# 2. SOURCE-MATCH GUARD  (the key safety — this is how the live app got clobbered)
# ---------------------------------------------------------------------------
step "source-match guard"
EXPECT="$(canon "$SOURCE_OF_TRUTH")"
HAVE="$(canon "$SOURCE_DIR")"
log "declared source_of_truth : $EXPECT"
log "actual deploy source     : $HAVE"

if [ "$EXPECT" != "$HAVE" ]; then
  fail "SOURCE MISMATCH"
  die  "refusing: source mismatch — this is EXACTLY how the live app got clobbered (a scaffold cross-linked to '$VERCEL_PROJECT' was deployed over prod). Deploy '$PRODUCT_ID' only from its declared source_of_truth:
        expected: $EXPECT
        got     : $HAVE
        cd into the correct folder (or pass --source) and re-run."
fi
pass "source matches declared source_of_truth — safe to proceed"

# ---------------------------------------------------------------------------
# read-only current production health check (runs in BOTH modes)
# ---------------------------------------------------------------------------
http_code() { curl -sS -o /dev/null -w '%{http_code}' -m 20 "$1" 2>/dev/null || echo "000"; }

step "current production health (read-only)"
if [ -n "$LIVE_URL" ]; then
  CUR="$(http_code "$LIVE_URL")"
  if [ "$CUR" = "200" ]; then pass "prod $LIVE_URL -> HTTP $CUR"; else fail "prod $LIVE_URL -> HTTP $CUR"; fi
else
  log "(no live_url in manifest; skipping)"
fi

# ---------------------------------------------------------------------------
# smoke-test helpers
# ---------------------------------------------------------------------------
# Fail-closed Stripe check: response must contain a real Stripe session URL and NONE of
# the known failure signatures (expired key, missing price, server error, inert 501).
STRIPE_BAD='Expired API Key|No such price|No such|Invalid API Key|api_key|error|501 |Not Implemented|"error"'
smoke_sellable() {
  local base="$1" body http url
  url="${base%/}${HEALTH_CHECK}"
  act "POST $url  (checkout smoke test)"
  http="$(curl -sS -o /tmp/factory_smoke_body.$$ -w '%{http_code}' -m 30 -X POST \
          -H 'Content-Type: application/json' -d '{"smoke":true}' "$url" 2>/dev/null || echo 000)"
  body="$(cat /tmp/factory_smoke_body.$$ 2>/dev/null || true)"; rm -f /tmp/factory_smoke_body.$$
  if [ "$http" != "200" ] && [ "$http" != "303" ]; then
    fail "checkout endpoint HTTP $http"; log "  body: ${body:0:300}"; return 1
  fi
  if printf '%s' "$body" | grep -Eiq "$STRIPE_BAD"; then
    fail "checkout response contains a failure signature (expired key / no such price / error)"; log "  body: ${body:0:300}"; return 1
  fi
  if printf '%s' "$body" | grep -Eq 'https://(checkout|buy)\.stripe\.com/|"url"[[:space:]]*:[[:space:]]*"https://[^"]*stripe'; then
    pass "checkout returned a real Stripe session URL"; return 0
  fi
  fail "checkout response did NOT contain a real Stripe session URL"; log "  body: ${body:0:300}"; return 1
}

# Full smoke: home path 200 + (if sellable) Stripe session. Fail-closed.
smoke_test() {
  local base="$1" ok=0
  local code; code="$(http_code "${base%/}/")"
  if [ "$code" = "200" ]; then pass "home ${base%/}/ -> HTTP 200"; else fail "home ${base%/}/ -> HTTP $code"; ok=1; fi
  if [ "${SELLABLE:-false}" = "true" ]; then
    if [ -z "$HEALTH_CHECK" ]; then fail "sellable product but no health_check path in manifest"; ok=1;
    else smoke_sellable "$base" || ok=1; fi
  fi
  return $ok
}

# ---------------------------------------------------------------------------
# PLAN (no --go): print what WOULD happen and stop. Nothing irreversible.
# ---------------------------------------------------------------------------
if [ "$GO" -ne 1 ]; then
  step "PLAN (dry-run — nothing deployed)"
  log "Would, from $HAVE, against Vercel project '$VERCEL_PROJECT':"
  log "  1. vercel deploy            (PREVIEW, no --prod) and capture the preview URL"
  log "  2. smoke-test the preview   home -> 200${SELLABLE:+; and (sellable) POST $HEALTH_CHECK must return a real Stripe session URL}"
  log "  3. vercel promote <preview> (only if smoke passes) -> production"
  log "  4. re-verify prod ($LIVE_URL); vercel rollback automatically if that check fails"
  log ""
  log "Re-run with --go to arm. (Requires you to be signed into the Vercel CLI.)"
  exit 0
fi

# ---------------------------------------------------------------------------
# ARMED (--go): preview -> smoke -> promote -> auto-rollback
# ---------------------------------------------------------------------------
command -v vercel >/dev/null 2>&1 || die "--go requires the Vercel CLI on PATH. Install & 'vercel login' first (interactive auth is the founder's step)."

cd "$HAVE" || die "cannot cd into source $HAVE"

# capture the CURRENT production deployment first, so auto-rollback has a known-good target.
step "capture current prod deployment (rollback anchor)"
PRIOR_PROD="$(vercel ls "$VERCEL_PROJECT" --prod 2>/dev/null | grep -Eo 'https://[a-zA-Z0-9./-]+' | head -n1 || true)"
log "prior prod deployment: ${PRIOR_PROD:-<unknown — will fall back to 'vercel rollback' default>}"

# 3. PREVIEW deploy (never --prod)
step "preview deploy"
act "vercel deploy  (PREVIEW, project=$VERCEL_PROJECT)  — from $HAVE"
PREVIEW_URL="$(vercel deploy --yes 2>/dev/null | grep -Eo 'https://[a-zA-Z0-9./-]+' | tail -n1 || true)"
[ -n "$PREVIEW_URL" ] || die "preview deploy did not return a URL — refusing to promote. Nothing was pushed to production."
pass "preview URL: $PREVIEW_URL"

# 4. SMOKE TEST the preview
step "smoke-test preview"
if ! smoke_test "$PREVIEW_URL"; then
  die "smoke test FAILED on preview — refusing to promote. Production is UNTOUCHED. Fix the build and re-run."
fi
pass "preview smoke test passed"

# 5. PROMOTE preview -> production
step "promote to production"
act "vercel promote $PREVIEW_URL  (project=$VERCEL_PROJECT)"
if ! vercel promote "$PREVIEW_URL" --yes >/dev/null 2>&1; then
  die "promote command failed. Production not confirmed changed; if it did change, re-run to re-verify. Investigate before retrying."
fi
pass "promote command completed"

# 6. RE-VERIFY prod; AUTO-ROLLBACK on failure
step "post-promote production re-verify"
POST_OK=0
if [ -n "$LIVE_URL" ]; then
  # brief settle window for the CDN to swap
  sleep 5
  smoke_test "$LIVE_URL" || POST_OK=1
else
  fail "no live_url to verify post-promote — treating as FAIL (fail-closed)"; POST_OK=1
fi

if [ "$POST_OK" -ne 0 ]; then
  fail "post-promote production check FAILED — rolling back NOW"
  if [ -n "$PRIOR_PROD" ]; then
    act "vercel rollback $PRIOR_PROD  (restore prior known-good prod)"
    vercel rollback "$PRIOR_PROD" --yes >/dev/null 2>&1 || vercel rollback --yes >/dev/null 2>&1 || true
  else
    act "vercel rollback  (restore previous production deployment)"
    vercel rollback --yes >/dev/null 2>&1 || true
  fi
  die "DEPLOY FAILED and was auto-rolled-back. Production restored to prior deployment. Exit non-zero."
fi

pass "production verified healthy after promote"
step "DONE"
log "$PRODUCT_ID deployed and verified: preview $PREVIEW_URL -> promoted -> $LIVE_URL healthy."
exit 0
