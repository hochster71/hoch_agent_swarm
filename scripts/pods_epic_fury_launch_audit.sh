#!/usr/bin/env bash
# scripts/pods_epic_fury_launch_audit.sh — Non-destructive launch audit for Epic Fury 2026
set -uo pipefail

REPO_PATH="/Users/michaelhoch/epic-fury-build/epic-fury-2026"
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

pass()  { echo -e "${GREEN}✓ PASS${NC}  $*"; }
fail()  { echo -e "${RED}✗ FAIL${NC}  $*"; exit 1; }
info()  { echo -e "${CYAN}→${NC} $*"; }

echo -e "${BOLD}==================================================${NC}"
echo -e "${BOLD}  EPIC FURY 2026 — Launch Intake Audit${NC}"
echo -e "${BOLD}==================================================${NC}"

# 1. Local Path Verification
if [[ -d "$REPO_PATH" ]]; then
  pass "Local repository found at $REPO_PATH"
else
  fail "Repository folder not found at $REPO_PATH"
fi

# 2. Package.json Verification
PKG_JSON="$REPO_PATH/package.json"
if [[ -f "$PKG_JSON" ]]; then
  pass "package.json exists"
else
  fail "package.json is missing"
fi

# 3. Stack Classification (Next.js & React)
if grep -q '"next":' "$PKG_JSON"; then
  pass "Stack detected: Next.js framework"
else
  fail "Next.js dependency not found in package.json"
fi

if grep -q '"react":' "$PKG_JSON"; then
  pass "Stack detected: React framework"
else
  fail "React dependency not found in package.json"
fi

# 4. Monetization Setup Verification
if grep -q '"stripe":' "$PKG_JSON"; then
  pass "Monetization: Stripe web integration detected"
else
  fail "Stripe dependency not found in package.json"
fi

if grep -q '"@revenuecat/purchases-capacitor":' "$PKG_JSON"; then
  pass "Monetization: RevenueCat iOS integration detected"
else
  fail "RevenueCat dependency not found in package.json"
fi

# 5. Core Interface / Page Audits
if [[ -d "$REPO_PATH/app/privacy" ]]; then
  pass "Compliance: Privacy Policy page route exists at /privacy"
else
  fail "Privacy Policy route is missing"
fi

if [[ -d "$REPO_PATH/app/support" ]]; then
  pass "Support: Contact / Support page route exists at /support"
else
  fail "Support / Contact route is missing"
fi

if [[ -d "$REPO_PATH/app/api/stripe/checkout" ]]; then
  pass "Checkout: API endpoint /api/stripe/checkout is present"
else
  fail "Stripe Checkout API endpoint route is missing"
fi

if [[ -d "$REPO_PATH/app/api/webhooks/stripe" ]]; then
  pass "Webhook: API endpoint /api/webhooks/stripe is present"
else
  fail "Stripe webhook API endpoint route is missing"
fi

# 6. Git Status Check
cd "$REPO_PATH"
if [[ -d ".git" ]]; then
  pass "Git Repository initialized"
  info "Branch: $(git branch --show-current)"
  info "Last commit: $(git log -1 --oneline)"
else
  fail "Git directory (.git) not found"
fi

echo ""
echo -e "${GREEN}${BOLD}EPIC FURY 2026 AUDIT COMPLETED SUCCESSFULLY. NO BLOCKERS DETECTED.${NC}"
echo ""
