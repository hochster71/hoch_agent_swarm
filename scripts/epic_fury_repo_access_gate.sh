#!/usr/bin/env bash
# =============================================================================
# epic_fury_repo_access_gate.sh
# Verifies repo access and stack metrics for Epic Fury 2026.
# =============================================================================
set -euo pipefail

echo "==> Running Epic Fury Repo Access Gate..."

REPO_PATH="/Users/michaelhoch/epic-fury-build/epic-fury-2026"

# 1. Verify directory access
if [ ! -d "${REPO_PATH}" ]; then
  echo "❌ FAIL: Epic Fury 2026 local directory not found at ${REPO_PATH}"
  exit 1
fi

# 2. Check build config files
if [ ! -f "${REPO_PATH}/package.json" ]; then
  echo "❌ FAIL: package.json is missing in ${REPO_PATH}"
  exit 1
fi

# 3. Check README
if [ ! -f "${REPO_PATH}/README.md" ]; then
  echo "❌ FAIL: README.md is missing in ${REPO_PATH}"
  exit 1
fi

# 4. Parse Git HEAD commit
pushd "${REPO_PATH}" >/dev/null
COMMIT_HASH=$(git rev-parse HEAD 2>/dev/null || echo "UNKNOWN")
popd >/dev/null

if [ "${COMMIT_HASH}" = "UNKNOWN" ]; then
  echo "❌ FAIL: Unable to resolve Git HEAD commit."
  exit 1
fi

echo "✅ Pass: Repo access verified."
echo "local_repo_path=${REPO_PATH}"
echo "current_commit=${COMMIT_HASH}"
exit 0
