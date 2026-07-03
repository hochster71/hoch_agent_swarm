#!/usr/bin/env bash
# =============================================================================
# epic_fury_shipping_gate.sh
# Master gate validating that all sub-gates and shipping files pass.
# =============================================================================
set -euo pipefail

echo "==> Running Master Epic Fury Shipping Gate..."

# Execute sub-gates
./scripts/epic_fury_repo_access_gate.sh
./scripts/epic_fury_product_definition_gate.sh
./scripts/epic_fury_build_test_gate.sh
./scripts/epic_fury_ui_ux_gate.sh
./scripts/epic_fury_security_gate.sh
./scripts/epic_fury_gap_gate.sh

# Verify presence of all release files
SHIPPING_FILES=(
  "docs/products/epic-fury-2026/KNOWN_LIMITATIONS.md"
  "docs/products/epic-fury-2026/RELEASE_CHECKLIST.md"
  "docs/products/epic-fury-2026/DEPLOYMENT_PLAN.md"
  "docs/products/epic-fury-2026/ROLLBACK_PLAN.md"
  "docs/products/epic-fury-2026/FOUNDER_RELEASE_DECISION.md"
  "docs/products/epic-fury-2026/FINAL_SHIPPING_REPORT.md"
)

for file in "${SHIPPING_FILES[@]}"; do
  if [ ! -s "$file" ]; then
    echo "❌ FAIL: Shipping artifact '$file' is missing or empty."
    exit 1
  fi
done

echo "✅ PASS: Master Shipping Gate Passed. Ready for Founder Review."
exit 0
