#!/bin/bash
# Install HOCH's version-controlled git hooks into .git/hooks.
# Idempotent. Run after clone (the hooks are the "prevent repeats" secret gate).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/scripts/git-hooks"
DST="$ROOT/.git/hooks"

[ -d "$DST" ] || { echo "no .git/hooks (not a git checkout?)"; exit 1; }
for hook in "$SRC"/*; do
    name="$(basename "$hook")"
    cp "$hook" "$DST/$name"
    chmod +x "$DST/$name"
    echo "installed $name -> .git/hooks/$name"
done
echo "done. secret pre-commit gate active."
