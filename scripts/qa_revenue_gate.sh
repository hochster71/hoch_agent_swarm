#!/usr/bin/env bash
# =============================================================================
# qa_revenue_gate.sh
# Verification gate for the revenue team dossier.
# =============================================================================
set -euo pipefail

DOSSIER_FILE="data/qa_dossiers/revenue_qa.json"

echo "==> Probing revenue QA dossier..."

if [ ! -f "$DOSSIER_FILE" ]; then
  echo "❌ FAIL: Dossier file '$DOSSIER_FILE' is missing!"
  exit 1
fi

STATUS=$(jq -r '.verification_status' "$DOSSIER_FILE" 2>/dev/null || echo "UNKNOWN")

if [ "$STATUS" != "PASS" ]; then
  echo "❌ FAIL: revenue QA Status is '$STATUS'"
  echo "Unresolved defects:"
  jq -r '.unresolved_defects[]' "$DOSSIER_FILE" 2>/dev/null || echo "None"
  exit 1
fi

echo "✅ revenue QA Dossier Verification Gate Passed."
exit 0
