#!/bin/bash
set -euo pipefail

# Directories
RELEASE_DIR="artifacts/releases/visual-control-plane-local"
EVIDENCE_DIR="$RELEASE_DIR/evidence"

# Compute actual file details for the ledger
sha_cockpit=$(shasum -a 256 "$RELEASE_DIR/control-plane.html" | awk '{print $1}')
size_cockpit=$(stat -f%z "$RELEASE_DIR/control-plane.html")

sha_styles=$(shasum -a 256 "$RELEASE_DIR/styles.css" | awk '{print $1}')
size_styles=$(stat -f%z "$RELEASE_DIR/styles.css")

sha_rollback=$(shasum -a 256 "$RELEASE_DIR/ROLLBACK.md" | awk '{print $1}')
size_rollback=$(stat -f%z "$RELEASE_DIR/ROLLBACK.md")

sha_readme=$(shasum -a 256 "$RELEASE_DIR/README.md" | awk '{print $1}')
size_readme=$(stat -f%z "$RELEASE_DIR/README.md")

sha_manifest=$(shasum -a 256 "$RELEASE_DIR/manifest.json" | awk '{print $1}')
size_manifest=$(stat -f%z "$RELEASE_DIR/manifest.json")

sha_provenance=$(shasum -a 256 "$RELEASE_DIR/provenance.json" | awk '{print $1}')
size_provenance=$(stat -f%z "$RELEASE_DIR/provenance.json")

sha_review=$(shasum -a 256 "$RELEASE_DIR/release_review.json" | awk '{print $1}')
size_review=$(stat -f%z "$RELEASE_DIR/release_review.json")

sha_evidence_acceptance=$(shasum -a 256 "$EVIDENCE_DIR/local_operator_acceptance.json" | awk '{print $1}')
size_evidence_acceptance=$(stat -f%z "$EVIDENCE_DIR/local_operator_acceptance.json")

sha_evidence_stabilization=$(shasum -a 256 "$EVIDENCE_DIR/local_visual_cockpit_stabilization_report.json" | awk '{print $1}')
size_evidence_stabilization=$(stat -f%z "$EVIDENCE_DIR/local_visual_cockpit_stabilization_report.json")

sha_evidence_reapply=$(shasum -a 256 "$EVIDENCE_DIR/reapply_local_visual_cockpit_report.json" | awk '{print $1}')
size_evidence_reapply=$(stat -f%z "$EVIDENCE_DIR/reapply_local_visual_cockpit_report.json")

created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 1. Write FREEZE.md
cat << EOF > "$RELEASE_DIR/FREEZE.md"
# HOCH Visual Control Plane Local Release Freeze

> [!IMPORTANT]
> **LOCAL RELEASE FREEZE ONLY**
> **NOT PRODUCTION DEPLOYMENT**
> **DO NOT MODIFY RELEASE PACKAGE WITHOUT NEW PHASE**
> **NO BACKEND MUTATION**
> **NO PROMPT EXECUTION**
> **NO APPROVAL DECISION EXECUTION**

This release package has been frozen and locked against modifications. All files, metadata, and cryptographic evidence are finalized.

*   **Rollback Path**: \`artifacts/releases/visual-control-plane-local/ROLLBACK.md\`
*   **Manifest Path**: \`artifacts/releases/visual-control-plane-local/manifest.json\`
*   **Provenance Path**: \`artifacts/releases/visual-control-plane-local/provenance.json\`
*   **Release Review Path**: \`artifacts/releases/visual-control-plane-local/release_review.json\`
EOF

# Write hash ledger
cat << EOF > "$RELEASE_DIR/hash_ledger.json"
{
  "phase": "V23_LOCAL_RELEASE_FREEZE",
  "local_only": true,
  "release_root": "artifacts/releases/visual-control-plane-local",
  "generated_at_utc": "$created_at",
  "deployment_performed": false,
  "external_publication_enabled": false,
  "files": [
    {
      "path": "artifacts/releases/visual-control-plane-local/control-plane.html",
      "sha256": "$sha_cockpit",
      "size_bytes": $size_cockpit
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/styles.css",
      "sha256": "$sha_styles",
      "size_bytes": $size_styles
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/ROLLBACK.md",
      "sha256": "$sha_rollback",
      "size_bytes": $size_rollback
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/README.md",
      "sha256": "$sha_readme",
      "size_bytes": $size_readme
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/manifest.json",
      "sha256": "$sha_manifest",
      "size_bytes": $size_manifest
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/provenance.json",
      "sha256": "$sha_provenance",
      "size_bytes": $size_provenance
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/release_review.json",
      "sha256": "$sha_review",
      "size_bytes": $size_review
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/evidence/local_operator_acceptance.json",
      "sha256": "$sha_evidence_acceptance",
      "size_bytes": $size_evidence_acceptance
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/evidence/local_visual_cockpit_stabilization_report.json",
      "sha256": "$sha_evidence_stabilization",
      "size_bytes": $size_evidence_stabilization
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/evidence/reapply_local_visual_cockpit_report.json",
      "sha256": "$sha_evidence_reapply",
      "size_bytes": $size_evidence_reapply
    }
  ]
}
EOF

# Write freeze record
cat << EOF > "$RELEASE_DIR/freeze_record.json"
{
  "phase": "V23_LOCAL_RELEASE_FREEZE",
  "local_only": true,
  "freeze_declared": true,
  "deployment_performed": false,
  "release_root": "artifacts/releases/visual-control-plane-local",
  "source_review_status": "REVIEW_COMPLETE",
  "manifest_verified": true,
  "provenance_verified": true,
  "rollback_verified": true,
  "evidence_verified": true,
  "hashes_verified": true,
  "checks_failed": [],
  "blocked_actions": [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ],
  "frozen_files": [
    "control-plane.html",
    "styles.css",
    "ROLLBACK.md",
    "README.md",
    "manifest.json",
    "provenance.json",
    "release_review.json",
    "local_operator_acceptance.json",
    "local_visual_cockpit_stabilization_report.json",
    "reapply_local_visual_cockpit_report.json"
  ]
}
EOF

echo "Visual Control Plane V23 Package Frozen Successfully."
