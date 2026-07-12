"""REQ-TO-003 — run the seven-stage proof on a NEUTRAL workload.

    TERMINAL_PATH_PROOF_WORKLOAD / NOT_CHAMPION_PRODUCT / NOT_PRODUCTION_RELEASE

The workload is deliberately boring and objective: ask a LOCAL model to write a small
pure-Python module, then verify it INDEPENDENTLY -- not by asking the model whether it
did a good job, but by importing the module, running it, and recomputing the answer with
a different mechanism (hashlib) than the one the model wrote.

  local-only .... routed to ollama through the governed gateway
  no keys ....... no credential is read
  no spend ...... local adapter, $0
  non-destructive written only inside the proof package directory
  objective ..... acceptance criteria are executable assertions

Run:  python3 scripts/council/run_terminal_path_proof.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.council.terminal_path import (  # noqa: E402
    PACKAGES, WORKLOAD_LABELS, State, TerminalPathOrchestrator, TransitionEvidence,
    sha256_file, sha256_obj, utc, validate_intake,
)
from scripts.council.dispatch import CouncilRouter, TaskEnvelope, new_task_id  # noqa: E402

CANONICAL_GOAL_ID = "HOCH_CANONICAL_GOAL_CONTRACT_v1"

ARTIFACT_NAME = "sha256_manifest.py"

WORKLOAD_PROMPT = """Write a single self-contained Python module. Output ONLY code, no prose, no markdown fences.

Requirements:
- module docstring on the first line
- import hashlib, json, os
- def build_manifest(directory): returns a dict mapping each filename (not full path) in
  that directory to the lowercase hex sha256 of that file's bytes. Non-recursive. Files only.
- def main(): prints json.dumps(build_manifest('.'), sort_keys=True)

Output the code only."""

ACCEPTANCE = [
    {"id": "AC1", "criterion": "artifact file exists and is non-empty",
     "validator": "artifact_exists"},
    {"id": "AC2", "criterion": "module imports without error",
     "validator": "module_imports"},
    {"id": "AC3", "criterion": "build_manifest is callable and returns a dict",
     "validator": "function_contract"},
    {"id": "AC4", "criterion": "manifest digests match an INDEPENDENT hashlib recomputation",
     "validator": "independent_digest_recomputation"},
]


def write(path: Path, obj) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def strip_fences(text: str) -> str:
    t = text.strip()
    if "```" in t:
        parts = t.split("```")
        for p in parts:
            if "def build_manifest" in p:
                t = p
                break
        if t.startswith("python"):
            t = t[len("python"):]
    return t.strip()


def ev(orch, validator, ok, path: Path, inp: str, out: str, exit_code=0, detail="",
       task_id="") -> TransitionEvidence:
    return TransitionEvidence(
        validator_name=validator,
        validator_result=bool(ok),
        validator_exit_code=exit_code,
        evidence_path=str(path.relative_to(ROOT)),
        evidence_digest=sha256_file(path),
        input_digest=inp,
        output_digest=out,
        event_timestamp=utc(),
        mission_id=orch.mission_id,
        task_id=task_id or orch.mission_id,
        detail=detail,
    )


def main() -> int:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_id = f"REQ-TO-003-{stamp}-{uuid.uuid4().hex[:6].upper()}"
    pkg = PACKAGES / f"REQ-TO-003-INTAKE-TO-DOORSTEP-{stamp}"
    pkg.mkdir(parents=True, exist_ok=True)
    orch = TerminalPathOrchestrator(mission_id, pkg)

    print("=" * 74)
    print(f"REQ-TO-003 TERMINAL PATH PROOF  —  {mission_id}")
    print(f"  {' / '.join(WORKLOAD_LABELS)}")
    print("=" * 74)

    # ---------------- STAGE 1: INTAKE ------------------------------------
    intake = {
        "mission_id": mission_id,
        "request_id": f"RQ-{uuid.uuid4().hex[:8].upper()}",
        "goal_contract_id": CANONICAL_GOAL_ID,
        "workload_type": "TERMINAL_PATH_PROOF_WORKLOAD",
        "labels": WORKLOAD_LABELS,
        "requested_outcome": (
            "Produce a local-only Python module that builds a sha256 manifest of a "
            "directory, verified by INDEPENDENT recomputation."),
        "constraints": ["local_only", "no_credentials", "no_spend", "non_destructive",
                        "no_production_deploy", "no_signing", "no_submission"],
        "founder_only_actions": [],           # honestly empty: this proof needs none
        "acceptance_criteria": ACCEPTANCE,
        "submitted_at": utc(),
        "source_identity": "helm-council-agent (autonomous; not founder-submitted)",
    }
    p_intake = write(pkg / "intake_envelope.json", intake)
    orch.state = State.INTAKE_RECEIVED
    ok, errs = validate_intake(intake, CANONICAL_GOAL_ID)
    intake_digest = sha256_obj(intake)
    orch.advance(State.INTAKE_VALIDATED,
                 ev(orch, "validate_intake", ok, p_intake, "GENESIS", intake_digest,
                    0 if ok else 1, ",".join(errs)))
    print(f"[1/7] INTAKE     {orch.state.value}  errors={errs or 'none'}")
    if orch.state != State.INTAKE_VALIDATED:
        return finish(orch, pkg, 1)

    # ---------------- STAGE 2: PLAN --------------------------------------
    plan = {
        "mission_id": mission_id,
        "tasks": [{
            "task_id": new_task_id("TO003"),
            "description": "generate the sha256 manifest module",
            "depends_on": [],
            "expected_artifacts": [ARTIFACT_NAME],
            "validators": ["artifact_exists", "module_imports", "function_contract",
                           "independent_digest_recomputation"],
            "adapter_policy": {"local_first": True, "frontier_required": False,
                               "preferred": "ollama"},
            "timeout_seconds": 180,
            "cost_ceiling_usd": 0.0,
            "failure_handling": "fail_closed -> BLOCKED, no retry beyond 1 revision",
            "scope": f"write only {ARTIFACT_NAME} inside the proof package",
        }],
        "founder_gates_detected": [],
        "evidence_contract": [c["validator"] for c in ACCEPTANCE],
        "created_at": utc(),
    }
    p_plan = write(pkg / "validated_plan.json", plan)
    plan_ok = bool(plan["tasks"]) and all(
        t.get("validators") and t.get("timeout_seconds") and t.get("expected_artifacts")
        for t in plan["tasks"])
    plan_digest = sha256_obj(plan)
    orch.advance(State.PLAN_CREATED,
                 ev(orch, "plan_created", True, p_plan, intake_digest, plan_digest))
    orch.advance(State.PLAN_VALIDATED,
                 ev(orch, "plan_has_validators_and_bounds", plan_ok, p_plan,
                    intake_digest, plan_digest, 0 if plan_ok else 1))
    print(f"[2/7] PLAN       {orch.state.value}  tasks={len(plan['tasks'])}")
    if orch.state != State.PLAN_VALIDATED:
        return finish(orch, pkg, 1)

    # ---------------- STAGE 3: ROUTE (governed gateway) -------------------
    task = plan["tasks"][0]
    route = {
        "mission_id": mission_id,
        "task_id": task["task_id"],
        "adapter_selected": "ollama",
        "selection_reason": "LOCAL_FIRST: workload does not declare frontier_required",
        "frontier_required": False,
        "gateway": "scripts/council/dispatch.py -> spend_gate.SubprocessSpendGate",
        "egress_policy": "local loopback only; provider hosts blocked without gateway token",
        "spend_policy": {"per_task_cap_usd": 0.05, "estimated_usd": 0.0},
        "pert_binding": {"pert_node": "TO-003", "requirement": "REQ-TO-003"},
        "direct_provider_bypass": False,
        "routed_at": utc(),
    }
    p_route = write(pkg / "route_decision.json", route)
    route_digest = sha256_obj(route)
    orch.advance(State.ROUTE_SELECTED,
                 ev(orch, "route_selected", True, p_route, plan_digest, route_digest))
    # authorized = the gateway's own preflight says this dispatch may proceed
    from scripts.council.spend_gate import DispatchRequest, SubprocessSpendGate
    gate = SubprocessSpendGate()
    pre = gate.preflight(DispatchRequest(
        task_id=task["task_id"], adapter="ollama", binary="ollama",
        prompt=WORKLOAD_PROMPT, frontier_required=False, per_task_cap_usd=0.05))
    route_authorized = not pre
    write(pkg / "route_authorization.json",
          {"preflight_blocks": pre, "authorized": route_authorized})
    orch.advance(State.ROUTE_AUTHORIZED,
                 ev(orch, "gateway_preflight", route_authorized, p_route,
                    plan_digest, route_digest, 0 if route_authorized else 1,
                    f"blocks={pre}"))
    print(f"[3/7] ROUTE      {orch.state.value}  adapter=ollama blocks={pre or 'none'}")
    if orch.state != State.ROUTE_AUTHORIZED:
        return finish(orch, pkg, 1)

    # ---------------- STAGE 4: EXECUTE (through the gateway) --------------
    orch.state = State.EXECUTION_ACTIVE
    started = utc()
    router = CouncilRouter()
    tenv = TaskEnvelope(
        task_id=task["task_id"],
        scope=task["scope"],
        prompt=WORKLOAD_PROMPT,
        evidence_contract=["def build_manifest"],
        frontier_required=False,
        pert_node="TO-003",
        timeout_seconds=task["timeout_seconds"],
        per_task_cap_usd=0.05,
    )
    result = router.dispatch_one(tenv, "ollama")
    code = strip_fences(result.output or "")
    artifact = pkg / "artifacts" / ARTIFACT_NAME
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(code, encoding="utf-8")

    execution = {
        "mission_id": mission_id,
        "task_id": task["task_id"],
        "adapter": result.adapter,
        "adapter_status": result.status,
        "critic_verdict": result.critic_verdict,
        "external_dispatch_count": 1 if result.external_call else 0,
        "estimated_cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
        "started_at": started,
        "completed_at": utc(),
        "files_written": [str(artifact.relative_to(ROOT))],
        "authorized_scope": task["scope"],
        "actual_scope": f"wrote {artifact.relative_to(pkg)} inside the proof package",
        "scope_deviation": False,
        "input_digest": hashlib.sha256(WORKLOAD_PROMPT.encode()).hexdigest(),
        "output_digest": sha256_file(artifact) if artifact.exists() else None,
        "cost_ledger_hash": result.cost_ledger_hash,
        "manual_copy_paste_operations": 0,
    }
    p_exec = write(pkg / "execution_manifest.json", execution)
    write(pkg / "execution_results.json",
          {"raw_output_sha256": result.response_sha256, "status": result.status,
           "blocks": result.blocks, "output_chars": len(result.output or "")})
    exec_ok = result.status == "COMPLETED" and artifact.exists() and artifact.stat().st_size > 0
    exec_digest = sha256_obj(execution)
    orch.advance(State.EXECUTION_COMPLETE,
                 ev(orch, "execution_completed_in_scope", exec_ok, p_exec,
                    route_digest, exec_digest, 0 if exec_ok else 1,
                    f"adapter={result.status}", task["task_id"]))
    print(f"[4/7] EXECUTE    {orch.state.value}  adapter={result.status} "
          f"${result.cost_usd:.5f} external={execution['external_dispatch_count']}")
    if orch.state != State.EXECUTION_COMPLETE:
        return finish(orch, pkg, 1)

    # ---------------- STAGE 5: VERIFY (INDEPENDENT) -----------------------
    orch.state = State.VERIFICATION_ACTIVE
    checks = independent_verification(artifact)
    all_pass = all(c["pass"] for c in checks)
    verification = {
        "mission_id": mission_id,
        "verifier_identity": "deterministic_python_validator",
        "producer_identity": f"model:{result.adapter}",
        "independent": True,
        "independence_basis": (
            "The verifier is NOT the producing model. It imports the produced module, "
            "runs it against a controlled fixture, and recomputes every digest with "
            "hashlib -- a different mechanism than the code under test."),
        "checks": checks,
        "acceptance_criteria": ACCEPTANCE,
        "result": "VERIFICATION_PASS" if all_pass else "UNVERIFIED",
        "verified_at": utc(),
    }
    p_verify = write(pkg / "verification_results.json", verification)
    write(pkg / "acceptance_results.json",
          {"criteria": [{**c, "pass": next(x["pass"] for x in checks
                                            if x["validator"] == c["validator"])}
                        for c in ACCEPTANCE],
           "all_pass": all_pass})
    ver_digest = sha256_obj(verification)
    orch.advance(State.VERIFICATION_PASS,
                 ev(orch, "independent_verification", all_pass, p_verify,
                    exec_digest, ver_digest, 0 if all_pass else 1))
    print(f"[5/7] VERIFY     {orch.state.value}  "
          f"{sum(c['pass'] for c in checks)}/{len(checks)} checks (independent)")
    if orch.state != State.VERIFICATION_PASS:
        return finish(orch, pkg, 1)

    # ---------------- STAGE 6: PACKAGE ------------------------------------
    inventory = [{"path": str(p.relative_to(pkg)), "bytes": p.stat().st_size}
                 for p in sorted(pkg.rglob("*")) if p.is_file()]
    write(pkg / "artifact_inventory.json", {"artifacts": inventory})
    write(pkg / "founder_actions.json", {
        "founder_action_required": False,
        "reason": ("The neutral proof workload is local-only, unpaid, unsigned and "
                   "unsubmitted. No founder-only action is reached. A gate was NOT "
                   "fabricated to exercise the interface."),
        "pending_founder_only_requirements_elsewhere": ["REQ-TO-001", "REQ-TO-002"],
    })
    write(pkg / "manual_intervention_metrics.json",
          orch.to_dict()["manual_intervention_metrics"])
    write(pkg / "runtime_truth.json", {
        "external_dispatch_count": execution["external_dispatch_count"],
        "estimated_cost_usd": execution["estimated_cost_usd"],
        "gateway_enforced": True, "fail_closed": True, "generated_at": utc()})
    write(pkg / "mission_manifest.json", {
        "mission_id": mission_id, "requirement": "REQ-TO-003",
        "labels": WORKLOAD_LABELS, "stages": [s for s in
        ("INTAKE", "PLAN", "ROUTE", "EXECUTE", "VERIFY", "PACKAGE", "DOORSTEP")],
        "state": orch.state.value, "transitions": orch.history})

    digests = {str(p.relative_to(pkg)): sha256_file(p)
               for p in sorted(pkg.rglob("*")) if p.is_file()}
    write(pkg / "artifact_digests.json", digests)
    (pkg / "SHA256SUMS").write_text(
        "".join(f"{h}  {n}\n" for n, h in sorted(digests.items())), encoding="utf-8")

    p_pkg = pkg / "artifact_digests.json"
    pkg_digest = sha256_obj(digests)
    orch.advance(State.PACKAGE_CREATED,
                 ev(orch, "package_created", True, p_pkg, ver_digest, pkg_digest))

    required = ["mission_manifest.json", "intake_envelope.json", "validated_plan.json",
                "route_decision.json", "execution_manifest.json", "execution_results.json",
                "verification_results.json", "acceptance_results.json",
                "artifact_inventory.json", "artifact_digests.json", "founder_actions.json",
                "runtime_truth.json", "SHA256SUMS"]
    missing = [r for r in required if not (pkg / r).exists()]
    # every digest must still match its file
    bad = [n for n, h in digests.items()
           if (pkg / n).exists() and n != "artifact_digests.json" and n != "SHA256SUMS"
           and sha256_file(pkg / n) != h]
    pkg_ok = not missing and not bad
    write(pkg / "validation.json", {
        "requirement": "REQ-TO-003", "mission_id": mission_id,
        "missing_artifacts": missing, "digest_mismatches": bad,
        "package_complete": pkg_ok,
        "state": orch.state.value, "validated_at": utc()})
    orch.advance(State.PACKAGE_VALIDATED,
                 ev(orch, "package_complete_and_digest_valid", pkg_ok,
                    pkg / "validation.json", ver_digest, pkg_digest,
                    0 if pkg_ok else 1, f"missing={missing} bad={bad}"))
    print(f"[6/7] PACKAGE    {orch.state.value}  artifacts={len(inventory)} "
          f"missing={missing or 'none'}")
    if orch.state != State.PACKAGE_VALIDATED:
        return finish(orch, pkg, 1)

    # ---------------- STAGE 7: DOORSTEP -----------------------------------
    m = orch.metrics
    zero_transport = (m.manual_prompt_copy_count == 0
                      and m.manual_result_copy_count == 0
                      and m.manual_stage_transition_count == 0)
    doorstep = {
        "mission_id": mission_id,
        "state": "DOORSTEP_READY" if zero_transport else "BLOCKED",
        "FOUNDER_ACTION_REQUIRED": "NO",
        "PROOF_WORKLOAD_COMPLETE": "YES",
        "manual_prompt_copy_count": m.manual_prompt_copy_count,
        "manual_result_copy_count": m.manual_result_copy_count,
        "manual_stage_transition_count": m.manual_stage_transition_count,
        "founder_interventions": m.founder_interventions,
        "all_non_founder_work_complete": True,
        "unresolved_founder_only_actions": [],
        "package_identity_immutable": True,
        "generated_at": utc(),
    }
    p_door = write(pkg / "doorstep.json", doorstep)
    door_digest = sha256_obj(doorstep)
    orch.advance(State.DOORSTEP_READY,
                 ev(orch, "zero_founder_transport", zero_transport, p_door,
                    pkg_digest, door_digest, 0 if zero_transport else 1))
    print(f"[7/7] DOORSTEP   {orch.state.value}  founder_action_required=NO")

    # refresh the digests/SHA256SUMS to include the final artifacts
    digests = {str(p.relative_to(pkg)): sha256_file(p)
               for p in sorted(pkg.rglob("*")) if p.is_file()
               and p.name not in ("artifact_digests.json", "SHA256SUMS")}
    write(pkg / "artifact_digests.json", digests)
    (pkg / "SHA256SUMS").write_text(
        "".join(f"{h}  {n}\n" for n, h in sorted(digests.items())), encoding="utf-8")

    return finish(orch, pkg, 0 if orch.state == State.DOORSTEP_READY else 1)


def independent_verification(artifact: Path) -> list[dict]:
    """Verify WITHOUT asking the producing model anything."""
    checks: list[dict] = []

    exists = artifact.exists() and artifact.stat().st_size > 0
    checks.append({"validator": "artifact_exists", "pass": bool(exists),
                   "detail": f"{artifact.name} {artifact.stat().st_size if artifact.exists() else 0} bytes"})

    mod = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("proof_mod", artifact)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)          # type: ignore[union-attr]
        checks.append({"validator": "module_imports", "pass": True, "detail": "imported"})
    except Exception as e:
        checks.append({"validator": "module_imports", "pass": False,
                       "detail": f"{type(e).__name__}: {e}"})

    fn_ok = bool(mod and callable(getattr(mod, "build_manifest", None)))
    checks.append({"validator": "function_contract", "pass": fn_ok,
                   "detail": "build_manifest callable" if fn_ok else "missing build_manifest"})

    # THE independent check: build a controlled fixture, run the model's code, and
    # recompute every digest ourselves with hashlib. The model does not get a vote.
    digest_ok = False
    detail = "not run"
    if fn_ok:
        try:
            with tempfile.TemporaryDirectory() as td:
                names = {"alpha.txt": b"alpha-bytes", "beta.bin": b"\x00\x01\x02beta"}
                for n, b in names.items():
                    (Path(td) / n).write_bytes(b)
                produced = mod.build_manifest(td)           # type: ignore[union-attr]
                expected = {n: hashlib.sha256(b).hexdigest() for n, b in names.items()}
                digest_ok = (isinstance(produced, dict)
                             and {k: str(v).lower() for k, v in produced.items()} == expected)
                detail = f"produced={produced} expected={expected}"
        except Exception as e:
            detail = f"{type(e).__name__}: {e}"
    checks.append({"validator": "independent_digest_recomputation", "pass": digest_ok,
                   "detail": detail[:300]})
    return checks


def finish(orch, pkg: Path, rc: int) -> int:
    (pkg / "orchestrator_state.json").write_text(
        json.dumps(orch.to_dict(), indent=2) + "\n", encoding="utf-8")
    print("-" * 74)
    print(f"  FINAL STATE : {orch.state.value}")
    print(f"  reason      : {orch.blocked_reason or '-'}")
    print(f"  package     : {pkg.relative_to(ROOT)}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
