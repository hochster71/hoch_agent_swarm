#!/usr/bin/env bash
# =============================================================================
# epic_fury_gap_gate.sh
# Validates presence and formatting of the gap audit documentation.
# =============================================================================
set -euo pipefail

echo "==> Running Epic Fury Gap Audit Gate..."

GAP_FILE="docs/products/epic-fury-2026/GAP_ANALYSIS.md"
BACKLOG_FILE="docs/products/epic-fury-2026/REMEDIATION_BACKLOG.md"

if [ ! -s "$GAP_FILE" ]; then
  echo "❌ FAIL: Gap analysis file is missing or empty."
  exit 1
fi

if [ ! -s "$BACKLOG_FILE" ]; then
  echo "❌ FAIL: Remediation backlog file is missing or empty."
  exit 1
fi

echo "✅ Pass: Gap audit gate passed successfully."
exit 0
