#!/usr/bin/env bash
# =============================================================================
# qa_ivv_red_team_gate.sh
# Verification gate for the ivv_red_team team dossier.
# =============================================================================
set -euo pipefail

DOSSIER_FILE="data/qa_dossiers/ivv_red_team_qa.json"

echo "==> Probing ivv_red_team QA dossier..."

if [ ! -f "$DOSSIER_FILE" ]; then
  echo "❌ FAIL: Dossier file '$DOSSIER_FILE' is missing!"
  exit 1
fi

STATUS=$(jq -r '.verification_status' "$DOSSIER_FILE" 2>/dev/null || echo "UNKNOWN")

if [ "$STATUS" != "PASS" ]; then
  echo "❌ FAIL: ivv_red_team QA Status is '$STATUS'"
  echo "Unresolved defects:"
  jq -r '.unresolved_defects[]' "$DOSSIER_FILE" 2>/dev/null || echo "None"
  exit 1
fi

echo "✅ ivv_red_team QA Dossier Verification Gate Passed."
exit 0
