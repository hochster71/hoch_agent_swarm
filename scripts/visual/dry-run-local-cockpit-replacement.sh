#!/bin/bash
set -euo pipefail

# 1. Verification of paths
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_ROOT="$BASE_DIR/artifacts/qa/visual_review/dry_run_backups"
CANDIDATE_ROOT="$BASE_DIR/artifacts/qa/visual_review/dry_run_candidate"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$BACKUP_ROOT/backup_$TIMESTAMP"

echo "Staging dry-run environments..."
mkdir -p "$BACKUP_DIR"
mkdir -p "$CANDIDATE_ROOT"

# 2. Copy baseline cockpit control-plane.html to timestamped backup
cp "$BASE_DIR/mockups/visual-control-plane/control-plane.html" "$BACKUP_DIR/control-plane.html.backup"

# 3. Copy dashboard-preview.html to staging candidate
cp "$BASE_DIR/mockups/visual-control-plane/dashboard-preview.html" "$CANDIDATE_ROOT/control-plane.candidate.html"

# 4. Generate ROLLBACK.md instructions
cat << EOF > "$CANDIDATE_ROOT/ROLLBACK.md"
# Dry Run Rollback Procedure

To roll back a mock replacement of the control plane:
\`\`\`bash
cp "$BACKUP_DIR/control-plane.html.backup" "$BASE_DIR/mockups/visual-control-plane/control-plane.html"
\`\`\`
EOF

# 5. Output local_replacement_dry_run_report.json
cat << EOF > "$BASE_DIR/artifacts/qa/visual_review/local_replacement_dry_run_report.json"
{
  "phase": "V12_LOCAL_REPLACEMENT_DRY_RUN",
  "dry_run_only": true,
  "replacement_performed": false,
  "active_cockpit_replacement_enabled": false,
  "backup_created": true,
  "candidate_created": true,
  "rollback_ready": true,
  "baseline_unchanged": true,
  "decision": "DRY_RUN_COMPLETE"
}
EOF

# 6. Safety Print Statements
echo "--------------------------------------------------"
echo "DRY_RUN_ONLY"
echo "NO_ACTIVE_REPLACEMENT"
echo "ROLLBACK_READY"
echo "--------------------------------------------------"
EOF_STATUS=0
exit $EOF_STATUS
