#!/bin/bash
set -euo pipefail

# 1. Verification of paths
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_ROOT="$BASE_DIR/artifacts/qa/visual_review/active_substitution_backups"
ROLLBACK_ROOT="$BASE_DIR/artifacts/qa/visual_review/active_substitution"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$BACKUP_ROOT/backup_$TIMESTAMP"

echo "Staging active substitution environments..."
mkdir -p "$BACKUP_DIR"
mkdir -p "$ROLLBACK_ROOT"

# 2. Copy baseline cockpit control-plane.html to timestamped backup
cp "$BASE_DIR/mockups/visual-control-plane/control-plane.html" "$BACKUP_DIR/control-plane.html.backup"

# 3. Copy candidate cockpit to mockups control-plane.html (substitution)
cp "$BASE_DIR/artifacts/qa/visual_review/dry_run_candidate/control-plane.candidate.html" "$BASE_DIR/mockups/visual-control-plane/control-plane.html"

# 4. Generate ROLLBACK.md instructions
cat << EOF > "$ROLLBACK_ROOT/ROLLBACK.md"
# Active Substitution Rollback Procedure

To roll back the active substitution:
\`\`\`bash
cp "$BACKUP_DIR/control-plane.html.backup" "$BASE_DIR/mockups/visual-control-plane/control-plane.html"
\`\`\`
EOF

# 5. Output controlled_local_substitution_report.json
cat << EOF > "$BASE_DIR/artifacts/qa/visual_review/controlled_local_substitution_report.json"
{
  "phase": "V15_CONTROLLED_LOCAL_SUBSTITUTION",
  "local_only": true,
  "substitution_performed": true,
  "backup_created": true,
  "rollback_ready": true,
  "backend_mutation_enabled": false,
  "prompt_execution_enabled": false,
  "approval_decision_execution_enabled": false,
  "decision": "CONTROLLED_LOCAL_SUBSTITUTION_COMPLETE"
}
EOF

# 6. Safety Print Statements
echo "--------------------------------------------------"
echo "CONTROLLED_LOCAL_SUBSTITUTION"
echo "LOCAL_ONLY"
echo "BACKUP_CREATED"
echo "ROLLBACK_READY"
echo "NO_BACKEND_MUTATION"
echo "--------------------------------------------------"
EOF_STATUS=0
exit $EOF_STATUS
