#!/usr/bin/env bash
# promotion_candidate_cas.sh — compare-and-swap update of the serialized candidate ref.
#
# FOUNDER DECISION 2026-07-20 (GOV-005 recurrent). Do NOT try to freeze the whole repository;
# multi-actor development needs to keep moving. Isolate ONE serialized ref instead:
#
#   refs/heads/helm-runtime-bridge-v1   development    multi-actor writes allowed
#   refs/heads/helm/promotion-candidate serialized     CAS-only, fails closed on drift
#
# The development branch may advance freely without invalidating a review of the candidate.
#
# HONEST SCOPE: this is LOCAL compare-and-swap. It makes an unauthorized candidate update
# FAIL rather than silently clobber. It does NOT stop a direct push to the remote candidate
# ref — that requires GitHub branch protection, which is a founder console action. Until
# that is configured, this is serialization by convention plus a hard local check.
#
# Usage:
#   promotion_candidate_cas.sh init   --new <sha>
#   promotion_candidate_cas.sh update --expected <sha> --new <sha> --session <id> --package-hash <h>
#   promotion_candidate_cas.sh show
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
REF=refs/heads/helm/promotion-candidate
LOG=coordination/governance/candidate_ref_log.jsonl

cur(){ git rev-parse --verify "$REF" 2>/dev/null || echo ""; }

case "${1:-}" in
  show)
    c=$(cur); echo "candidate ref : $REF"; echo "current       : ${c:-<unset>}"
    [ -n "$c" ] && git log -1 --format='  %h %s' "$c"
    echo "development   : $(git rev-parse --verify refs/heads/helm-runtime-bridge-v1 2>/dev/null | cut -c1-12)"
    ;;
  init)
    shift; new=""; while [ $# -gt 0 ]; do [ "$1" = "--new" ] && new="$2" && shift 2 || shift; done
    [ -n "$(cur)" ] && { echo "REFUSED: candidate ref already exists at $(cur). Use update." >&2; exit 4; }
    git cat-file -e "${new}^{commit}" 2>/dev/null || { echo "REFUSED: $new is not a commit" >&2; exit 5; }
    git update-ref "$REF" "$new"
    echo "candidate initialized -> $(cur)"
    ;;
  update)
    shift; exp=""; new=""; sess=""; pkg=""
    while [ $# -gt 0 ]; do case "$1" in
      --expected) exp="$2"; shift 2;; --new) new="$2"; shift 2;;
      --session) sess="$2"; shift 2;; --package-hash) pkg="$2"; shift 2;; *) shift;; esac; done
    c=$(cur)
    if [ "$c" != "$exp" ]; then
      echo "CAS FAILED — candidate ref moved" >&2
      echo "  expected $exp" >&2; echo "  actual   ${c:-<unset>}" >&2
      echo "  Another actor advanced the candidate. Re-review before retrying." >&2
      exit 1
    fi
    git cat-file -e "${new}^{commit}" 2>/dev/null || { echo "REFUSED: $new is not a commit" >&2; exit 5; }
    # atomic: only swaps if the ref still equals exp at write time
    if ! git update-ref "$REF" "$new" "$exp"; then
      echo "CAS FAILED at write — ref changed between check and swap (race)." >&2; exit 2
    fi
    printf '{"ts":"%s","ref":"%s","old":"%s","new":"%s","session":"%s","package_hash":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REF" "$exp" "$new" "$sess" "$pkg" >> "$LOG"
    echo "CAS OK: $exp -> $new"
    ;;
  *) echo "usage: $0 {show|init --new <sha>|update --expected <sha> --new <sha> --session <id> --package-hash <h>}" >&2; exit 64;;
esac
