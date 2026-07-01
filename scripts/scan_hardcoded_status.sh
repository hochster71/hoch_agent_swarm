#!/usr/bin/env bash
# scan_hardcoded_status.sh - Scans the codebase for static hardcoded status overrides

echo "==> Scanning codebase for hardcoded status overrides..."

# Simple check to find potential static status indicators in HTML files that should be dynamic
grep -rnw "./frontend" -e "status-value" || true

echo "==> Static check completed successfully."
exit 0
