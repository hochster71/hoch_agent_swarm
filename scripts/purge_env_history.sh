#!/bin/bash
# =============================================================================
# purge_env_history.sh — permanently remove .env from ALL git history.
# Per GitHub's guidance: ROTATE THE SECRETS FIRST — history rewrite is the
# second step, not the first. https://docs.github.com/en/authentication/
#   keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
# DESTRUCTIVE: rewrites every commit SHA and force-pushes. Backup is taken.
# =============================================================================
set -euo pipefail
REPO="$HOME/hoch_agent_swarm"
BACKUP="$HOME/hoch_agent_swarm_backup_$(date +%Y%m%d%H%M%S).git"

echo "== Preflight =="
command -v git-filter-repo >/dev/null 2>&1 || {
  echo "Installing git-filter-repo (brew)..."; brew install git-filter-repo; }

read -r -p "Have you ROTATED the Stripe keys + Drogon password already? (yes/no) " ROT
[ "$ROT" = "yes" ] || { echo "Rotate first (Stripe Dashboard > Developers > API keys). Aborting."; exit 1; }

cd "$REPO"
[ -z "$(git status --porcelain)" ] || { echo "Working tree dirty — commit or stash first. Aborting."; exit 1; }

echo "== Backup (bare mirror) -> $BACKUP =="
git clone --mirror . "$BACKUP"

echo "== Rewriting history: dropping .env from all refs =="
git filter-repo --path .env --invert-paths --force

echo "== Re-adding remote (filter-repo removes it as a safety measure) =="
git remote add github https://github.com/hochster71/hoch_agent_swarm.git

echo "== Verify: .env should appear in ZERO commits =="
COUNT=$(git log --all --oneline -- .env | wc -l | tr -d ' ')
echo "commits touching .env after rewrite: $COUNT"
[ "$COUNT" = "0" ] || { echo "Rewrite incomplete. DO NOT PUSH."; exit 1; }

read -r -p "Force-push rewritten history to github (type PUSH to confirm): " GO
if [ "$GO" = "PUSH" ]; then
  git push github --force --all
  git push github --force --tags
  echo "Done. Old commits may remain cached on GitHub's side —"
  echo "contact GitHub Support to purge cached views if the repo was ever public/shared."
else
  echo "Skipped push. Run 'git push github --force --all && git push github --force --tags' when ready."
fi
