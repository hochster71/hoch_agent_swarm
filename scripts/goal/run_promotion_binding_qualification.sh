#!/bin/zsh
# PROMOTION-BINDING qualification in an ISOLATED git worktree (v1 - PREPARED, NOT YET RUNNABLE
# BY POLICY: executes only after founder-gated candidate freeze; usage requires the frozen SHA).
#
# Council architecture (2026-07-20): T10 reviewed -> curated candidate committed -> SHA frozen
# -> THIS script: isolated worktree from that exact SHA -> ratified baseline copied+hash-verified
# -> no daemon writers on the isolated path -> exclusive qualification -> artifacts bound to
# frozen SHA and tree hash. The isolated worktree gets its own TMPDIR, sqlite paths (via
# TMPDIR derivation), evidence output, lock, and logs. Daemons write only to the main repo
# path, so exclusivity here holds by construction.
#
# Usage: ./scripts/goal/run_promotion_binding_qualification.sh <FROZEN_SHA>
set -e
set -o pipefail
MAIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FROZEN_SHA="$1"
[ -z "$FROZEN_SHA" ] && { echo "usage: $0 <FROZEN_SHA> (full 40-char frozen candidate sha)" >&2; exit 2; }
[ ${#FROZEN_SHA} -eq 40 ] || { echo "FAIL-CLOSED: frozen SHA must be the full 40-char sha" >&2; exit 2; }
cd "$MAIN_ROOT"
git cat-file -e "${FROZEN_SHA}^{commit}" || { echo "FAIL-CLOSED: unknown sha" >&2; exit 2; }

SHA8=${FROZEN_SHA[1,8]}
WT="$MAIN_ROOT/../helm_candidate_${SHA8}"
LABEL="promotion_binding_${SHA8}"

echo "== 1. isolated worktree at the exact frozen SHA =="
[ -e "$WT" ] && { echo "FAIL-CLOSED: $WT already exists - refuse to reuse; remove explicitly first" >&2; exit 2; }
git worktree add --detach "$WT" "$FROZEN_SHA"
cd "$WT"
[ "$(git rev-parse HEAD)" = "$FROZEN_SHA" ] || { echo "FAIL-CLOSED: worktree HEAD mismatch" >&2; exit 2; }
[ -z "$(git status --porcelain)" ] || { echo "FAIL-CLOSED: fresh worktree not clean" >&2; exit 2; }
TREE_SHA=$(git rev-parse "HEAD^{tree}")

echo "== 2. no daemon writers may reference this path =="
if pgrep -f "$WT" >/dev/null 2>&1; then echo "FAIL-CLOSED: processes already reference $WT" >&2; exit 2; fi
grep -rl "$WT" ~/Library/LaunchAgents/ 2>/dev/null && { echo "FAIL-CLOSED: a LaunchAgent references $WT" >&2; exit 2; }

echo "== 3. ratified baseline copied + hash-verified against the pinned sha =="
BASE_SRC="$MAIN_ROOT/coordination/evidence/sbom_cve_20260719/runtime/expected_full_suite_residue.json"
PIN=$(python3 -c "import json;print(json.load(open('$MAIN_ROOT/coordination/evidence/sbom_cve_20260719/runtime/burndown_record.json'))['expected_residue_baseline_sha256_pin'])")
GOT=$(shasum -a 256 "$BASE_SRC" | awk '{print $1}')
[ "$GOT" = "$PIN" ] || { echo "FAIL-CLOSED: baseline hash $GOT != pinned $PIN - re-pin required before binding run" >&2; exit 2; }
mkdir -p coordination/evidence/sbom_cve_20260719/runtime
cp "$BASE_SRC" coordination/evidence/sbom_cve_20260719/runtime/
[ "$(shasum -a 256 coordination/evidence/sbom_cve_20260719/runtime/expected_full_suite_residue.json | awk '{print $1}')" = "$PIN" ] || exit 2

echo "== 4. isolated venv sync (frozen lock, worktree-local .venv) =="
uv sync --frozen

echo "== 5. exclusive qualification via the controlled launcher (worktree copy) =="
./scripts/goal/run_qualification_suite.sh "$LABEL"
RC=$?

echo "== 6. bind + repatriate artifacts to the main evidence chain =="
ART="coordination/evidence/sbom_cve_20260719/runtime/${LABEL}_artifact.json"
python3 - "$ART" "$FROZEN_SHA" "$TREE_SHA" <<'PYEOF'
import json, os, sys, tempfile
art, sha, tree = sys.argv[1:4]
a = json.load(open(art))
a["promotion_binding"] = {"frozen_candidate_sha": sha, "candidate_tree_sha": tree,
                          "isolated_worktree": os.getcwd(),
                          "binding_note": "executed in a detached worktree at the exact frozen SHA; clean by construction"}
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(art))
with os.fdopen(fd, "w") as f: json.dump(a, f, indent=2); f.flush(); os.fsync(f.fileno())
os.replace(tmp, art)
PYEOF
DEST="$MAIN_ROOT/coordination/evidence/sbom_cve_20260719/runtime/"
cp "$ART" "${ART%.json}_acceptance.json" "$DEST" 2>/dev/null || cp "$ART" "$DEST"
cp "/tmp/${LABEL}_suite.log" "$MAIN_ROOT/coordination/evidence/sbom_cve_20260719/runtime/originals/" 2>/dev/null || true
echo "artifacts repatriated to main evidence chain. Worktree preserved for inspection: $WT"
echo "(remove later with: git worktree remove --force $WT)"
exit $RC
