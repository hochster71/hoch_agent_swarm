#!/bin/bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROLLBACK_MD="$BASE_DIR/artifacts/qa/visual_review/active_substitution/ROLLBACK.md"

if [ ! -f "$ROLLBACK_MD" ]; then
  echo "Rollback instruction file not found: $ROLLBACK_MD"
  exit 1
fi

# Extract command lines containing 'cp'
ROLLBACK_CMD=$(grep "cp " "$ROLLBACK_MD" | sed 's/```bash//g' | sed 's/```//g' | xargs)
echo "Extracted rollback command: $ROLLBACK_CMD"

# Extract backup path (second argument in the command)
BACKUP_PATH=$(echo "$ROLLBACK_CMD" | awk '{print $2}' | tr -d '"')

if [ ! -f "$BACKUP_PATH" ]; then
  echo "Backup file does not exist: $BACKUP_PATH"
  exit 1
fi

# Execute rollback
eval "$ROLLBACK_CMD"

# Verify restoration
if ! diff "$BACKUP_PATH" "$BASE_DIR/mockups/visual-control-plane/control-plane.html" >/dev/null; then
  echo "Validation failed: restored control-plane.html differs from backup!"
  exit 1
fi

# Update config & report values
cat << EOF > "$BASE_DIR/artifacts/qa/visual_review/local_substitution_rollback_proof_report.json"
{
  "phase": "V16_LOCAL_SUBSTITUTION_VALIDATION_AND_ROLLBACK_PROOF",
  "local_only": true,
  "rollback_executed": true,
  "baseline_restored": true,
  "backend_mutation_enabled": false,
  "prompt_execution_enabled": false,
  "approval_decision_execution_enabled": false,
  "decision": "ROLLBACK_PROOF_COMPLETE"
}
EOF

# Update config state
cat << EOF > "$BASE_DIR/config/visual_rollback_proof.json"
{
  "phase": "V16_LOCAL_SUBSTITUTION_VALIDATION_AND_ROLLBACK_PROOF",
  "local_only": true,
  "rollback_required": true,
  "rollback_executed": true,
  "baseline_restored": true,
  "backend_mutation_enabled": false,
  "prompt_execution_enabled": false,
  "approval_decision_execution_enabled": false,
  "external_publication_enabled": false,
  "production_deployment_enabled": false,
  "security_posture_change_enabled": false,
  "rollback_path": "artifacts/qa/visual_review/active_substitution/ROLLBACK.md",
  "baseline_cockpit_path": "mockups/visual-control-plane/control-plane.html",
  "next_allowed_phase": "V17_OPERATOR_POST_ROLLBACK_DECISION"
}
EOF

echo "--------------------------------------------------"
echo "ROLLBACK_PROOF"
echo "BASELINE_RESTORED"
echo "LOCAL_ONLY"
echo "NO_BACKEND_MUTATION"
echo "--------------------------------------------------"
EOF_STATUS=0
exit $EOF_STATUS
