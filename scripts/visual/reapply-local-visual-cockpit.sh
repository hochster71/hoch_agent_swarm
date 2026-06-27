#!/bin/bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DECISION_JSON="$BASE_DIR/artifacts/qa/visual_review/operator_post_rollback_decision.json"
CANDIDATE_PATH="$BASE_DIR/artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html"

# 1. Verification checks
if [ ! -f "$DECISION_JSON" ]; then
  echo "Operator post rollback decision record not found: $DECISION_JSON"
  exit 1
fi

DECISION=$(python3 -c "import json; print(json.load(open('$DECISION_JSON'))['decision'])")
if [ "$DECISION" != "REAPPLY_VISUAL_COCKPIT_LOCALLY" ]; then
  echo "Invalid operator decision: $DECISION. Must be REAPPLY_VISUAL_COCKPIT_LOCALLY"
  exit 1
fi

if [ ! -f "$CANDIDATE_PATH" ]; then
  echo "Staged candidate cockpit not found: $CANDIDATE_PATH"
  exit 1
fi

# 2. Reapply preparation
BACKUP_ROOT="$BASE_DIR/artifacts/qa/visual_review/reapply_backups"
ROLLBACK_ROOT="$BASE_DIR/artifacts/qa/visual_review/reapply_local"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$BACKUP_ROOT/backup_$TIMESTAMP"

echo "Staging reapply environment..."
mkdir -p "$BACKUP_DIR"
mkdir -p "$ROLLBACK_ROOT"

# 3. Create backup before substitution
cp "$BASE_DIR/mockups/visual-control-plane/control-plane.html" "$BACKUP_DIR/control-plane.html.backup"

# 4. Copy candidate to mockups cockpit
cp "$CANDIDATE_PATH" "$BASE_DIR/mockups/visual-control-plane/control-plane.html"

# 5. Generate ROLLBACK.md instructions
cat << EOF > "$ROLLBACK_ROOT/ROLLBACK.md"
# Active Reapply Rollback Procedure

To roll back the reapplied cockpit configuration:
\`\`\`bash
cp "$BACKUP_DIR/control-plane.html.backup" "$BASE_DIR/mockups/visual-control-plane/control-plane.html"
\`\`\`
EOF

# 6. Output reapply_local_visual_cockpit_report.json
cat << EOF > "$BASE_DIR/artifacts/qa/visual_review/reapply_local_visual_cockpit_report.json"
{
  "phase": "V18_REAPPLY_LOCAL_VISUAL_COCKPIT",
  "local_only": true,
  "reapply_performed": true,
  "backup_created": true,
  "rollback_ready": true,
  "backend_mutation_enabled": false,
  "prompt_execution_enabled": false,
  "approval_decision_execution_enabled": false,
  "decision": "REAPPLY_LOCAL_VISUAL_COCKPIT_COMPLETE"
}
EOF

# 7. Print Safety Identifiers
echo "--------------------------------------------------"
echo "REAPPLY_LOCAL_VISUAL_COCKPIT"
echo "LOCAL_ONLY"
echo "BACKUP_CREATED"
echo "ROLLBACK_READY"
echo "NO_BACKEND_MUTATION"
echo "--------------------------------------------------"
EOF_STATUS=0
exit $EOF_STATUS
