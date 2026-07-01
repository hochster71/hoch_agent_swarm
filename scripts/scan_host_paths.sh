#!/usr/bin/env bash
# scan_host_paths.sh - Scans production codebase for host path contamination (/Users/michaelhoch)

echo "==> Scanning codebase for host path contamination..."

# Find occurrences of /Users/michaelhoch in backend production code
matches=$(grep -rn "/Users/michaelhoch" ./backend \
  --exclude-dir=tests \
  --exclude-dir=.venv \
  --exclude-dir=.git \
  --exclude-dir=dummy_mcp \
  --exclude-dir=scripts \
  --exclude-dir=__pycache__ \
  --exclude="*.db" \
  --exclude="*.pyc" || true)

if [ -n "$matches" ]; then
  echo "FAIL: Found host path contamination in production backend:"
  echo "$matches"
  exit 1
fi

echo "[PASS] Host path contamination scan clean"
exit 0
