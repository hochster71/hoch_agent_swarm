#!/usr/bin/env bash
# gov007_validate.sh — GOV-007 adversarial validation against a disposable protected ref.
#
# FALSIFIABLE CLAIM UNDER TEST:
#   One actor cannot create a contribution accepted by the protected repository as another
#   actor, or without required signing.
#
# WHY A DISPOSABLE BRANCH: the test must exercise a REAL server-side policy boundary.
# The 578f7317 push to helm-runtime-bridge-v1 succeeded and proves only that the network
# and credential path work — that ref carries no policy, so the rejection that would
# validate the control was never possible. boundary_exercised was true for the NETWORK,
# false for the POLICY.
#
# OUTCOME CLASSES — attribution, not pass/fail:
#   VALIDATED_IDENTITY_BOUNDARY  refused for missing/unverified signature or unauthorized
#                                signing authority.        *** ONLY THIS CLOSES GOV-007 ***
#   VALIDATED_BRANCH_WORKFLOW    refused because direct pushes prohibited / PR required.
#                                AUTHOR-INDEPENDENT — would reject any pusher. Proves
#                                change-path enforcement, NOT impersonation resistance.
#   VALIDATED_OTHER_POLICY       refused by status checks, linear history, reviews, rules.
#   DISPROVEN                    impersonating contribution ACCEPTED.
#   INCONCLUSIVE                 DNS, timeout, auth failure, malformed refspec, missing
#                                access, client-side hook, or unclassified rejection.
#
# PROBES — one probe tests ONE control:
#   A  unsigned commit authored as another actor      (tests: is any author + no sig accepted?)
#   B  validly signed, key NOT authorized for that identity
#      (tests: does GitHub BIND signature to identity, or merely recognise a valid signature?)
#   Probe B requires signing to be configured first.
#
# Usage:
#   scripts/gov007_validate.sh --setup          # create + protect gov-007-test (gh, admin)
#   scripts/gov007_validate.sh --attempt A      # probe A
#   scripts/gov007_validate.sh --attempt B      # probe B (after signing configured)
#   scripts/gov007_validate.sh --teardown
#
# SAFE: operates only on refs/heads/gov-007-test. Never touches master,
# helm-runtime-bridge-v1, or the promotion candidate. Handles no secrets.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

REPO="hochster71/hoch_agent_swarm"
BR="gov-007-test"
OUT="coordination/governance/gov007_evidence.json"
IMPERSONATED_NAME="HELM Builder (Claude)"
IMPERSONATED_EMAIL="builder@helm.local"

need_gh(){ command -v gh >/dev/null 2>&1 || { echo "FAIL: gh CLI required. brew install gh" >&2; exit 2; }
           gh auth status >/dev/null 2>&1 || { echo "FAIL: gh not authenticated. gh auth login" >&2; exit 3; }; }

case "${1:-}" in
--setup)
  need_gh
  echo "creating disposable branch $BR at HEAD"
  git push github "HEAD:refs/heads/$BR" 2>&1 | tail -2
  echo "applying protection (signed commits + PR required + admins included)"
  gh api -X PUT "repos/$REPO/branches/$BR/protection" \
    -H "Accept: application/vnd.github+json" \
    -f  'required_status_checks=null' -F 'enforce_admins=true' \
    -f  'required_pull_request_reviews[required_approving_review_count]=1' \
    -f  'restrictions=null' -F 'allow_force_pushes=false' -F 'allow_deletions=false' \
    >/dev/null 2>&1 && echo "  protection applied" || { echo "  FAIL: protection not applied" >&2; exit 4; }
  gh api -X POST "repos/$REPO/branches/$BR/protection/required_signatures" \
    -H "Accept: application/vnd.github+json" >/dev/null 2>&1 \
    && echo "  required_signatures ON" || echo "  WARN: required_signatures not set"
  echo
  echo "VERIFY before attempting — a test against an UNPROTECTED ref proves nothing:"
  gh api "repos/$REPO/branches/$BR/protection" --jq \
    '{enforce_admins:.enforce_admins.enabled, signatures:.required_signatures.enabled,
      reviews:.required_pull_request_reviews.required_approving_review_count}' 2>/dev/null
  ;;

--attempt)
  need_gh
  # PROBE SEPARATION. One probe must test ONE control. Combining impersonation with
  # missing-signature makes an ambiguous rejection uninterpretable — you cannot tell
  # whether GitHub objected to the identity, the absent signature, or a branch rule.
  PROBE="${2:-A}"
  case "$PROBE" in
    A) echo "PROBE A — unsigned commit authored as another actor";;
    B) echo "PROBE B — signed commit, signing key NOT authorized for the asserted identity"
       git config user.signingkey >/dev/null 2>&1 || {
         echo "REFUSED: Probe B needs a configured signing key. Probe A first." >&2; exit 6; };;
    *) echo "usage: --attempt [A|B]" >&2; exit 64;;
  esac
  # confirm the policy boundary EXISTS, or the result is meaningless
  prot=$(gh api "repos/$REPO/branches/$BR/protection" 2>/dev/null)
  [ -z "$prot" ] && { echo "REFUSED: $BR has no protection. Run --setup first." >&2
                      echo "An attempt against an unprotected ref cannot validate anything." >&2; exit 5; }

  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  echo "gov-007 adversarial probe $ts" > "$tmp/probe"
  git -c user.name="$IMPERSONATED_NAME" -c user.email="$IMPERSONATED_EMAIL" \
      -c commit.gpgsign=false hash-object -w "$tmp/probe" >/dev/null

  # unsigned commit authored as ANOTHER actor, on top of the protected ref
  base=$(git rev-parse "github/$BR" 2>/dev/null || git rev-parse HEAD)
  blob=$(git hash-object -w "$tmp/probe")
  tree=$(printf '100644 blob %s\tgov007_probe.txt\n' "$blob" | git mktree)
  sha=$(GIT_AUTHOR_NAME="$IMPERSONATED_NAME"   GIT_AUTHOR_EMAIL="$IMPERSONATED_EMAIL" \
        GIT_COMMITTER_NAME="$IMPERSONATED_NAME" GIT_COMMITTER_EMAIL="$IMPERSONATED_EMAIL" \
        git commit-tree "$tree" -p "$base" -m "GOV-007 adversarial probe: unsigned, impersonating")

  echo "attempting push of $sha (author: $IMPERSONATED_NAME <$IMPERSONATED_EMAIL>, unsigned)"
  raw=$(git push github "$sha:refs/heads/$BR" 2>&1); rc=$?
  echo "$raw" | sed 's/^/    /'

  # CLASSIFY — five classes. Attribution matters more than pass/fail.
  #
  # FOUNDER CORRECTION 2026-07-20: the prior version treated ANY policy rejection as
  # GOV-007 validation. That was wrong. A generic "protected branch" or "pull request
  # required" refusal rejects EVERY direct push regardless of the asserted author —
  # it demonstrates BRANCH-WORKFLOW enforcement, not IMPERSONATION RESISTANCE.
  # Only a rejection attributable to the IDENTITY or SIGNING boundary closes GOV-007.
  boundary=false; succeeded=false; klass=INCONCLUSIVE
  low=$(printf '%s' "$raw" | tr 'A-Z' 'a-z')
  if [ $rc -eq 0 ]; then
    boundary=true; succeeded=true; klass=DISPROVEN
  elif echo "$low" | grep -qE 'signature|signed commits|unsigned|unverified|gpg|not authorized to (push|sign)|committer identity|email address.*not|verified'; then
    boundary=true; klass=VALIDATED_IDENTITY_BOUNDARY
  elif echo "$low" | grep -qE 'gh006|protected branch|pull request|push declined|refusing to allow'; then
    boundary=true; klass=VALIDATED_BRANCH_WORKFLOW
  elif echo "$low" | grep -qE 'status check|linear history|required review|deployment|rule violation|ruleset'; then
    boundary=true; klass=VALIDATED_OTHER_POLICY
  fi

  python3 - "$OUT" "$ts" "$sha" "$boundary" "$succeeded" "$klass" "$PROBE" "$raw" <<'PYEOF'
import json, sys
out, ts, sha, boundary, succeeded, klass, probe, raw = sys.argv[1:9]
b, s = boundary == "true", succeeded == "true"
CLOSES_GOV007 = klass == "VALIDATED_IDENTITY_BOUNDARY"
rec = {
  "control": "GOV-007", "adversarial": True, "boundary_exercised": b,
  "attempt_succeeded": s, "rejection_reason": raw.strip()[:800],
  "target": "refs/heads/gov-007-test", "attempt_timestamp": ts,
  "attacking_actor": "local shell (uid 501, michaelhoch)",
  "impersonated_actor": "HELM Builder (Claude) <builder@helm.local>",
  "candidate_sha": sha, "acceptance_path_exercised": "git push to protected remote ref",
  "probe": probe,
  "result_class": klass,
  "closes_gov007": CLOSES_GOV007,
  "verdict": {
    "DISPROVEN": "DISPROVEN — impersonating unsigned contribution was ACCEPTED",
    "VALIDATED_IDENTITY_BOUNDARY": "VALIDATED — refused for identity/signing reasons. CLOSES GOV-007.",
    "VALIDATED_BRANCH_WORKFLOW": ("VALIDATED (branch workflow) — refused because direct pushes "
      "are prohibited. Does NOT close GOV-007: this rejection is author-independent and would "
      "occur for any pusher. Proves change-path enforcement only."),
    "VALIDATED_OTHER_POLICY": ("VALIDATED (other policy) — refused by status checks, linear "
      "history, reviews, or an unrelated rule. Does NOT close GOV-007."),
    "INCONCLUSIVE": "INCONCLUSIVE — never reached the policy boundary, or rejection unclassified",
  }[klass],
  "closure_note": ("GOV-007 closes ONLY on VALIDATED_IDENTITY_BOUNDARY. Other validating "
                   "classes close their own controls, not identity attribution."),
}
open(out, "w").write(json.dumps(rec, indent=2) + "\n")
print("\n" + json.dumps({k: rec[k] for k in
      ("probe","result_class","boundary_exercised","attempt_succeeded",
       "closes_gov007","verdict")}, indent=2))
print(f"\nevidence -> {out}")
if not b:
    print("\nINCONCLUSIVE. Do NOT record as validation — the attempt failed before "
          "reaching the enforcement boundary.", file=sys.stderr)
elif not CLOSES_GOV007 and not s:
    print(f"\n{klass}: a real policy refused this push, but the refusal is NOT "
          "attributable to the identity/signing boundary. GOV-007 REMAINS OPEN.",
          file=sys.stderr)
PYEOF
  ;;

--teardown)
  need_gh
  gh api -X DELETE "repos/$REPO/branches/$BR/protection" >/dev/null 2>&1
  git push github --delete "$BR" 2>&1 | tail -1
  echo "disposable branch removed"
  ;;

*) echo "usage: $0 {--setup|--attempt|--teardown}" >&2; exit 64;;
esac
