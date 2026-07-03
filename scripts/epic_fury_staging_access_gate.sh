#!/usr/bin/env bash
# =============================================================================
# epic_fury_staging_access_gate.sh
# Validates staging preview URL accessibility, static asset loading, and TLS response.
# =============================================================================
set -euo pipefail

STAGING_URL="https://epic-fury-2026-4hjkgwv9v-us-is-ir-war-2026.vercel.app"
# Get the bypass token dynamically from Vercel config
BYPASS_TOKEN=${VERCEL_BYPASS_TOKEN:-}
if [ -z "${BYPASS_TOKEN}" ]; then
  echo "     Fetching bypass token dynamically from Vercel..."
  BYPASS_TOKEN=$(npx vercel project protection epic-fury-2026 --scope us-is-ir-war-2026 --format json | jq -r '.protectionBypass | keys[0] // empty')
fi

if [ -z "${BYPASS_TOKEN}" ]; then
  echo "❌ FAIL: Vercel Automation Bypass Token not found."
  exit 1
fi

export VERCEL_BYPASS_TOKEN="${BYPASS_TOKEN}"

echo "==> Running Epic Fury Staging Access Gate..."

# 1. Verify Homepage loads via bypass header
echo "  1. Checking staging homepage status..."
HOME_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "x-vercel-protection-bypass: ${BYPASS_TOKEN}" "${STAGING_URL}/")
echo "     Status: $HOME_STATUS"
if [ "$HOME_STATUS" -ne 200 ]; then
  echo "❌ FAIL: Staging homepage returned non-200 status (${HOME_STATUS}) with bypass token."
  exit 1
fi

# 2. Extract static asset path dynamically and verify it loads with 200
echo "  2. Testing static asset loading..."
ASSET_PATH=$(curl -sS -H "x-vercel-protection-bypass: ${BYPASS_TOKEN}" "${STAGING_URL}/" | grep -o '/_next/static/chunks/webpack[^"]*' | head -n 1)

if [ -z "$ASSET_PATH" ]; then
  echo "❌ FAIL: Failed to extract webpack asset path from homepage."
  exit 1
fi

echo "     Testing static chunk: ${ASSET_PATH}"
ASSET_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "x-vercel-protection-bypass: ${BYPASS_TOKEN}" "${STAGING_URL}${ASSET_PATH}")
echo "     Asset status: $ASSET_STATUS"
if [ "$ASSET_STATUS" -ne 200 ]; then
  echo "❌ FAIL: Static asset ${ASSET_PATH} returned non-200 status (${ASSET_STATUS})."
  exit 1
fi

# 3. Run browser-level Playwright test
echo "  3. Running Playwright staging asset loading test..."
if ! npx playwright test tests/e2e/epic-fury-staging-assets.spec.ts; then
  echo "❌ FAIL: Playwright staging browser smoke test failed."
  exit 1
fi

# 4. Verify Live Release posture remains false
echo "  4. Verifying live release status..."
RELEASE_DECISION="docs/products/epic-fury-2026/FOUNDER_RELEASE_DECISION.md"
if grep -q "APPROVED_FOR_STAGING_OR_SANDBOX_REVIEW_ONLY" "$RELEASE_DECISION"; then
  echo "     Live release is correctly blocked in docs."
else
  echo "❌ FAIL: Unexpected live release state in ${RELEASE_DECISION}."
  exit 1
fi

echo "✅ Pass: Staging access gate passed successfully."
exit 0
