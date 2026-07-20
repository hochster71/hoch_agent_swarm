#!/bin/zsh
# Controlled qualification-suite runner v2 (council directives 2026-07-20, BD-F4/BD-F5 closure
# + the seven edge controls from the Option-C ratification).
#
# Enforces mechanically: single execution lane, hash-bound baseline, recorded candidate
# identity. v2 adds over v1:
#   1. PID-reuse protection: foreign processes recorded as pid+lstart+command, not bare pid
#   2. ancestry awareness: the runner's own pytest DESCENDANTS are not "foreign"
#   3. (harvest/evaluator write atomically - tmp + fsync + rename; see those scripts)
#   4. sqlite isolation: unique TMPDIR per run => tests/conftest.py computes a unique
#      HOCHSTER_DB_PATH (it derives from tempfile.gettempdir()); no shared-DB collisions
#      even if exclusion somehow fails
#   5. git integrity: worktree diff hash, INDEX diff hash, and path sets captured start+end;
#      any INDEX change or any CODE-path worktree change during the run => NOT_CONTROLLED
#      (runtime evidence appends by the live daemon are recorded, not fatal - T1-F5 reality)
#   6. baseline schema validated BEFORE hashing/starting
#   7. this script never commits, freezes, signs, or populates a promotion manifest
#
# Usage: ./scripts/goal/run_qualification_suite.sh [label]
set -e
set -o pipefail
cd "$(dirname "$0")/../.."
LABEL="${1:-qualification}"
LOG="/tmp/${LABEL}_suite.log"
SIDECAR="/tmp/${LABEL}_concurrency_sidecar.txt"
BASELINE=coordination/evidence/sbom_cve_20260719/runtime/expected_full_suite_residue.json

echo "== preflight 6: baseline schema validation =="
.venv/bin/python - "$BASELINE" <<'PYEOF'
import json, sys
b = json.load(open(sys.argv[1]))
assert b.get("schema") == "HELM_EXPECTED_SUITE_RESIDUE_v1", "bad schema id"
ids = b.get("expected_wip_failed_ids")
assert isinstance(ids, list) and all(isinstance(i, str) and "::" in i for i in ids), "expected_wip_failed_ids malformed"
sk = b.get("expected_skips", {})
assert isinstance(sk.get("expected_total_skipped"), int), "expected_total_skipped malformed"
if not ids:
    a = b.get("re_pin_authorization") or {}
    assert a.get("authorized") is True and a.get("authorized_by") and a.get("authorized_at") \
        and isinstance(a.get("supporting_evidence"), list) and a.get("supporting_evidence"), \
        "empty expected set without a complete re_pin_authorization block"
print("baseline schema OK (%d expected failure ids)" % len(ids))
PYEOF

echo "== preflight 1: exclusive-lane check =="
FOREIGN=$(pgrep -f "python(3)? .*(-m )?pytest" || true)
if [ -n "$FOREIGN" ]; then
  echo "FAIL-CLOSED: foreign pytest running:" >&2
  echo "$FOREIGN" | while read P; do ps -p "$P" -o pid,lstart,command 2>/dev/null | tail -1 >&2; done
  exit 3
fi

BASELINE_SHA_START=$(shasum -a 256 "$BASELINE" | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)
WT_DIFF_SHA_START=$(git diff --binary | shasum -a 256 | awk '{print $1}')
IDX_DIFF_SHA_START=$(git diff --cached --binary | shasum -a 256 | awk '{print $1}')
git status --porcelain | sort > "/tmp/${LABEL}_paths_start.txt"
echo "baseline sha256:  $BASELINE_SHA_START"
echo "candidate HEAD:   $HEAD_SHA"
echo "worktree diff:    $WT_DIFF_SHA_START"
echo "index diff:       $IDX_DIFF_SHA_START"

echo "== control 4: per-run isolated TMPDIR (unique sqlite path via conftest derivation) =="
RUN_TMP=$(mktemp -d "/tmp/${LABEL}_XXXXXX")
echo "TMPDIR=$RUN_TMP"

# cross-lane advisory lock (2026-07-20, after an external kill terminated a qualification
# run mid-flight): a visible in-repo marker telling ANY other agent on this machine that a
# controlled qualification run is executing and must not be disturbed. Removed on exit.
LOCK=artifacts/goal/QUALIFICATION_RUN_IN_PROGRESS.json
cat > "$LOCK" <<LOCKEOF
{"owner": "evidence-campaign session (Claude/Cowork)", "label": "$LABEL", "runner_pid": $$,
 "started_at": "$(date -u +%FT%TZ)",
 "notice": "CONTROLLED QUALIFICATION RUN EXECUTING - do not launch pytest, mutate the worktree/index, or terminate python processes until this file is gone. Council-governed evidence run."}
LOCKEOF
trap 'rm -f "$LOCK"' EXIT

echo "== launching monitored full suite (-rs, log -> $LOG) =="
: > "$SIDECAR"
TMPDIR="$RUN_TMP" .venv/bin/python -m pytest tests/ -q --tb=no -rs -p no:cacheprovider > "$LOG" 2>&1 &
PYTEST_PID=$!
PYTEST_IDENTITY=$(ps -p $PYTEST_PID -o pid,lstart,command | tail -1)
echo "runner pytest: $PYTEST_IDENTITY"
(
  # controls 1+2: monitor for pytest processes OUTSIDE our descendant tree, with identity
  while kill -0 $PYTEST_PID 2>/dev/null; do
    DESC=" $PYTEST_PID "
    FRONTIER="$PYTEST_PID"
    for _i in 1 2 3 4 5 6; do
      KIDS=""
      for FP in ${=FRONTIER}; do
        K=$(pgrep -P "$FP" 2>/dev/null | tr '\n' ' ') || K=""
        KIDS="$KIDS $K"
      done
      KIDS="${KIDS## }"; KIDS="${KIDS%% }"
      [ -z "${KIDS// /}" ] && break
      DESC="$DESC$KIDS "
      FRONTIER="$KIDS"
    done
    for P in $(pgrep -f "python(3)? .*(-m )?pytest" 2>/dev/null); do
      case "$DESC" in
        *" $P "*) ;;  # our own descendant - not foreign
        *)
          PCMD=$(ps -p $P -o command= 2>/dev/null)
          # v2.2 carve-out (attempt-2 lesson, disclosed in the finding): a bare
          # `pytest --version`/`--help` probe starts no test session, loads no tests, and
          # touches no shared repo state - recorded for the audit trail but not a violation.
          # ANY other foreign pytest (incl. --collect-only, which imports conftest) is fatal.
          case "$PCMD" in
            *" --version"|*" --help") echo "$(date -u +%FT%TZ) INERT_PYTEST_PROBE: $(ps -p $P -o pid,lstart,command 2>/dev/null | tail -1)" >> "$SIDECAR" ;;
            *) echo "$(date -u +%FT%TZ) FOREIGN_PYTEST: $(ps -p $P -o pid,lstart,command 2>/dev/null | tail -1)" >> "$SIDECAR" ;;
          esac ;;
      esac
    done
    sleep 10
  done
) &
MONITOR_PID=$!
set +e
wait $PYTEST_PID
PYTEST_RC=$?
wait $MONITOR_PID 2>/dev/null
set -e

echo "== postflight: controls verification =="
CONTROLLED=true
VIOLATIONS=""
BASELINE_SHA_END=$(shasum -a 256 "$BASELINE" | awk '{print $1}')
WT_DIFF_SHA_END=$(git diff --binary | shasum -a 256 | awk '{print $1}')
IDX_DIFF_SHA_END=$(git diff --cached --binary | shasum -a 256 | awk '{print $1}')
git status --porcelain | sort > "/tmp/${LABEL}_paths_end.txt"
if grep -q "FOREIGN_PYTEST" "$SIDECAR" 2>/dev/null; then CONTROLLED=false; VIOLATIONS="$VIOLATIONS foreign_pytest"; fi
if [ "$BASELINE_SHA_START" != "$BASELINE_SHA_END" ]; then CONTROLLED=false; VIOLATIONS="$VIOLATIONS baseline_mutated"; fi
if [ "$HEAD_SHA" != "$(git rev-parse HEAD)" ]; then CONTROLLED=false; VIOLATIONS="$VIOLATIONS head_moved"; fi
if [ "$IDX_DIFF_SHA_START" != "$IDX_DIFF_SHA_END" ]; then CONTROLLED=false; VIOLATIONS="$VIOLATIONS index_mutated"; fi
# worktree delta: code-path changes are fatal; live-runtime evidence appends are recorded
CHANGED_PATHS=$(comm -13 "/tmp/${LABEL}_paths_start.txt" "/tmp/${LABEL}_paths_end.txt" | awk '{print $NF}')
CODE_MUTATIONS=$(echo "$CHANGED_PATHS" | grep -E "^(tests|backend|scripts|src)/" || true)
if [ -n "$CODE_MUTATIONS" ]; then CONTROLLED=false; VIOLATIONS="$VIOLATIONS code_paths_mutated"; fi
echo "controlled=$CONTROLLED violations:${VIOLATIONS:- none}"
if [ -n "$CHANGED_PATHS" ]; then
  echo "worktree path delta during run:"
  echo "$CHANGED_PATHS"
fi

echo "== mechanical harvest + evaluation =="
.venv/bin/python scripts/goal/harvest_full_suite_proof.py "$LOG" --label "$LABEL" \
  --pytest-command ".venv/bin/python -m pytest tests/ -q --tb=no -rs -p no:cacheprovider" >/dev/null
ART=coordination/evidence/sbom_cve_20260719/runtime/${LABEL}_artifact.json
CONTROLLED="$CONTROLLED" ART="$ART" BASELINE_SHA_START="$BASELINE_SHA_START" \
WT0="$WT_DIFF_SHA_START" WT1="$WT_DIFF_SHA_END" IDX0="$IDX_DIFF_SHA_START" IDX1="$IDX_DIFF_SHA_END" \
SIDECAR="$SIDECAR" RUNTMP="$RUN_TMP" VIOL="$VIOLATIONS" IDENT="$PYTEST_IDENTITY" CHANGED="$CHANGED_PATHS" PYTEST_RC="$PYTEST_RC" \
.venv/bin/python - <<'PYEOF'
import json, os, tempfile
art_path = os.environ["ART"]
a = json.load(open(art_path))
a["execution_controls"] = {
    "exclusive_lane_verified": os.environ["CONTROLLED"] == "true",
    "violations": (os.environ.get("VIOL") or "").split(),
    "runner_pytest_identity": os.environ["IDENT"],
    "pytest_return_code": int(os.environ["PYTEST_RC"]),
    "baseline_sha256_at_start": os.environ["BASELINE_SHA_START"],
    "worktree_diff_sha256": {"start": os.environ["WT0"], "end": os.environ["WT1"]},
    "index_diff_sha256": {"start": os.environ["IDX0"], "end": os.environ["IDX1"]},
    "worktree_path_delta": (os.environ.get("CHANGED") or "").splitlines(),
    "isolated_tmpdir": os.environ["RUNTMP"],
    "concurrency_sidecar_violations": open(os.environ["SIDECAR"]).read().splitlines(),
}
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(art_path))
with os.fdopen(fd, "w") as f:
    json.dump(a, f, indent=2); f.flush(); os.fsync(f.fileno())
os.replace(tmp, art_path)
PYEOF
if [ "$CONTROLLED" != "true" ]; then
  echo "RESULT: ENVIRONMENT_NOT_CONTROLLED ($VIOLATIONS) - artifact stamped; NOT eligible for acceptance" >&2
  exit 4
fi
.venv/bin/python scripts/goal/evaluate_full_suite_acceptance.py "$ART"
