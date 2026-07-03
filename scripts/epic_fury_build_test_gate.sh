#!/usr/bin/env bash
# =============================================================================
# epic_fury_build_test_gate.sh
# Runs typecheck, build, and test suites for Epic Fury 2026.
# =============================================================================
set -euo pipefail

echo "==> Running Epic Fury Build & Test Gate..."

REPO_PATH="/Users/michaelhoch/epic-fury-build/epic-fury-2026"

pushd "${REPO_PATH}" >/dev/null

echo "1. Running TypeScript Typecheck..."
npm run typecheck

echo "2. Running Next.js Build..."
npm run build

echo "3. Running Contract Tests..."
npm run test:contract

echo "4. Running Smoke Tests..."
npm run test:smoke

echo "5. Running API Hardening Tests..."
npm run test:api-hardening

popd >/dev/null

echo "✅ Pass: Build and test gate passed successfully."
exit 0
