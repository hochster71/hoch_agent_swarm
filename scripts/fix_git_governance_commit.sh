#!/usr/bin/env bash
# Clears the stale git lock and lands the pending HELM governance commit.
# Safe by construction: refuses to touch locks if a real git process is running;
# keeps the nested backup repo (recovered_sources/story-studio-live) OUT of the commit.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # repo root

echo "▸ 1) Safety — no live git process may be running"
if pgrep -x git >/dev/null; then
  echo "  ✗ a 'git' process is running. Wait for it to finish, then re-run. (Not forcing.)"
  exit 1
fi
echo "  ✓ none"

echo "▸ 2) Clear stale lock(s)"
for L in .git/HEAD.lock .git/index.lock; do
  [ -e "$L" ] && { rm -f "$L" && echo "  ✓ removed $L"; } || echo "  · $L absent"
done

echo "▸ 3) Keep the nested backup repo out of the commit (files stay on disk)"
touch .gitignore
grep -qxF 'recovered_sources/story-studio-live/' .gitignore || echo 'recovered_sources/story-studio-live/' >> .gitignore
git rm -r --cached --quiet recovered_sources/story-studio-live 2>/dev/null && echo "  ✓ unstaged embedded repo" || echo "  · nothing to unstage"

echo "▸ 4) Stage the governance set + everything else (embedded repo now ignored)"
git add -A
echo "  files staged:"; git diff --cached --name-only | sed 's/^/    /' | head -40

echo "▸ 5) Commit (this is YOUR founder action)"
git commit -m "HELM governance: Constitution v1.0 RATIFIED + roadmap + EDR-0003/0004 + verification authorization"
echo "  ✓ committed: $(git rev-parse --short HEAD) on $(git branch --show-current)"

echo "▸ DONE. Verify with:  git log --oneline -1"
