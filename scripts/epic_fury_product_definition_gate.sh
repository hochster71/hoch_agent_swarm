#!/usr/bin/env bash
# =============================================================================
# epic_fury_product_definition_gate.sh
# Validates the existence and contents of the product definition files.
# =============================================================================
set -euo pipefail

echo "==> Running Epic Fury Product Definition Gate..."

DOCS_DIR="docs/products/epic-fury-2026"

# Check file existence
for f in PRODUCT_BRIEF.md FOUNDER_INTENT.md SHIP_CRITERIA.md HASF_PRODUCT_GATE.md; do
  if [ ! -f "${DOCS_DIR}/${f}" ]; then
    echo "❌ FAIL: Missing product definition document: ${DOCS_DIR}/${f}"
    exit 1
  fi
done

# Verify crucial patterns in documents
grep -q "Target User" "${DOCS_DIR}/PRODUCT_BRIEF.md" || { echo "❌ FAIL: Target User definition missing."; exit 1; }
grep -q "High-Priority Exclusions" "${DOCS_DIR}/FOUNDER_INTENT.md" || { echo "❌ FAIL: High-Priority Exclusions missing."; exit 1; }
grep -q "Quality & Performance Thresholds" "${DOCS_DIR}/SHIP_CRITERIA.md" || { echo "❌ FAIL: Quality Thresholds missing."; exit 1; }

echo "✅ Pass: Product definition gate check successful."
exit 0
