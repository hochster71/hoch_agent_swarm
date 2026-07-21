#!/usr/bin/env bash
#
#  ############  SUPERSEDED — DO NOT RUN  ############
#
#  Superseded 2026-07-20 by docs/release/rc23_branch_protection_runbook.md
#  (authored 2026-06-28, on branch rc23-branch-protection-and-deployment-readiness).
#
#  This script conflicts with that pre-existing design in three material ways:
#    1. targets helm/promotion-candidate     — the runbook protects `master`
#    2. sets required_status_checks=null     — the runbook requires the RC22 provenance check
#    3. omits signed-commit enforcement      — the runbook REQUIRES it, and signed commits are
#                                              the control that addresses GOV-007 attribution
#
#  Running it would install a weaker policy on a different ref and leave the attribution gap
#  open. helm/promotion-candidate may itself be redundant: the runbook already defines the
#  promotion lane as rcXX -> local validation -> CI+signing -> tag -> PR -> protected master.
#
#  Retained as a record of what was proposed before the existing design was discovered.
#
#  ###################################################
#
# protect_governance_refs.sh — enable GitHub branch protection on the governance refs.
#
# WHY: three commits landed during active review leases on 2026-07-20, the last opening a
# lease under another session's identity. Every repo-local control built this session
# (lease, drift gate, CAS, freeze marker) is writable by the actor it constrains. Branch
# protection is the first control that lives OUTSIDE that trust domain.
#
# RUN THIS ON MICHAEL'S MACHINE — the sandbox has no gh, no token, no credential helper.
# Auth is yours: `gh auth login` prompts natively. This script never handles a secret.
#
#   scripts/protect_governance_refs.sh          # verify only, changes nothing
#   scripts/protect_governance_refs.sh --go     # apply protection
#
# Requires: gh CLI, authenticated, with admin on the repo.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

REPO="hochster71/hoch_agent_swarm"
CANDIDATE="helm/promotion-candidate"
GO=0; [ "${1:-}" = "--go" ] && GO=1

say(){ printf '  %-42s %s\n' "$1" "$2"; }

echo "GOVERNANCE REF PROTECTION — $REPO"
echo

# --- preflight -----------------------------------------------------------------
command -v gh >/dev/null 2>&1 || { echo "FAIL: gh CLI not installed. brew install gh" >&2; exit 2; }
gh auth status >/dev/null 2>&1 || { echo "FAIL: gh not authenticated. Run: gh auth login" >&2; exit 3; }
say "gh CLI" "$(gh --version | head -1)"
say "authenticated" "yes"

perm=$(gh api "repos/$REPO" --jq '.permissions.admin' 2>/dev/null)
[ "$perm" = "true" ] || { echo "FAIL: branch protection requires admin on $REPO (got admin=$perm)" >&2; exit 4; }
say "admin permission" "yes"

# --- does the candidate ref exist on the remote? --------------------------------
remote_has=$(git ls-remote --heads origin "$CANDIDATE" 2>/dev/null | wc -l | tr -d ' ')
[ "$remote_has" = "0" ] && remote_has=$(git ls-remote --heads github "$CANDIDATE" 2>/dev/null | wc -l | tr -d ' ')
local_sha=$(git rev-parse --verify "refs/heads/$CANDIDATE" 2>/dev/null || echo "")
say "candidate ref (local)"  "${local_sha:-<absent>}"
say "candidate ref (remote)" "$([ "$remote_has" != "0" ] && echo present || echo ABSENT)"

echo
echo "=== current protection state ==="
for br in "$CANDIDATE" helm-runtime-bridge-v1; do
  st=$(gh api "repos/$REPO/branches/${br}/protection" 2>/dev/null | head -c 60)
  say "$br" "$([ -n "$st" ] && echo PROTECTED || echo UNPROTECTED)"
done

if [ $GO -eq 0 ]; then
  echo
  echo "VERIFY ONLY — nothing changed."
  echo "This would apply to $CANDIDATE:"
  echo "    direct pushes        prohibited (PR required, 1 approval)"
  echo "    force pushes         prohibited"
  echo "    branch deletion      prohibited"
  echo "    admin bypass         disabled (enforce_admins=true)"
  echo "    stale reviews        dismissed on new commits"
  echo
  echo "helm-runtime-bridge-v1 is left UNPROTECTED so development can keep moving."
  echo
  echo "Re-run with --go to apply."
  exit 0
fi

# --- push the candidate ref if the remote lacks it ------------------------------
if [ "$remote_has" = "0" ]; then
  [ -z "$local_sha" ] && { echo "FAIL: no local $CANDIDATE to publish" >&2; exit 5; }
  echo
  echo "publishing $CANDIDATE -> remote at $local_sha"
  git push github "refs/heads/$CANDIDATE:refs/heads/$CANDIDATE" || { echo "FAIL: push refused" >&2; exit 6; }
fi

# --- apply protection ----------------------------------------------------------
echo
echo "applying protection to $CANDIDATE …"
gh api -X PUT "repos/$REPO/branches/${CANDIDATE}/protection" \
  -H "Accept: application/vnd.github+json" \
  -f  'required_status_checks=null' \
  -F  'enforce_admins=true' \
  -f  'required_pull_request_reviews[required_approving_review_count]=1' \
  -F  'required_pull_request_reviews[dismiss_stale_reviews]=true' \
  -f  'restrictions=null' \
  -F  'allow_force_pushes=false' \
  -F  'allow_deletions=false' \
  >/dev/null 2>&1 && echo "  PROTECTION APPLIED" || { echo "  FAIL: see: gh api repos/$REPO/branches/$CANDIDATE/protection" >&2; exit 7; }

echo
echo "=== verification ==="
gh api "repos/$REPO/branches/${CANDIDATE}/protection" \
  --jq '{enforce_admins:.enforce_admins.enabled,
         force_pushes:.allow_force_pushes.enabled,
         deletions:.allow_deletions.enabled,
         reviews:.required_pull_request_reviews.required_approving_review_count}' 2>/dev/null

echo
echo "Governance refs now have a writer boundary OUTSIDE the local trust domain."
echo "Repo-local controls remain detect-only; this one prevents."
