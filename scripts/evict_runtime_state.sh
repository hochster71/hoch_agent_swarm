#!/bin/bash
# H3: remove tracked build/release binaries from the git index (keep on disk).
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== Untracking release archives/zips (files remain on disk) =="
git rm --cached --ignore-unmatch \
  'dist/releases/*.tar.gz' \
  'dist/releases/**/*.zip' \
  'artifacts/releases/visual-control-plane-local-archive/visual-control-plane-local.tar.gz' \
  2>/dev/null || true
echo "== Remaining tracked archives (should be empty) =="
git ls-files | grep -E '\.(tar\.gz|zip)$' || echo "  none"
echo "Done. Commit the removals; publish release binaries via GitHub Releases instead."
