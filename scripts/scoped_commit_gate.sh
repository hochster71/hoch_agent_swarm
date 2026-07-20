#!/usr/bin/env bash
# scoped_commit_gate.sh — make a claim's commit boundary an executable gate.
#
# WHY THIS EXISTS
# ---------------
# 2026-07-20, W1-002a: `git add <two files>` was run, and the resulting commit
# contained THREE. A third file (mission_envelope.py) had been staged earlier and rode
# along silently. `git add <paths>` ADDS to the index; it does not CONSTRAIN the commit.
# The only signal was the file count in git's output, which is operator observation, not
# a gate. This converts the boundary into an assertion that fails closed.
#
# USAGE
#   scripts/scoped_commit_gate.sh <path> [<path>...]        # verify staged == exactly these
#   scripts/scoped_commit_gate.sh --strict <path> [...]     # also require clean whitespace
#
# Exit 0 = staged set matches the allowlist exactly. Exit non-zero = refuse to commit.
#
# Typical claim flow:
#   git add <paths>
#   scripts/scoped_commit_gate.sh <paths> && git commit -F msg.txt
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

STRICT=0
if [[ "${1:-}" == "--strict" ]]; then STRICT=1; shift; fi

if [[ $# -eq 0 ]]; then
  echo "FAIL: no allowlist supplied. A scoped commit with no declared boundary is not scoped." >&2
  exit 2
fi

expected="$(printf '%s\n' "$@" | sort -u)"
actual="$(git diff --cached --name-only | sort -u)"

if [[ -z "$actual" ]]; then
  echo "FAIL: nothing staged." >&2
  exit 3
fi

if [[ "$expected" != "$actual" ]]; then
  echo "COMMIT BOUNDARY VIOLATION — staged set does not match the declared claim." >&2
  echo >&2
  echo "  expected (${#@} path(s)):" >&2
  printf '    %s\n' $expected >&2
  echo "  actually staged ($(printf '%s\n' "$actual" | wc -l | tr -d ' ') path(s)):" >&2
  printf '    %s\n' $actual >&2
  echo >&2
  unexpected="$(comm -13 <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") || true)"
  missing="$(comm -23 <(printf '%s\n' "$expected") <(printf '%s\n' "$actual") || true)"
  [[ -n "$unexpected" ]] && { echo "  UNEXPECTED (likely stale index — unstage these):" >&2
                              printf '    git restore --staged %s\n' $unexpected >&2; }
  [[ -n "$missing" ]] && { echo "  MISSING (declared but not staged):" >&2
                           printf '    %s\n' $missing >&2; }
  exit 1
fi

if ! git diff --cached --check; then
  echo "FAIL: whitespace/conflict-marker errors in staged content." >&2
  exit 4
fi

if [[ $STRICT -eq 1 ]]; then
  # Record the exact bytes being committed so an audit can later prove that the
  # reviewed files and the committed files are identical.
  echo "staged content hashes (record these in the claim evidence):"
  while IFS= read -r f; do
    [[ -f "$f" ]] && printf '  %s  %s\n' "$(git show ":$f" | sha256sum | cut -d' ' -f1)" "$f"
  done <<< "$actual"
fi

echo "COMMIT BOUNDARY OK — $(printf '%s\n' "$actual" | wc -l | tr -d ' ') file(s), exactly as declared."
