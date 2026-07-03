#!/usr/bin/env bash
# =============================================================================
# github_actions_hardening_gate.sh
# Verifies GitHub Actions workflows adhere to hardening guidelines.
# =============================================================================
set -euo pipefail

echo "==> Running GitHub Actions Hardening Gate..."

WORKFLOW_DIR=".github/workflows"

if [ -d "$WORKFLOW_DIR" ]; then
  for wf in "$WORKFLOW_DIR"/*.yml; do
    if [ -f "$wf" ]; then
      # Check for potential secret leak via echo
      if grep -qi "echo.*secrets" "$wf"; then
        echo "❌ FAIL: Workflow '$wf' contains potential secret echo leak!"
        exit 1
      fi
    fi
  done
fi

echo "✅ GitHub Actions Hardening Gate Passed."
exit 0
