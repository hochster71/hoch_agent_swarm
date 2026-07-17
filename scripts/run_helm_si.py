#!/usr/bin/env python3
"""HELM System Integration test runner — runs the HELM platform SI scope and
writes an honest result snapshot to coordination/goal/si_status.json.

Scope = the HELM platform suites (runtime bridge, dispatch, mission, truth,
governance, conmon, hmai, external milestones, jspace, freshness). Orphaned
legacy modules (missing hoch_agent_swarm.* packages / crewai) are excluded and
recorded as OUT_OF_SCOPE — not counted as HELM failures (no fake green either way).

Usage: python3 scripts/run_helm_si.py   (run repeatedly; the live UI reads the JSON)
"""
from __future__ import annotations
import json, re, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "coordination" / "goal" / "si_status.json"

SI_SCOPE = [
    "tests/helm_runtime/",
    "tests/test_authority_binding_chain.py", "tests/test_brain_truth_endpoints.py",
    "tests/test_conmon.py", "tests/test_executive_mission.py", "tests/test_external_milestones.py",
    "tests/test_factory_runtime_truth.py", "tests/test_goal_truth_engine.py",
    "tests/test_h1d_dispatch.py", "tests/test_h1d_dispatch_gateway.py",
    "tests/test_helm_agents_accountability.py", "tests/test_helm_live_api_security.py",
    "tests/test_helm_runtime_transactions.py", "tests/test_helm_truth_fa1_fa2_fa6.py",
    "tests/test_hmai.py", "tests/test_jspace_governance.py", "tests/test_jspace_hjos.py",
    "tests/test_jspace_latch_clearing.py", "tests/test_jspace_lens.py", "tests/test_jspace_negative.py",
    "tests/test_lease_release_truth.py", "tests/test_live_runtime_truth_validator.py",
    "tests/test_local_runtime_supervisor.py", "tests/test_no_fake_green_truth_endpoints.py",
    "tests/test_runtime_animation_state.py", "tests/test_runtime_freshness.py",
    "tests/test_runtime_governor.py", "tests/test_runtime_process_bus.py",
    "tests/test_runtime_refresher.py", "tests/test_runtime_truth_defaults.py",
    "tests/test_soak_select_freshness.py",
]
OUT_OF_SCOPE = [
    {"module": "tests/test_brain_runtime.py", "reason": "orphaned: hoch_agent_swarm.brain_runtime missing"},
    {"module": "tests/test_promptbrain.py", "reason": "orphaned: hoch_agent_swarm.promptbrain_manager missing"},
    {"module": "tests/test_crew_smoke.py", "reason": "env: crewai not installed"},
    {"module": "tests/test_model_router.py", "reason": "env: crewai not installed"},
    {"module": "tests/test_swarm_pipeline.py", "reason": "orphaned: hoch_agent_swarm.crew missing"},
    {"module": "tests/test_entry_points.py", "reason": "orphaned: hoch_agent_swarm.main missing"},
]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run() -> dict:
    t0 = time.time()
    cmd = ["python3", "-m", "pytest", *SI_SCOPE, "-q", "-p", "no:cacheprovider", "-o", "addopts="]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = p.stdout + p.stderr
    def grab(pat):
        m = re.search(rf"(\d+)\s+{pat}", out)
        return int(m.group(1)) if m else 0
    passed, failed, errors = grab("passed"), grab("failed"), grab("error"),
    total = passed + failed + errors
    result = {
        "schema": "HELM_SI_STATUS_v1",
        "ran_at": _now(),
        "duration_s": round(time.time() - t0, 1),
        "scope_modules": len(SI_SCOPE),
        "passed": passed, "failed": failed, "errors": errors, "total": total,
        "green": failed == 0 and errors == 0 and passed > 0,
        "exit_code": p.returncode,
        "out_of_scope": OUT_OF_SCOPE,
        "summary_line": next((l for l in reversed(out.splitlines()) if "passed" in l or "failed" in l or "error" in l), ""),
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    r = run()
    print(f"HELM SI: {r['passed']} passed, {r['failed']} failed, {r['errors']} errors "
          f"({r['duration_s']}s) → green={r['green']} → {OUT}")
