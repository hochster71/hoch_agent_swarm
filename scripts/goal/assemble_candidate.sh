#!/bin/zsh
# Candidate assembly with ENFORCED tree-hash invariant (v1, council directive 2026-07-20).
#
# Implements exactly: assemble -> compute write-tree -> compare against the expected hash from
# CANDIDATE_IDENTITY_RECORD.json -> ABORT on mismatch -> only then may curated units and
# qualification proceed. The hash is an enforced invariant, not documentation.
#
# Modes:
#   (default)    DRY RUN - assemble in a throwaway worktree, verify hash, tear down. Repeatable
#                proof that the recipe still reproduces the recorded identity.
#   --execute    FOUNDER FREEZE STEP ONLY - assemble into the persistent candidate worktree
#                (../helm_candidate_assembly) and STOP with the verified state STAGED but
#                UNCOMMITTED. Committing the candidate is a founder act this script never does.
set -e
set -o pipefail
cd "$(dirname "$0")/../.."
RECORD=coordination/goal/CANDIDATE_IDENTITY_RECORD.json

BASE=$(python3 -c "import json;print(json.load(open('$RECORD'))['base_commit'])")
PICK=$(python3 -c "import json;print(json.load(open('$RECORD'))['cherry_picked_commits'][0]['sha'])")
EXPECTED=$(python3 -c "import json;print(json.load(open('$RECORD'))['initial_tree_hash'])")
EXCL=$(python3 -c "import json;print(' '.join(json.load(open('$RECORD'))['cherry_picked_commits'][0]['excluded_files_within_pick']))")
echo "recipe: base=$BASE pick=${PICK[1,12]}... expected_tree=$EXPECTED"

if [ "$1" = "--execute" ]; then
  WT="$(pwd)/../helm_candidate_assembly"
  [ -e "$WT" ] && { echo "FAIL-CLOSED: $WT exists - remove explicitly first" >&2; exit 2; }
  PERSIST=1
else
  WT=$(mktemp -d /tmp/candidate_assembly_XXXXXX); rmdir "$WT"
  PERSIST=0
fi

git worktree add --detach "$WT" "$BASE" >/dev/null
cd "$WT"
git cherry-pick --no-commit "$PICK" >/dev/null
git restore --staged --worktree ${=EXCL}
GOT=$(git write-tree)
echo "assembled tree: $GOT"

if [ "$GOT" != "$EXPECTED" ]; then
  echo "ABORT: TREE HASH MISMATCH - got $GOT, expected $EXPECTED. Candidate identity NOT" >&2
  echo "reproduced; nothing may proceed. Worktree removed; investigate the recipe drift." >&2
  cd - >/dev/null; git worktree remove --force "$WT"
  exit 4
fi
echo "TREE HASH INVARIANT SATISFIED: $GOT == expected"

if [ "$PERSIST" = "1" ]; then
  echo "EXECUTE mode: verified assembly left STAGED and UNCOMMITTED in $WT"
  echo "NEXT (founder acts, in order): commit initial candidate -> apply curated units per T10"
  echo "manifests -> freeze SHA -> finalize CANDIDATE_IDENTITY_RECORD (frozen sha + record sha256)"
  echo "-> run_promotion_binding_qualification.sh <frozen sha>"
else
  cd - >/dev/null; git worktree remove --force "$WT"
  echo "DRY RUN complete: recipe reproduces the recorded identity; worktree removed"
fi
