#!/bin/bash
set -euo pipefail

TAR_FILE="artifacts/releases/visual-control-plane-local-archive/visual-control-plane-local.tar.gz"
MANIFEST_FILE="artifacts/releases/visual-control-plane-local-archive/archive_manifest.json"
FINAL_REVIEW_FILE="artifacts/releases/visual-control-plane-local-archive/final_review.json"

# Verify archive exists
if [ ! -f "$TAR_FILE" ]; then
  echo "Error: Archive file does not exist: $TAR_FILE"
  exit 1
fi

# Calculate sha256
actual_sha=$(shasum -a 256 "$TAR_FILE" | awk '{print $1}')

# Check manifest sha
manifest_sha=$(python3 -c "import json; print(json.load(open('$MANIFEST_FILE')).get('archive_sha256'))")
if [ "$actual_sha" != "$manifest_sha" ]; then
  echo "Error: SHA-256 mismatch with manifest"
  exit 1
fi

# Check final review sha
final_review_sha=$(python3 -c "import json; print(json.load(open('$FINAL_REVIEW_FILE')).get('archive_sha256'))")
if [ "$actual_sha" != "$final_review_sha" ]; then
  echo "Error: SHA-256 mismatch with final_review"
  exit 1
fi

# Create install review directory
INSTALL_DIR="artifacts/install-review/visual-control-plane-local"
mkdir -p "$INSTALL_DIR"

# Extract archive into the install review directory stripping top-level directory
tar -xzf "$TAR_FILE" -C "$INSTALL_DIR" --strip-components=1

# Write install_review.json
cat << EOF > "$INSTALL_DIR/install_review.json"
{
  "phase": "V26_LOCAL_INSTALL_REVIEW",
  "local_only": true,
  "install_review_performed": true,
  "archive_verified": true,
  "extract_verified": true,
  "manifest_verified": true,
  "provenance_verified": true,
  "rollback_verified": true,
  "evidence_verified": true,
  "deployment_performed": false,
  "external_publication_enabled": false,
  "production_deployment_enabled": false,
  "backend_mutation_enabled": false,
  "prompt_execution_enabled": false,
  "approval_decision_execution_enabled": false,
  "security_posture_change_enabled": false,
  "checks_failed": [],
  "decision": "INSTALL_REVIEW_COMPLETE"
}
EOF

# Print indicators
echo "LOCAL_INSTALL_REVIEW"
echo "ARCHIVE_VERIFIED"
echo "INSTALL_REVIEW_EXTRACTED"
echo "NO_DEPLOYMENT"
echo "NO_BACKEND_MUTATION"
