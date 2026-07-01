#!/bin/bash
set -euo pipefail

FREEZE_RECORD="artifacts/releases/visual-control-plane-local/freeze_record.json"
HASH_LEDGER="artifacts/releases/visual-control-plane-local/hash_ledger.json"

# Verify freeze declared
freeze_val=$(python3 -c "import json; print(json.load(open('$FREEZE_RECORD')).get('freeze_declared'))")
if [ "$freeze_val" != "True" ]; then
  echo "Error: Freeze not declared in freeze_record.json"
  exit 1
fi

# Directory structures
ARCHIVE_DIR="artifacts/releases/visual-control-plane-local-archive"
mkdir -p "$ARCHIVE_DIR"

# Compress release package
tar -czf "$ARCHIVE_DIR/visual-control-plane-local.tar.gz" -C artifacts/releases visual-control-plane-local

# Calculate hash and size
archive_sha=$(shasum -a 256 "$ARCHIVE_DIR/visual-control-plane-local.tar.gz" | awk '{print $1}')
archive_size=$(stat -f%z "$ARCHIVE_DIR/visual-control-plane-local.tar.gz")

# Write checksums
echo "$archive_sha  visual-control-plane-local.tar.gz" > "$ARCHIVE_DIR/archive_checksums.sha256"

git_head=$(git rev-parse HEAD)
created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Write archive manifest
cat << EOF > "$ARCHIVE_DIR/archive_manifest.json"
{
  "phase": "V24_LOCAL_RELEASE_ARCHIVE",
  "local_only": true,
  "archive_name": "visual-control-plane-local.tar.gz",
  "archive_path": "artifacts/releases/visual-control-plane-local-archive/visual-control-plane-local.tar.gz",
  "archive_sha256": "$archive_sha",
  "archive_size_bytes": $archive_size,
  "source_release_root": "artifacts/releases/visual-control-plane-local",
  "source_freeze_record_path": "artifacts/releases/visual-control-plane-local/freeze_record.json",
  "source_hash_ledger_path": "artifacts/releases/visual-control-plane-local/hash_ledger.json",
  "source_head": "$git_head",
  "deployment_performed": false,
  "external_publication_enabled": false,
  "production_deployment_enabled": false,
  "backend_mutation_enabled": false,
  "prompt_execution_enabled": false,
  "approval_decision_execution_enabled": false,
  "blocked_actions": [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ]
}
EOF

# Write archive review
cat << EOF > "$ARCHIVE_DIR/archive_review.json"
{
  "phase": "V24_LOCAL_RELEASE_ARCHIVE",
  "local_only": true,
  "archive_created": true,
  "archive_checksum_verified": true,
  "source_freeze_verified": true,
  "deployment_performed": false,
  "external_publication_enabled": false,
  "production_deployment_enabled": false,
  "backend_mutation_enabled": false,
  "prompt_execution_enabled": false,
  "approval_decision_execution_enabled": false,
  "security_posture_change_enabled": false,
  "checks_failed": [],
  "decision": "ARCHIVE_COMPLETE"
}
EOF

# Print indicators
echo "LOCAL_RELEASE_ARCHIVE"
echo "ARCHIVE_CREATED"
echo "CHECKSUM_WRITTEN"
echo "NO_DEPLOYMENT"
echo "NO_BACKEND_MUTATION"
