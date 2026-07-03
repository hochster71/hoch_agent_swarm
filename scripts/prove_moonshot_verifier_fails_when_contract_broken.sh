#!/usr/bin/env bash
set -eo pipefail

UI_FILE="has_live_project_tracker/ui/hoch_pods_liftoff.html"
UI_BACKUP="has_live_project_tracker/ui/hoch_pods_liftoff.html.bak"

echo "=== TASK 2: PROVING MOONSHOT VERIFIER FAILS WHEN CONTRACT IS BROKEN ==="

# 1. Backup the current UI file
if [ ! -f "$UI_FILE" ]; then
  echo "❌ Error: UI source file $UI_FILE does not exist!"
  exit 1
fi
cp "$UI_FILE" "$UI_BACKUP"

# Ensure cleanup on exit
cleanup() {
  if [ -f "$UI_BACKUP" ]; then
    echo "Restoring $UI_FILE from backup..."
    mv "$UI_BACKUP" "$UI_FILE"
  fi
}
trap cleanup EXIT

# 2. Temporarily break launchBeam
echo "Breaking contract: renaming launchBeam to launchBeam_broken..."
sed -i '' 's/id="launchBeam"/id="launchBeam_broken"/g' "$UI_FILE"

# 3. Run verifier
echo "Running verifier against broken UI..."
set +e
PERT_BASE_URL=http://127.0.0.1:8765 node scripts/verify_ui_moonshot_browser.mjs > broken_output.log 2>&1
EXIT_CODE=$?
set -e

# 4. Confirm it FAILS
cat broken_output.log
if [ $EXIT_CODE -eq 0 ]; then
  echo "❌ Failure: The broken UI verifier passed but it was expected to fail!"
  exit 1
fi

if grep -q "MOONSHOT_LAUNCH_BEAM_MISSING" broken_output.log; then
  echo "🟢 Pass: Verifier failed as expected with MOONSHOT_LAUNCH_BEAM_MISSING."
else
  echo "❌ Failure: Verifier failed but not with the expected error!"
  exit 1
fi

# 5. Restore the UI file
echo "Restoring UI file..."
mv "$UI_BACKUP" "$UI_FILE"

# 6. Re-run the verifier
echo "Re-running verifier against restored UI..."
PERT_BASE_URL=http://127.0.0.1:8765 node scripts/verify_ui_moonshot_browser.mjs

echo "🟢 Success: Planted failure proof for Moonshot verifier completed successfully!"
exit 0
