#!/usr/bin/env bash
# =============================================================================
# epic_fury_security_gate.sh
# Validates security standards and thresholds for Epic Fury 2026.
# =============================================================================
set -euo pipefail

LATEST_RUN_ID_FILE="data/security_scans/epic-fury-2026/latest_run_id"
if [ -f "$LATEST_RUN_ID_FILE" ]; then
  RUN_ID=$(cat "$LATEST_RUN_ID_FILE")
else
  RUN_ID="20260702T233000Z-epic-fury-2026-hasf-vetting"
fi
SCANS_DIR="data/security_scans/epic-fury-2026/${RUN_ID}"


echo "==> Running Epic Fury Security Gate..."

# 1. Check npm audit for critical/high vulns
AUDIT_FILE="${SCANS_DIR}/npm-audit.json"
if [ ! -f "$AUDIT_FILE" ]; then
  echo "❌ FAIL: npm audit file not found at $AUDIT_FILE"
  exit 1
fi

CRIT_COUNT=$(jq '.metadata.vulnerabilities.critical // 0' "$AUDIT_FILE")
HIGH_COUNT=$(jq '.metadata.vulnerabilities.high // 0' "$AUDIT_FILE")

echo "  Critical vulnerabilities: $CRIT_COUNT"
echo "  High vulnerabilities: $HIGH_COUNT"

if [ "$CRIT_COUNT" -ne 0 ] || [ "$HIGH_COUNT" -ne 0 ]; then
  echo "❌ FAIL: Dependency vulnerabilities found."
  exit 1
fi

# 2. Check secret findings (only allow docker-compose & setup-monetization.sh parameter)
GITLEAKS_FILE="${SCANS_DIR}/gitleaks.json"
if [ ! -f "$GITLEAKS_FILE" ]; then
  echo "❌ FAIL: gitleaks.json not found at $GITLEAKS_FILE"
  exit 1
fi

UNACCEPTED_SECRETS=$(jq '[.findings[] | select(.file != "docker-compose.yml" and .file != "docker-compose.dev.yml" and .file != "setup-monetization.sh")] | length' "$GITLEAKS_FILE")

echo "  Unaccepted secrets: $UNACCEPTED_SECRETS"

if [ "$UNACCEPTED_SECRETS" -ne 0 ]; then
  echo "❌ FAIL: Unaccepted secrets found outside permitted developer-mode files."
  exit 1
fi

# 3. Verify SBOM present
SBOM_FILE="${SCANS_DIR}/sbom.cdx.json"
if [ ! -f "$SBOM_FILE" ]; then
  echo "❌ FAIL: SBOM file not found at $SBOM_FILE"
  exit 1
fi

echo "✅ Pass: Security gate passed successfully."
exit 0
