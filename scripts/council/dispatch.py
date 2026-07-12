"""HELM H1D — autonomous council dispatch and model relay.

WHAT THIS REPLACES
------------------
    BEFORE:  ChatGPT -> Michael copies -> Grok -> Michael copies -> Claude -> AG IDE
    AFTER:   PERT task READY -> CouncilDispatchGateway -> adapters -> critic -> PERT

Michael is removed from prompt transport. He is retained for founder-only gates:
spend beyond policy, metered API keys, credentials, signing, submission, release.

H1D.7: EVERY model invocation routes through CouncilDispatchGateway
(scripts/council/gateway.py). SubprocessSpendGate is an internal transport of
the gateway only. Adapters build argv; they never spawn or open sockets.

FAIL-CLOSED: an adapter failure yields BLOCKED or UNKNOWN. It never yields a
fabricated result, and it never advances a PERT node.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from scripts.council.gateway import (
    CouncilDispatchGateway,
    DispatchType,
    GatewayRequest,
    ensure_guard,
)
from scripts.council.spend_gate import SubprocessSpendGate

ROOT = Path(__file__).resolve().parents[2]
RELAY_DIR = ROOT / "coordination" / "council" / "relay"
DISPATCH_LEDGER = RELAY_DIR / "dispatch_ledger.jsonl"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# ===========================================================================
# ENVELOPES  (H1D acceptance gates: "Task envelope", "Result envelope")
# ===========================================================================

@dataclass
class TaskEnvelope:
    """The unit of work the council dispatches. Immutable once hashed."""
    task_id: str
    scope: str                          # what the model may touch
    prompt: str
    evidence_contract: list[str]        # what the result MUST contain to be accepted
    timeout_seconds: int = 300
    frontier_required: bool = False
    pert_node: str | None = None
    per_task_cap_usd: float = 0.50
    milestone_ceiling_usd: float | None = None
    created_at: str = field(default_factory=_now)

    def digest(self) -> str:
        body = {k: v for k, v in asdict(self).items() if k != "created_at"}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


@dataclass
class ResultEnvelope:
    """What came back. `status` is never inferred -- it is measured."""
    task_id: str
    adapter: str
    status: str                         # COMPLETED | FAILED | BLOCKED | TIMEOUT | UNKNOWN
    output: str = ""
    files_changed: list[str] = field(default_factory=list)
    tests: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    blocks: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: int = 0
    external_call: bool = False
    response_sha256: str | None = None
    cost_ledger_hash: str | None = None
    critic_verdict: str | None = None   # ACCEPT | REVISE | REJECT
    critic_reasons: list[str] = field(default_factory=list)
    revision_of: str | None = None
    created_at: str = field(default_factory=_now)


# ===========================================================================
# ADAPTERS — each builds argv; NONE of them spawns anything itself
# ===========================================================================

class Adapter:
    name: str = "abstract"
    binary: str = ""
    external: bool = True

    def argv(self, task: TaskEnvelope) -> list[str]:
        raise NotImplementedError


class GrokAdapter(Adapter):
    """xAI Grok CLI (0.2.93). Headless, read-only tooling, no auto-approval."""
    name = "grok"
    binary = "grok"

    def argv(self, task: TaskEnvelope) -> list[str]:
        # -p = single-turn headless: prints the response to stdout and exits.
        # permission-mode plan = read-only; the model analyses, it does not act.
        # No --always-approve, ever.
        return [self.binary, "-p", task.prompt,
                "--permission-mode", "plan",
                "--output-format", "plain",
                "--no-subagents",
                "--cwd", str(ROOT)]


class GeminiAdapter(Adapter):
    """Google Gemini CLI (0.49.0). Headless via -p, read-only approval mode.

    Runs in a SCRATCH cwd: the Gemini CLI auto-ingests its working directory, and
    pointed at this repo it spends minutes scanning before answering. A council seat
    answers from the prompt it was given, not from an unbounded repo crawl. This also
    bounds what leaves the machine -- the seat sees the prompt, not the tree.
    """
    name = "gemini"
    binary = "gemini"
    scratch_cwd = "/tmp"

    def argv(self, task: TaskEnvelope) -> list[str]:
        # -p = non-interactive. approval-mode plan = read-only; the model analyses,
        # it does not act. Plain text: the critic reads substrings, not a JSON schema.
        # --skip-trust: headless in an untrusted scratch dir. Safe here precisely
        # BECAUSE approval-mode plan is read-only -- the seat cannot act on the folder.
        return [self.binary, "-p", task.prompt,
                "--approval-mode", "plan", "--skip-trust"]


class OllamaAdapter(Adapter):
    """Local model. Never leaves the machine. Always free."""
    name = "ollama"
    binary = "ollama"
    external = False

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model

    def argv(self, task: TaskEnvelope) -> list[str]:
        return [self.binary, "run", self.model, task.prompt]


ADAPTERS: dict[str, Adapter] = {
    "grok": GrokAdapter(),
    "gemini": GeminiAdapter(),
    "ollama": OllamaAdapter(),
}

ADAPTER_DISPATCH_TYPE: dict[str, DispatchType] = {
    "grok": DispatchType.CLI_GROK,
    "gemini": DispatchType.CLI_GEMINI,
    "ollama": DispatchType.LOCAL_OLLAMA,
}


# ===========================================================================
# CRITIC — validates a result against the task's evidence contract
# ===========================================================================

def critic_review(task: TaskEnvelope, result: ResultEnvelope) -> tuple[str, list[str]]:
    """ACCEPT | REVISE | REJECT. Absence of required evidence is never an ACCEPT.

    This is deliberately mechanical, not an LLM judgment call: a result is accepted
    only if it literally satisfies the evidence contract the task declared. A model
    cannot talk its way past this.
    """
    reasons: list[str] = []

    if result.status == "BLOCKED":
        return "REJECT", ["ADAPTER_BLOCKED:" + ",".join(result.blocks)]
    if result.status in ("TIMEOUT", "FAILED"):
        return "REVISE", [f"ADAPTER_{result.status}"]
    if not (result.output or "").strip():
        return "REVISE", ["EMPTY_OUTPUT"]

    lowered = result.output.lower()
    for required in task.evidence_contract:
        if required.lower() not in lowered:
            reasons.append(f"MISSING_REQUIRED_EVIDENCE:{required}")

    if reasons:
        return "REVISE", reasons
    return "ACCEPT", []


def revision_prompt(task: TaskEnvelope, result: ResultEnvelope,
                    reasons: list[str]) -> str:
    """The correction sent back automatically. No human retypes this."""
    return (
        f"{task.prompt}\n\n"
        f"--- AUTOMATED COUNCIL REVISION REQUEST ---\n"
        f"Your previous response was NOT accepted. Reasons:\n"
        + "\n".join(f"  - {r}" for r in reasons)
        + "\n\nYour response MUST explicitly contain each of these required items:\n"
        + "\n".join(f"  - {e}" for e in task.evidence_contract)
        + "\nRespond again, satisfying every item."
    )


# ===========================================================================
# COUNCIL ROUTER — the thing that replaces Michael's clipboard
# ===========================================================================

class CouncilRouter:
    def __init__(
        self,
        gate: SubprocessSpendGate | None = None,
        relay_dir: Path | None = None,
        gateway: CouncilDispatchGateway | None = None,
        caller_identity: str = "helm.council.router",
    ):
        ensure_guard()
        self.gate = gate or SubprocessSpendGate()
        self.relay_dir = relay_dir or RELAY_DIR
        self.relay_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.relay_dir / "dispatch_ledger.jsonl"
        self.caller_identity = caller_identity
        self.gateway = gateway or CouncilDispatchGateway(spend_gate=self.gate)

    # -- one adapter, one attempt -------------------------------------------
    def dispatch_one(self, task: TaskEnvelope, adapter_name: str,
                     prompt_override: str | None = None,
                     revision_of: str | None = None) -> ResultEnvelope:
        adapter = ADAPTERS.get(adapter_name)
        if adapter is None:
            return ResultEnvelope(task_id=task.task_id, adapter=adapter_name,
                                  status="BLOCKED", blocks=["UNKNOWN_ADAPTER"])

        effective = TaskEnvelope(**{**asdict(task),
                                    "prompt": prompt_override or task.prompt})

        dtype = ADAPTER_DISPATCH_TYPE.get(adapter.name)
        if dtype is None:
            return ResultEnvelope(
                task_id=task.task_id,
                adapter=adapter_name,
                status="BLOCKED",
                blocks=["UNKNOWN_DISPATCH_TYPE"],
            )

        # THE ONLY SPAWN POINT. Everything external goes through the gateway.
        gw_req = GatewayRequest(
            task_id=task.task_id,
            pert_node=task.pert_node or "",
            caller_identity=self.caller_identity,
            dispatch_type=dtype,
            prompt=effective.prompt,
            scope=task.scope,
            evidence_contract=list(task.evidence_contract),
            frontier_required=task.frontier_required,
            frontier_justification=(
                "task declares frontier_required for independent council review"
                if task.frontier_required
                else ""
            ),
            timeout_seconds=task.timeout_seconds,
            per_task_cap_usd=task.per_task_cap_usd,
            milestone_ceiling_usd=task.milestone_ceiling_usd,
            binary=adapter.binary,
            argv=adapter.argv(effective),
            cwd=getattr(adapter, "scratch_cwd", None),
            metadata={"model": getattr(adapter, "model", None)},
        )
        res = self.gateway.dispatch(gw_req)

        env = ResultEnvelope(
            task_id=task.task_id,
            adapter=adapter.name,
            status=res.status,
            output=res.output,
            blocks=res.blocks,
            cost_usd=res.estimated_cost,
            latency_ms=res.latency_ms,
            external_call=res.external_call,
            response_sha256=res.output_digest or None,
            cost_ledger_hash=res.record_hash or None,
            revision_of=revision_of,
            evidence={
                "task_digest": task.digest(),
                "prompt_sha256": _sha(effective.prompt),
                "exit_code": res.exit_code,
                "stderr_tail": (res.stderr or "")[-400:],
                "gateway_dispatch_id": res.dispatch_id,
                "decision_status": res.decision_status,
                "billing_source": res.billing_source,
                "provider_reported_cost": res.provider_reported_cost,
                "credit_balance_authoritative": res.credit_balance_authoritative,
            },
        )
        verdict, reasons = critic_review(task, env)
        env.critic_verdict = verdict
        env.critic_reasons = reasons
        self._ledger(task, env)
        return env

    # -- the full council loop: dispatch -> critic -> one revision -> aggregate
    def run_council_task(self, task: TaskEnvelope,
                         adapters: list[str],
                         max_revisions: int = 1) -> dict:
        attempts: list[ResultEnvelope] = []

        for name in adapters:
            res = self.dispatch_one(task, name)
            attempts.append(res)

            revisions = 0
            while res.critic_verdict == "REVISE" and revisions < max_revisions:
                revisions += 1
                res = self.dispatch_one(
                    task, name,
                    prompt_override=revision_prompt(task, res, res.critic_reasons),
                    revision_of=res.response_sha256,
                )
                attempts.append(res)

        accepted = [a for a in attempts if a.critic_verdict == "ACCEPT"]
        total_cost = round(sum(a.cost_usd for a in attempts), 6)

        # PERT binding: the node moves ONLY on validated evidence from >= 2 adapters
        # that each independently satisfied the evidence contract.
        distinct_accepting = {a.adapter for a in accepted}
        if len(distinct_accepting) >= 2:
            node_state, reason = "COMPLETED", "MULTI_ADAPTER_VALIDATED_EVIDENCE"
        elif len(distinct_accepting) == 1:
            node_state, reason = "PARTIAL", "SINGLE_ADAPTER_ONLY_NO_CORROBORATION"
        elif any(a.status == "BLOCKED" for a in attempts):
            node_state, reason = "BLOCKED", "ADAPTER_BLOCKED"
        else:
            node_state, reason = "UNKNOWN", "NO_ADAPTER_SATISFIED_EVIDENCE_CONTRACT"

        summary = {
            "task_id": task.task_id,
            "task_digest": task.digest(),
            "pert_node": task.pert_node,
            "adapters_dispatched": adapters,
            "attempts": len(attempts),
            "revisions_performed": sum(1 for a in attempts if a.revision_of),
            "accepted_adapters": sorted(distinct_accepting),
            "pert_node_state": node_state,
            "pert_node_reason": reason,
            "total_cost_usd": total_cost,
            "external_calls": sum(1 for a in attempts if a.external_call),
            "founder_intervention_required": node_state == "BLOCKED"
            and any("FOUNDER_GATE" in b for a in attempts for b in a.blocks),
            "manual_copy_paste_operations": 0,     # the whole point
            "results": [asdict(a) for a in attempts],
            "completed_at": _now(),
        }
        (self.relay_dir / f"{task.task_id}.council.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    def _ledger(self, task: TaskEnvelope, env: ResultEnvelope) -> None:
        entry = {
            "ts": _now(),
            "task_id": task.task_id,
            "task_digest": task.digest(),
            "adapter": env.adapter,
            "status": env.status,
            "critic_verdict": env.critic_verdict,
            "critic_reasons": env.critic_reasons,
            "response_sha256": env.response_sha256,
            "cost_ledger_hash": env.cost_ledger_hash,
            "cost_usd": env.cost_usd,
            "external_call": env.external_call,
            "revision_of": env.revision_of,
        }
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())


def new_task_id(prefix: str = "H1D") -> str:
    return f"{prefix}-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6].upper()}"
