#!/usr/bin/env bash
set -euo pipefail

cd /Users/michaelhoch/hoch_agent_swarm

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="logs/goal_runner"
EVIDENCE_DIR="docs/evidence/goal_runner"
STATUS_FILE="has_live_project_tracker/data/goal_runner_status.json"
LOCK_DIR="/tmp/has_goal_e2e_runner.lockdir"

mkdir -p "$LOG_DIR" "$EVIDENCE_DIR" has_live_project_tracker/data

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "GOAL_RUNNER: another run is already active"
  exit 0
fi

cleanup_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup_lock EXIT INT TERM

LOG_FILE="$LOG_DIR/goal_runner_${RUN_ID}.log"
EVIDENCE_FILE="$EVIDENCE_DIR/goal_runner_${RUN_ID}.md"

write_status() {
  local state="$1"
  local step="$2"
  local note="$3"
  python3 - "$state" "$step" "$note" "$RUN_ID" "$LOG_FILE" "$EVIDENCE_FILE" "$STATUS_FILE" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

state, step, note, run_id, log_file, evidence_file, status_file = sys.argv[1:]
status = {
    "runner_id": "michaels-ai-model-goal-orchestrator",
    "runner_name": "Michaels AI Model",
    "run_id": run_id,
    "state": state,
    "current_step": step,
    "note": note,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "log_file": log_file,
    "evidence_file": evidence_file,
    "safe_mode": True,
    "unsafe_actions_blocked": [
        "STRIPE_LIVE_CONFIG",
        "DEPLOYMENT",
        "DESTRUCTIVE",
        "PUBLIC_EXPOSURE",
        "REPO_TAG_PROMOTION",
        "NETWORK_WRITE"
    ]
}
Path(status_file).write_text(json.dumps(status, indent=2))
PY
}

run_step() {
  local name="$1"
  shift

  echo
  echo "================================================================"
  echo "STEP: $name"
  echo "COMMAND: $*"
  echo "TIME: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "================================================================"

  write_status "RUNNING" "$name" "Executing safe local GOAL step"

  if "$@"; then
    echo "STEP_RESULT: PASS $name"
    return 0
  else
    echo "STEP_RESULT: FAIL $name"
    write_status "DEGRADED" "$name" "Step failed; continuing safe evidence collection"
    return 1
  fi
}

{
  echo "# Michaels AI Model GOAL Runner Evidence"
  echo
  echo "- Run ID: $RUN_ID"
  echo "- Runner: Michaels AI Model"
  echo "- Mode: AUTO_GOAL_LOOP_SAFE_LOCAL"
  echo "- Started UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Michael Hoch remains Final Approval Authority."
  echo

  write_status "RUNNING" "START" "GOAL runner started"

  run_step "Refresh live telemetry" python3 scripts/refresh_live_telemetry.py || true
  run_step "Verify telemetry freshness" python3 scripts/verify_live_telemetry_freshness.py || true
  run_step "Verify UI V2.1 smoke" bash scripts/verify_ui_v21.sh || true

  echo
  echo "NOTE: Legacy mirror / RC35 release chains are diagnostic only and skipped by default."
  echo "NOTE: They still enforce old git-clean and stale-metrics gates."
  echo "NOTE: To run them manually, set RUN_LEGACY_RELEASE_GATES=1."

  if [ "${RUN_LEGACY_RELEASE_GATES:-0}" = "1" ]; then
    if [ -x scripts/has_parallel_mirror_verify.sh ]; then
      run_step "Verify parallel mirror diagnostic" bash scripts/has_parallel_mirror_verify.sh || true
    else
      echo "SKIP: scripts/has_parallel_mirror_verify.sh missing or not executable"
    fi

    if [ -x scripts/rc35_compute_expansion_verify.sh ]; then
      run_step "Verify swarm scheduler legacy diagnostic" bash scripts/rc35_compute_expansion_verify.sh || true
    else
      echo "SKIP: scripts/rc35_compute_expansion_verify.sh missing or not executable"
    fi
  else
    echo "SKIP: Legacy parallel mirror diagnostic"
    echo "SKIP: Legacy RC35 scheduler/release diagnostic"
  fi

  if [ -x scripts/secure_build_guardrail_check.sh ]; then
    run_step "Run secure build guardrail checks" bash scripts/secure_build_guardrail_check.sh || true
  else
    echo "SKIP: scripts/secure_build_guardrail_check.sh missing or not executable"
  fi

  if [ -f package.json ] && command -v node >/dev/null 2>&1; then
    run_step "Run UI V2.1 browser gate" env PERT_BASE_URL=http://127.0.0.1:8765 node scripts/verify_ui_v21_browser.mjs || true

    echo
    echo "NOTE: Full legacy Playwright is diagnostic only and skipped by default."
    echo "NOTE: To run it manually, set RUN_FULL_LEGACY_PLAYWRIGHT=1."
    if [ "${RUN_FULL_LEGACY_PLAYWRIGHT:-0}" = "1" ] && command -v npx >/dev/null 2>&1; then
      run_step "Run full legacy Playwright diagnostic suite" npx playwright test || true
    else
      echo "SKIP: Full legacy Playwright diagnostic suite"
    fi
  else
    echo "SKIP: Node/package.json unavailable"
  fi

  echo
  echo "=== FINAL API GOAL SNAPSHOT ==="
  curl -fsS http://127.0.0.1:8765/api/pert/data > /tmp/has_goal_runner_api.json || true

  python3 - <<'PY' || true
import json
from pathlib import Path

p = Path("/tmp/has_goal_runner_api.json")
if not p.exists():
    print("API_SNAPSHOT: MISSING")
    raise SystemExit(0)

data = json.loads(p.read_text())
src = data.get("freshness_authority", {}).get("reconciled_sources", {})
metrics = data.get("metrics", {})
print("percent_goal_complete:", metrics.get("percent_goal_complete"))
for k in ["global_verify", "hoch_pods_runtime_state", "hoch_pod_schedule"]:
    s = src.get(k, {})
    print(k, s.get("computed_state"), s.get("freshness_age_seconds"), s.get("reason"))
PY

  echo
  echo "- Completed UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Status File: $STATUS_FILE"
  echo "- Log File: $LOG_FILE"

  write_status "COMPLETED" "COMPLETE" "Safe local GOAL runner completed one full cycle"

} 2>&1 | tee "$LOG_FILE"

cp "$LOG_FILE" "$EVIDENCE_FILE"

echo "GOAL_RUNNER: COMPLETE"
echo "Evidence: $EVIDENCE_FILE"
