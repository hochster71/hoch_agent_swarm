#!/usr/bin/env bash
# =============================================================================
# qa_backup_recovery_gate.sh
# Verification gate for the backup_recovery team dossier.
# =============================================================================
set -euo pipefail

DOSSIER_FILE="data/qa_dossiers/backup_recovery_qa.json"

echo "==> Probing backup_recovery QA dossier..."

if [ ! -f "$DOSSIER_FILE" ]; then
  echo "❌ FAIL: Dossier file '$DOSSIER_FILE' is missing!"
  exit 1
fi

STATUS=$(jq -r '.verification_status' "$DOSSIER_FILE" 2>/dev/null || echo "UNKNOWN")

if [ "$STATUS" != "PASS" ]; then
  echo "❌ FAIL: backup_recovery QA Status is '$STATUS'"
  echo "Unresolved defects:"
  jq -r '.unresolved_defects[]' "$DOSSIER_FILE" 2>/dev/null || echo "None"
  exit 1
fi

echo "✅ backup_recovery QA Dossier Verification Gate Passed."
exit 0
