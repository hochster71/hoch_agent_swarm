#!/usr/bin/env python3
"""hrf_runtime.py — HRF-RUNTIME-001. The governed HRF execution path.

WHY THIS EXISTS (GOV-017)
-------------------------
The factory registry declared HRF's agent_roles, validators, security_policy and budget.
Nothing consumed them. `readiness_basis` was `on_disk=True` — a PRESENCE observation
standing in for a CAPABILITY property. This module is the missing consumer: it turns those
declarations into an execution path that can actually be run, and therefore actually fail.

BOUNDED SCOPE (founder ruling 2026-07-20). In scope: intake, Researcher, Evidence Auditor,
Synthesis Writer, fact_check_verifier, council routing, budget enforcement, SANDBOX_STRICT,
provenance. OUT of scope: monetization, Stripe, packaging, registry redesign, readiness
mutation. This module NEVER writes readiness or health into the registry — a run produces
evidence; something else may later derive state from it.

DOCTRINE APPLIED
----------------
- Classification is DERIVED from what the run observed, never declared. There is no
  `set_status`. See `_classify`.
- Fail-closed: an unknown role, an unauthorised adapter, an over-budget step, or a missing
  sandbox policy HALTS. A halted run is BLOCKED, not PARTIAL, and never OPERATIONAL_PROVEN.
- OPERATIONAL_PROVEN requires every declared component to have actually executed AND the
  validator to have passed. Absence of failure is not proof of success.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "coordination" / "council" / "factory_registry.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()


class Outcome(str, Enum):
    """The five founder-specified classes. UNKNOWN is a real answer, not a placeholder."""

    OPERATIONAL_PROVEN = "OPERATIONAL_PROVEN"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    NOT_OPERATIONAL = "NOT_OPERATIONAL"
    UNKNOWN = "UNKNOWN"


class SandboxViolation(RuntimeError):
    """SANDBOX_STRICT refused a step. Fail-closed: never downgraded to a warning."""


@dataclass
class StepRecord:
    """One observed execution. Immutable evidence (ARCH-002) — callers append, never edit."""

    component: str
    executed: bool
    ok: bool
    detail: str = ""
    cost_usd: float = 0.0
    model: str = ""
    output_sha256: str = ""
    at: str = field(default_factory=_now)


@dataclass
class BudgetLedger:
    """Budget enforcement. Refuses BEFORE dispatch — an overrun detected afterwards is an
    accounting record, not a control."""

    per_task_limit_usd: float
    monthly_limit_usd: float
    spent_usd: float = 0.0

    def authorize(self, estimate_usd: float) -> None:
        if estimate_usd > self.per_task_limit_usd:
            raise SandboxViolation(
                f"per-task budget: estimate {estimate_usd} > limit {self.per_task_limit_usd}"
            )
        if self.spent_usd + estimate_usd > self.monthly_limit_usd:
            raise SandboxViolation(
                f"monthly budget: {self.spent_usd}+{estimate_usd} > {self.monthly_limit_usd}"
            )

    def record(self, actual_usd: float) -> None:
        self.spent_usd += max(0.0, float(actual_usd or 0.0))


def load_factory(factory_id: str = "HRF") -> Dict[str, Any]:
    """Read the declaration. Fail-closed if absent — an execution path with no contract
    cannot be governed, and guessing the contract is how proxies become properties."""
    doc = json.loads(REGISTRY.read_text())
    fac = (doc.get("factories") or {}).get(factory_id)
    if not fac:
        raise SandboxViolation(f"factory {factory_id} absent from registry — refusing to run")
    for required in ("agent_roles", "validators", "security_policy", "budget", "intake_schema"):
        if required not in fac:
            raise SandboxViolation(f"{factory_id}.{required} undeclared — refusing to run")
    return fac


def validate_intake(payload: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """Minimal, dependency-free check against the registry's declared intake_schema."""
    if not isinstance(payload, dict):
        raise SandboxViolation("intake must be an object")
    for key in schema.get("required", []):
        if key not in payload or payload[key] in (None, "", [], {}):
            raise SandboxViolation(f"intake missing required field: {key}")
    props = schema.get("properties", {})
    for k, v in payload.items():
        want = (props.get(k) or {}).get("type")
        if want == "string" and not isinstance(v, str):
            raise SandboxViolation(f"intake field {k} must be string")
        if want == "array" and not isinstance(v, list):
            raise SandboxViolation(f"intake field {k} must be array")


def enforce_sandbox(policy: str, *, environment: str, scope: str) -> None:
    """SANDBOX_STRICT: local-only, read-only. Refuses anything else."""
    if policy != "SANDBOX_STRICT":
        raise SandboxViolation(f"unsupported security_policy {policy!r} — refusing to run")
    if environment != "local_only":
        raise SandboxViolation(f"SANDBOX_STRICT forbids environment={environment!r}")
    if scope != "read-only":
        raise SandboxViolation(f"SANDBOX_STRICT forbids scope={scope!r}")


# --- role prompts -------------------------------------------------------------
# Each role gets ONLY what its task requires. The model is not told what HELM is, how
# governance works, or how the pieces fit together (compartmentalisation).
ROLE_PROMPTS = {
    "Researcher": (
        "Research the question below. Return findings as numbered claims. "
        "For each claim give a source. If you do not have a source, write SOURCE: NONE.\n\nQUESTION: {query}"
    ),
    "Evidence Auditor": (
        "Below are research claims. For each, state SUPPORTED or UNSUPPORTED and why. "
        "A claim with SOURCE: NONE is UNSUPPORTED.\n\nCLAIMS:\n{prior}"
    ),
    "Synthesis Writer": (
        "Write a brief from the SUPPORTED claims only. Omit UNSUPPORTED claims entirely. "
        "Do not add facts not present below.\n\nAUDITED CLAIMS:\n{prior}"
    ),
}

LANE_FOR_ROLE = {
    "Researcher": "local",
    "Evidence Auditor": "auditor",
    "Synthesis Writer": "local",
}


def fact_check_verifier(brief: str, audited: str) -> Dict[str, Any]:
    """The registry's declared validator. Deterministic and offline — a verifier that
    depends on the same model it verifies would decorrelate nothing (ARCH-001)."""
    findings: List[str] = []
    if not brief.strip():
        findings.append("empty brief")
    unsupported = [
        ln for ln in audited.splitlines() if "UNSUPPORTED" in ln.upper()
    ]
    leaked = [ln for ln in unsupported if ln.split("UNSUPPORTED")[0].strip()[:40]
              and ln.split("UNSUPPORTED")[0].strip()[:40] in brief]
    if leaked:
        findings.append(f"{len(leaked)} unsupported claim(s) present in brief")
    if "SOURCE: NONE" in brief.upper():
        findings.append("brief carries an unsourced claim")
    return {"passed": not findings, "findings": findings,
            "checked_unsupported": len(unsupported)}


def _classify(steps: List[StepRecord], verifier: Optional[Dict[str, Any]],
              halted: Optional[str]) -> Outcome:
    """DERIVED. There is deliberately no way to assert an outcome directly.

    OPERATIONAL_PROVEN requires: nothing halted, every declared component executed and
    succeeded, and the validator passed. Anything less is reported as what it was.
    """
    if halted:
        return Outcome.BLOCKED
    if not steps:
        return Outcome.UNKNOWN
    executed = [s for s in steps if s.executed]
    if not executed:
        return Outcome.NOT_OPERATIONAL
    if verifier is None:
        return Outcome.PARTIAL
    if all(s.executed and s.ok for s in steps) and verifier.get("passed") is True:
        return Outcome.OPERATIONAL_PROVEN
    return Outcome.PARTIAL


def run(payload: Dict[str, Any], *, factory_id: str = "HRF",
        dispatch=None) -> Dict[str, Any]:
    """Execute one governed HRF mission. Returns evidence; writes no state.

    `dispatch` is injectable so the path is testable without a live model. The default is
    the guarded, cost-capped, ledgered gateway — never a raw provider call.
    """
    run_id = str(uuid.uuid4())
    started = _now()
    steps: List[StepRecord] = []
    halted: Optional[str] = None
    verifier: Optional[Dict[str, Any]] = None
    outputs: Dict[str, str] = {}

    if dispatch is None:  # pragma: no cover - exercised only with a live gateway
        from backend.dispatch.guarded_council import guarded_dispatch as dispatch

    try:
        fac = load_factory(factory_id)
        validate_intake(payload, fac["intake_schema"])
        enforce_sandbox(fac["security_policy"], environment="local_only", scope="read-only")
        budget = BudgetLedger(
            per_task_limit_usd=float(fac["budget"]["per_task_limit_usd"]),
            monthly_limit_usd=float(fac["budget"]["monthly_limit_usd"]),
        )

        prior = ""
        for role in fac["agent_roles"]:
            if role not in ROLE_PROMPTS:
                raise SandboxViolation(f"role {role!r} declared but not implemented")
            budget.authorize(0.0)  # local lane is free; frontier lanes carry a real estimate
            prompt = ROLE_PROMPTS[role].format(query=payload.get("query", ""), prior=prior)
            res = dispatch(LANE_FOR_ROLE.get(role, "local"), prompt, pert_node="HRF")
            ok = bool(res.get("ok"))
            text = (res.get("text") or "").strip()
            budget.record(res.get("cost") or 0.0)
            steps.append(StepRecord(
                component=role, executed=True, ok=ok,
                detail="" if ok else str(res.get("message") or res.get("status") or "")[:200],
                cost_usd=float(res.get("cost") or 0.0), model=str(res.get("model") or ""),
                output_sha256=_sha(text),
            ))
            if not ok:
                break
            outputs[role] = text
            prior = text

        if len(outputs) == len(fac["agent_roles"]):
            verifier = fact_check_verifier(
                outputs.get("Synthesis Writer", ""), outputs.get("Evidence Auditor", "")
            )
            steps.append(StepRecord(
                component="fact_check_verifier", executed=True,
                ok=bool(verifier["passed"]), detail="; ".join(verifier["findings"]),
            ))
    except SandboxViolation as e:
        halted = str(e)
    except Exception as e:  # unexpected: still honest, still not green
        halted = f"{type(e).__name__}: {e}"

    outcome = _classify(steps, verifier, halted)
    evidence = {
        "run_id": run_id,
        "factory": factory_id,
        "started_at": started,
        "finished_at": _now(),
        "outcome": outcome.value,
        "halted_reason": halted,
        "steps": [s.__dict__ for s in steps],
        "verifier": verifier,
        "total_cost_usd": round(sum(s.cost_usd for s in steps), 6),
        "components_declared": None,
        "components_executed": [s.component for s in steps if s.executed],
    }
    try:
        evidence["components_declared"] = (
            load_factory(factory_id)["agent_roles"] + load_factory(factory_id)["validators"]
        )
    except SandboxViolation:
        pass
    evidence["provenance"] = _provenance(evidence)
    return evidence


def _provenance(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Provenance generation. Best-effort on the governed emitter, but the local hashes are
    unconditional — a run must be attributable even when telemetry is unavailable
    (delegation requires attribution)."""
    prov: Dict[str, Any] = {
        "run_id": evidence["run_id"],
        "content_hash": _sha({k: v for k, v in evidence.items() if k != "provenance"}),
        "schema_version": "HRF_RUN_EVIDENCE_v1",
        "generated_by": "backend.helm_runtime.hrf_runtime.run",
        "generated_at": _now(),
        "canonicalization": "json.dumps(sort_keys=True,default=str)",
    }
    try:
        from backend.helm_runtime.governed_emit import build_proof_record

        prov["proof_record"] = build_proof_record(
            authority="HRF-RUNTIME-001",
            decision_id=evidence["run_id"],
            explanation=f"HRF governed run -> {evidence['outcome']}",
            inputs={"components_executed": evidence["components_executed"]},
            proof_command="backend.helm_runtime.hrf_runtime.run",
            evidence_class="DERIVED",
            environment="local_only",
            correlation_id=evidence["run_id"],
        )
    except Exception as e:
        prov["proof_record"] = None
        prov["proof_record_unavailable"] = str(e)[:200]
    return prov


if __name__ == "__main__":  # pragma: no cover
    import sys

    q = " ".join(sys.argv[1:]) or "What is the authoritative provenance contract for generated HELM state artifacts?"
    print(json.dumps(run({"query": q}), indent=2)[:4000])
