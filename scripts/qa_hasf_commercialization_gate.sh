#!/usr/bin/env bash
# =============================================================================
# qa_hasf_commercialization_gate.sh
# Verification gate for the hasf_commercialization team dossier.
# =============================================================================
set -euo pipefail

DOSSIER_FILE="data/qa_dossiers/hasf_commercialization_qa.json"

echo "==> Probing hasf_commercialization QA dossier..."

if [ ! -f "$DOSSIER_FILE" ]; then
  echo "❌ FAIL: Dossier file '$DOSSIER_FILE' is missing!"
  exit 1
fi

STATUS=$(jq -r '.verification_status' "$DOSSIER_FILE" 2>/dev/null || echo "UNKNOWN")

if [ "$STATUS" != "PASS" ]; then
  echo "❌ FAIL: hasf_commercialization QA Status is '$STATUS'"
  echo "Unresolved defects:"
  jq -r '.unresolved_defects[]' "$DOSSIER_FILE" 2>/dev/null || echo "None"
  exit 1
fi

echo "✅ hasf_commercialization QA Dossier Verification Gate Passed."
exit 0
