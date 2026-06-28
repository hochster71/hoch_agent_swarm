#!/bin/bash
set -euo pipefail

# Directories
RELEASE_DIR="artifacts/releases/visual-control-plane-local"
EVIDENCE_DIR="$RELEASE_DIR/evidence"

mkdir -p "$RELEASE_DIR"
mkdir -p "$EVIDENCE_DIR"

# Copy files
cp mockups/visual-control-plane/control-plane.html "$RELEASE_DIR/"
cp mockups/visual-control-plane/styles.css "$RELEASE_DIR/"

# Copy evidence
cp artifacts/qa/visual_review/local_operator_acceptance.json "$EVIDENCE_DIR/"
cp artifacts/qa/visual_review/local_visual_cockpit_stabilization_report.json "$EVIDENCE_DIR/"
cp artifacts/qa/visual_review/reapply_local_visual_cockpit_report.json "$EVIDENCE_DIR/"

# Rollback instructions
cat << 'EOF' > "$RELEASE_DIR/ROLLBACK.md"
# Local Visual Cockpit Package Rollback Instructions

To roll back the local release package cockpit and restore the baseline control plane:
```bash
cp "artifacts/qa/visual_review/reapply_backups/backup_20260627_152229/control-plane.html.backup" "mockups/visual-control-plane/control-plane.html"
```
EOF

# README
cat << 'EOF' > "$RELEASE_DIR/README.md"
# HOCH Visual Control Plane Local Release Package

> [!IMPORTANT]
> **LOCAL RELEASE PACKAGE ONLY**
> **NOT PRODUCTION DEPLOYMENT**
> **NO BACKEND MUTATION**
> **NO PROMPT EXECUTION**
> **NO APPROVAL DECISION EXECUTION**

This release package contains the accepted local visual cockpit mockup along with all cryptographic validation evidence, QA references, and rollback instructions.

*   **Accepted Cockpit Path**: `mockups/visual-control-plane/control-plane.html`
*   **Rollback Command Location**: `artifacts/releases/visual-control-plane-local/ROLLBACK.md`
EOF

# Calculate SHAs
sha_cockpit=$(shasum -a 256 "$RELEASE_DIR/control-plane.html" | awk '{print $1}')
sha_styles=$(shasum -a 256 "$RELEASE_DIR/styles.css" | awk '{print $1}')
sha_rollback=$(shasum -a 256 "$RELEASE_DIR/ROLLBACK.md" | awk '{print $1}')
sha_readme=$(shasum -a 256 "$RELEASE_DIR/README.md" | awk '{print $1}')

sha_evidence_acceptance=$(shasum -a 256 "$EVIDENCE_DIR/local_operator_acceptance.json" | awk '{print $1}')
sha_evidence_stabilization=$(shasum -a 256 "$EVIDENCE_DIR/local_visual_cockpit_stabilization_report.json" | awk '{print $1}')
sha_evidence_reapply=$(shasum -a 256 "$EVIDENCE_DIR/reapply_local_visual_cockpit_report.json" | awk '{print $1}')

git_branch=$(git branch --show-current)
git_head=$(git rev-parse HEAD)
created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Manifest
cat << EOF > "$RELEASE_DIR/manifest.json"
{
  "phase": "V21_LOCAL_RELEASE_PACKAGE",
  "local_only": true,
  "package_name": "visual-control-plane-local",
  "package_type": "local_release_package",
  "deployment_performed": false,
  "files": [
    {
      "path": "artifacts/releases/visual-control-plane-local/control-plane.html",
      "role": "cockpit",
      "sha256": "$sha_cockpit"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/styles.css",
      "role": "stylesheet",
      "sha256": "$sha_styles"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/ROLLBACK.md",
      "role": "rollback_instructions",
      "sha256": "$sha_rollback"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/README.md",
      "role": "readme",
      "sha256": "$sha_readme"
    }
  ],
  "evidence": [
    {
      "path": "artifacts/releases/visual-control-plane-local/evidence/local_operator_acceptance.json",
      "role": "local_operator_acceptance",
      "sha256": "$sha_evidence_acceptance"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/evidence/local_visual_cockpit_stabilization_report.json",
      "role": "local_visual_cockpit_stabilization_report",
      "sha256": "$sha_evidence_stabilization"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/evidence/reapply_local_visual_cockpit_report.json",
      "role": "reapply_local_visual_cockpit_report",
      "sha256": "$sha_evidence_reapply"
    }
  ],
  "blocked_actions": [
    "backend mutation",
    "prompt execution",
    "approval decision execution",
    "production deployment",
    "external publication",
    "security posture change"
  ],
  "rollback_path": "artifacts/releases/visual-control-plane-local/ROLLBACK.md",
  "accepted_commit_head": "$git_head"
}
EOF

# Provenance
cat << EOF > "$RELEASE_DIR/provenance.json"
{
  "phase": "V21_LOCAL_RELEASE_PACKAGE",
  "builder": "HOCH Agent Swarm Antigravity local workflow",
  "source_branch": "$git_branch",
  "source_head": "$git_head",
  "created_at_utc": "$created_at",
  "input_artifacts": [
    {
      "path": "mockups/visual-control-plane/control-plane.html",
      "sha256": "$sha_cockpit"
    },
    {
      "path": "mockups/visual-control-plane/styles.css",
      "sha256": "$sha_styles"
    }
  ],
  "output_artifacts": [
    {
      "path": "artifacts/releases/visual-control-plane-local/control-plane.html",
      "sha256": "$sha_cockpit"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/styles.css",
      "sha256": "$sha_styles"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/manifest.json"
    },
    {
      "path": "artifacts/releases/visual-control-plane-local/provenance.json"
    }
  ],
  "qa_commands": [
    "npm run qa:visual-local-release-package"
  ],
  "ci_command": "npm run ci:validate",
  "deployment_performed": false,
  "external_publication_enabled": false
}
EOF

echo "Visual Control Plane V21 Package Built Successfully."
