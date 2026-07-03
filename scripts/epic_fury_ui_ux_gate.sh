#!/usr/bin/env bash
# =============================================================================
# epic_fury_ui_ux_gate.sh
# Runs UI/UX and accessibility E2E Playwright tests for Epic Fury 2026.
# =============================================================================
set -euo pipefail

echo "==> Running Epic Fury UI/UX and Accessibility Gate..."

# Clean next cache and restart the dev server to avoid webpack chunk mismatch issues from the build step
echo "Restarting Next.js dev server to clean compilation caches..."
DEV_PID=$(lsof -t -i :3003 || true)
if [ -n "$DEV_PID" ]; then
  kill -9 $DEV_PID || true
fi
rm -rf /Users/michaelhoch/epic-fury-build/epic-fury-2026/.next

nohup npm run dev --prefix /Users/michaelhoch/epic-fury-build/epic-fury-2026 > /Users/michaelhoch/epic-fury-build/epic-fury-2026/dev-server.log 2>&1 &
sleep 6

npx playwright test tests/e2e/epic-fury-smoke.spec.ts \
                    tests/e2e/epic-fury-mobile.spec.ts \
                    tests/e2e/epic-fury-accessibility.spec.ts

echo "✅ Pass: UI/UX gate passed successfully."
exit 0
