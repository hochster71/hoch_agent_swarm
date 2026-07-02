#!/usr/bin/env bash
set -euo pipefail

cd /Users/michaelhoch/hoch_agent_swarm

mkdir -p docs/evidence/goal_runner
OUT="docs/evidence/goal_runner/goal_readiness_summary_$(date -u +%Y%m%dT%H%M%SZ).md"

{
  echo "# GOAL Readiness Summary"
  echo
  echo "- Timestamp UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- Active Orchestrator: Michaels AI Model"
  echo "- Michael Hoch: Final Approval Authority"
  echo "- Mode: AUTO_GOAL_LOOP_SAFE_LOCAL"
  echo

  echo "## Runner Status"
  cat has_live_project_tracker/data/goal_runner_status.json | python3 -m json.tool
  echo

  echo "## Critical Telemetry"
  curl -sS http://127.0.0.1:8765/api/pert/data > /tmp/has_goal_summary_api.json
  python3 - /tmp/has_goal_summary_api.json <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
src = data.get("freshness_authority", {}).get("reconciled_sources", {})
metrics = data.get("metrics", {})

print("- percent_goal_complete:", metrics.get("percent_goal_complete"))
for k in ["global_verify", "hoch_pods_runtime_state", "hoch_pod_schedule"]:
    s = src.get(k, {})
    print(f"- {k}: {s.get('computed_state')} age={s.get('freshness_age_seconds')} reason={s.get('reason')}")
PY
  echo

  echo "## UI V2.1 Browser Gate"
  PERT_BASE_URL=http://127.0.0.1:8765 node scripts/verify_ui_v21_browser.mjs
  echo

  echo "## Guardrails"
  bash scripts/secure_build_guardrail_check.sh
  echo

  echo "## Blocker Triage"
  bash scripts/has_goal_blocker_triage.sh
} | tee "$OUT"

echo
echo "WROTE: $OUT"
