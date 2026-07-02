#!/usr/bin/env bash
# =============================================================================
# qa_secrets_identity_gate.sh
# Verification gate for the secrets_identity team dossier.
# =============================================================================
set -euo pipefail

DOSSIER_FILE="data/qa_dossiers/secrets_identity_qa.json"

echo "==> Probing secrets_identity QA dossier..."

if [ ! -f "$DOSSIER_FILE" ]; then
  echo "❌ FAIL: Dossier file '$DOSSIER_FILE' is missing!"
  exit 1
fi

STATUS=$(jq -r '.verification_status' "$DOSSIER_FILE" 2>/dev/null || echo "UNKNOWN")

if [ "$STATUS" != "PASS" ]; then
  echo "❌ FAIL: secrets_identity QA Status is '$STATUS'"
  echo "Unresolved defects:"
  jq -r '.unresolved_defects[]' "$DOSSIER_FILE" 2>/dev/null || echo "None"
  exit 1
fi

echo "✅ secrets_identity QA Dossier Verification Gate Passed."
exit 0
