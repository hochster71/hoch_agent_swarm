#!/usr/bin/env bash
# =============================================================================
# qa_customer_outcome_gate.sh
# Verification gate for the customer_outcome team dossier.
# =============================================================================
set -euo pipefail

DOSSIER_FILE="data/qa_dossiers/customer_outcome_qa.json"

echo "==> Probing customer_outcome QA dossier..."

if [ ! -f "$DOSSIER_FILE" ]; then
  echo "❌ FAIL: Dossier file '$DOSSIER_FILE' is missing!"
  exit 1
fi

STATUS=$(jq -r '.verification_status' "$DOSSIER_FILE" 2>/dev/null || echo "UNKNOWN")

if [ "$STATUS" != "PASS" ]; then
  echo "❌ FAIL: customer_outcome QA Status is '$STATUS'"
  echo "Unresolved defects:"
  jq -r '.unresolved_defects[]' "$DOSSIER_FILE" 2>/dev/null || echo "None"
  exit 1
fi

echo "✅ customer_outcome QA Dossier Verification Gate Passed."
exit 0
