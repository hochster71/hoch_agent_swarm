"""HELM H1D — SubprocessSpendGate.

THE HOLE THIS CLOSES
--------------------
H1B put an egress gate in front of urllib INSIDE the Python process. A CLI adapter
that shells out (`subprocess.run(["grok", prompt])`) walks straight past it: the
external call happens in a child process, so the authorization binding, the budget
caps, and the consume ledger never see it. Every H1B control is bypassed by one
subprocess call.

This gate sits in front of the subprocess. Nothing in H1D may spawn a model CLI
except through `SubprocessSpendGate.dispatch()`.

WHAT IT ENFORCES (from the founder's ALREADY-RATIFIED policy in cost_governor.json)
-----------------------------------------------------------------------------------
  local_first                 -> a frontier CLI may only run for task classes that
                                 declare frontier_required; otherwise route local.
  frontier_escalation_only    -> same rule, enforced rather than printed.
  grok credits < $25          -> BLOCKED (this threshold already existed in
                                 frontier_escalation_gate.py; it just never ran).
  monthly spend > $200        -> BLOCKED (monthly_incremental_budget_usd).
  per-task cap                -> BLOCKED.
  paid_api_enablement         -> still FOUNDER-GATED (metered API keys are NOT
                                 covered by standing authorization).

FAIL-CLOSED. Absence of budget evidence is a BLOCK, never a pass. Unlike
frontier_escalation_gate.py (always prints PASS, exits 0) and
verify_api_budget_guard.py (compares a hardcoded 0.0 to the budget and therefore
cannot fail), this gate can and does say NO.

EVERY dispatch is metered into cost_ledger.jsonl — which today contains two Linode
invoices and zero model calls. This is the first real model-spend ledger in the repo.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "has_live_project_tracker" / "data"
COST_GOVERNOR = DATA / "cost_governor.json"
COST_LEDGER = Path(os.environ.get("HELM_COST_LEDGER",
                                  ROOT / "hoch_pods" / "compute" / "cost_ledger.jsonl"))

# --- policy constants, sourced from the founder's ratified cost_governor.json ---
GROK_CREDIT_FLOOR_USD = 25.00        # already the threshold in frontier_escalation_gate.py
MONTHLY_GUARDRAIL_USD = 200.00       # cost_governor.monthly_incremental_budget_usd
DEFAULT_PER_TASK_CAP_USD = 0.50      # a single council task may not exceed this

# Adapters that draw on ALREADY-PAID subscriptions/credits (standing authorization).
STANDING_AUTHORIZED = {"grok", "gemini", "ollama"}
# Adapters that bill a metered API key: these stay behind the H1B founder gate.
FOUNDER_GATED = {"openai", "anthropic", "xai_api"}
# Adapters that never leave the machine.
LOCAL_ADAPTERS = {"ollama"}


class SpendBlocked(PermissionError):
    """Raised when a dispatch is refused. Carries stable block codes."""

    def __init__(self, blocks: list[str]):
        self.blocks = blocks
        super().__init__("SUBPROCESS_SPEND_BLOCKED: " + ", ".join(blocks))


B_UNKNOWN_ADAPTER = "UNKNOWN_ADAPTER"
B_FOUNDER_GATE_REQUIRED = "FOUNDER_GATE_REQUIRED_METERED_API"
B_CLI_NOT_INSTALLED = "CLI_NOT_INSTALLED"
B_NO_BUDGET_EVIDENCE = "NO_BUDGET_EVIDENCE"
B_GROK_CREDITS_EXHAUSTED = "GROK_CREDITS_BELOW_FLOOR"
B_MONTHLY_CAP = "MONTHLY_BUDGET_EXCEEDED"
B_TASK_CAP = "PER_TASK_CAP_EXCEEDED"
B_LOCAL_FIRST = "LOCAL_FIRST_VIOLATION_FRONTIER_NOT_REQUIRED"
B_TIMEOUT = "ADAPTER_TIMEOUT"
B_MILESTONE_CEILING = "MILESTONE_CEILING_EXCEEDED"


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# The cost ledger — append-only, hash-chained
# ---------------------------------------------------------------------------

class CostLedger:
    """Append-only, hash-chained record of every model dispatch and its cost.

    Each entry carries prev_hash, so a silently deleted or edited entry breaks the
    chain and is detectable. cost_ledger.jsonl currently holds two Linode invoices
    and no model calls at all; model entries are additive and do not disturb them.
    """

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else COST_LEDGER

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def model_entries(self) -> list[dict]:
        return [e for e in self.entries() if e.get("category") == "model_dispatch"]

    def _last_hash(self) -> str:
        models = self.model_entries()
        return models[-1]["entry_hash"] if models else "GENESIS"

    def month_to_date_usd(self, when: datetime.datetime | None = None) -> float:
        when = when or _now()
        period = when.strftime("%Y-%m")
        return round(sum(
            float(e.get("amount_usd", 0.0))
            for e in self.model_entries()
            if str(e.get("billing_period", "")) == period
        ), 6)

    def append(self, entry: dict) -> dict:
        prev = self._last_hash()
        body = dict(entry)
        body["prev_hash"] = prev
        body["entry_hash"] = hashlib.sha256(
            json.dumps(body, sort_keys=True).encode("utf-8")
        ).hexdigest()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(body, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return body

    def verify_chain(self) -> tuple[bool, list[str]]:
        errs, prev = [], "GENESIS"
        for e in self.model_entries():
            if e.get("prev_hash") != prev:
                errs.append(f"CHAIN_BREAK at {e.get('task_id')}: expected prev {prev}")
            body = {k: v for k, v in e.items() if k != "entry_hash"}
            expect = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            if expect != e.get("entry_hash"):
                errs.append(f"HASH_MISMATCH at {e.get('task_id')}")
            prev = e.get("entry_hash")
        return (not errs), errs


# ---------------------------------------------------------------------------
# Pricing — estimate before the call, meter after it
# ---------------------------------------------------------------------------

# Grok: measured from the founder's own usage in cost_governor.json --
# 1406 requests, $13.59, 43,112,382 tokens => $0.315 per 1M tokens.
GROK_USD_PER_1M_TOKENS = 0.315
# Gemini via the paid Google AI Ultra plan: zero MARGINAL cost per call.
GEMINI_MARGINAL_USD = 0.0
# Local: free.
OLLAMA_MARGINAL_USD = 0.0


def estimate_cost_usd(adapter: str, prompt: str, max_output_tokens: int = 4000) -> float:
    if adapter in ("gemini",):
        return GEMINI_MARGINAL_USD
    if adapter in LOCAL_ADAPTERS:
        return OLLAMA_MARGINAL_USD
    if adapter == "grok":
        tokens = max(1, len(prompt) // 4) + max_output_tokens
        return round((tokens / 1_000_000.0) * GROK_USD_PER_1M_TOKENS, 6)
    return float("inf")          # unknown pricing => infinite => always blocked


@dataclass
class DispatchRequest:
    task_id: str
    adapter: str
    prompt: str
    # The actual executable. The gate verifies THIS is installed -- checking the
    # adapter's name would let a dispatch through that then execs something else.
    binary: str | None = None
    frontier_required: bool = False
    timeout_seconds: int = 300
    per_task_cap_usd: float = DEFAULT_PER_TASK_CAP_USD
    cwd: str | None = None
    milestone_ceiling_usd: float | None = None   # optional hard ceiling across a run
    metadata: dict = field(default_factory=dict)


@dataclass
class DispatchResult:
    task_id: str
    adapter: str
    status: str                  # COMPLETED | BLOCKED | FAILED | TIMEOUT | UNKNOWN
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    latency_ms: int = 0
    estimated_cost_usd: float = 0.0
    external_call: bool = False
    blocks: list[str] = field(default_factory=list)
    ledger_entry_hash: str | None = None
    raw_sha256: str | None = None


class SubprocessSpendGate:
    """The ONLY permitted way to invoke a model CLI in H1D."""

    def __init__(self, ledger: CostLedger | None = None,
                 governor_path: Path | None = None,
                 spent_this_run_usd: float = 0.0):
        self.ledger = ledger or CostLedger()
        self.governor_path = governor_path or COST_GOVERNOR
        self.spent_this_run_usd = spent_this_run_usd

    # -- pre-flight: can this dispatch happen at all? -----------------------
    def preflight(self, req: DispatchRequest) -> list[str]:
        blocks: list[str] = []

        if req.adapter in FOUNDER_GATED:
            # Metered API keys are NOT covered by standing authorization.
            blocks.append(B_FOUNDER_GATE_REQUIRED)
        elif req.adapter not in STANDING_AUTHORIZED:
            blocks.append(B_UNKNOWN_ADAPTER)

        if shutil.which(req.binary or req.adapter) is None:
            blocks.append(B_CLI_NOT_INSTALLED)

        is_local = req.adapter in LOCAL_ADAPTERS
        # local_first: a frontier adapter runs ONLY when the task declares it needs one.
        if not is_local and not req.frontier_required:
            blocks.append(B_LOCAL_FIRST)

        est = estimate_cost_usd(req.adapter, req.prompt)
        if est > req.per_task_cap_usd:
            blocks.append(B_TASK_CAP)

        if req.milestone_ceiling_usd is not None:
            if self.spent_this_run_usd + est > req.milestone_ceiling_usd:
                blocks.append(B_MILESTONE_CEILING)

        # Budget evidence is REQUIRED for any non-local call. Absence => block.
        if not is_local:
            gov = _load(self.governor_path)
            if not gov:
                blocks.append(B_NO_BUDGET_EVIDENCE)
            else:
                if req.adapter == "grok":
                    credits = gov.get("grok", {}).get("credits_remaining_usd")
                    if credits is None:
                        blocks.append(B_NO_BUDGET_EVIDENCE)
                    elif float(credits) - est < GROK_CREDIT_FLOOR_USD:
                        blocks.append(B_GROK_CREDITS_EXHAUSTED)

                cap = float(gov.get("monthly_incremental_budget_usd", MONTHLY_GUARDRAIL_USD))
                if self.ledger.month_to_date_usd() + est > cap:
                    blocks.append(B_MONTHLY_CAP)

        return sorted(set(blocks))

    # -- the gate itself -----------------------------------------------------
    def dispatch(self, req: DispatchRequest, argv: list[str]) -> DispatchResult:
        """Run a model CLI. Refuses first, meters always, fails closed."""
        blocks = self.preflight(req)
        est = estimate_cost_usd(req.adapter, req.prompt)

        if blocks:
            # A refused dispatch is still recorded -- a block leaves a trace.
            self.ledger.append({
                "date": _now().date().isoformat(),
                "billing_period": _now().strftime("%Y-%m"),
                "category": "model_dispatch",
                "task_id": req.task_id,
                "adapter": req.adapter,
                "status": "BLOCKED",
                "blocks": blocks,
                "amount_usd": 0.0,
                "external_call": False,
                "ts": _now().isoformat().replace("+00:00", "Z"),
            })
            return DispatchResult(task_id=req.task_id, adapter=req.adapter,
                                  status="BLOCKED", blocks=blocks,
                                  estimated_cost_usd=0.0, external_call=False)

        external = req.adapter not in LOCAL_ADAPTERS
        t0 = time.time()
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=req.timeout_seconds,
                cwd=req.cwd or str(ROOT),
                # Never hand the child a credential this process was not given.
                env={**os.environ},
            )
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
            status = "COMPLETED" if code == 0 else "FAILED"
        except subprocess.TimeoutExpired:
            stdout, stderr, code, status = "", "adapter timed out", None, "TIMEOUT"
        except Exception as e:                      # fail CLOSED, never silently
            stdout, stderr, code, status = "", f"{type(e).__name__}: {e}", None, "FAILED"

        latency = int((time.time() - t0) * 1000)
        raw_sha = hashlib.sha256((stdout or "").encode("utf-8")).hexdigest()
        actual = est if status in ("COMPLETED", "FAILED", "TIMEOUT") and external else 0.0

        entry = self.ledger.append({
            "date": _now().date().isoformat(),
            "billing_period": _now().strftime("%Y-%m"),
            "category": "model_dispatch",
            "task_id": req.task_id,
            "adapter": req.adapter,
            "status": status,
            "amount_usd": actual,
            "currency": "USD",
            "external_call": external,
            "exit_code": code,
            "latency_ms": latency,
            "prompt_sha256": hashlib.sha256(req.prompt.encode("utf-8")).hexdigest(),
            "response_sha256": raw_sha,
            "ts": _now().isoformat().replace("+00:00", "Z"),
            "note": "marginal cost 0 (already-paid plan)" if external and actual == 0.0 else "",
        })
        self.spent_this_run_usd += actual
        self._decrement_governor(req.adapter, actual)

        return DispatchResult(
            task_id=req.task_id, adapter=req.adapter, status=status,
            stdout=stdout, stderr=stderr, exit_code=code, latency_ms=latency,
            estimated_cost_usd=actual, external_call=external,
            ledger_entry_hash=entry["entry_hash"], raw_sha256=raw_sha,
        )

    def _decrement_governor(self, adapter: str, spent: float) -> None:
        """Make cost_governor.json LIVE. It has been static since 2026-07-02."""
        if spent <= 0 or adapter != "grok":
            return
        gov = _load(self.governor_path)
        if not gov or "grok" not in gov:
            return
        g = gov["grok"]
        g["credits_remaining_usd"] = round(float(g.get("credits_remaining_usd", 0.0)) - spent, 4)
        g["credits_used_usd"] = round(float(g.get("credits_used_usd", 0.0)) + spent, 4)
        g["requests"] = int(g.get("requests", 0)) + 1
        gov["last_metered_at"] = _now().isoformat().replace("+00:00", "Z")
        gov["metered_by"] = "scripts/council/spend_gate.py"
        tmp = self.governor_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(gov, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.governor_path)          # atomic


def budget_status() -> dict:
    """Honest budget snapshot. UNKNOWN when evidence is absent -- never a green default."""
    gov = _load(COST_GOVERNOR)
    ledger = CostLedger()
    chain_ok, chain_errs = ledger.verify_chain()
    if not gov:
        return {"status": "UNKNOWN", "reason": "NO_BUDGET_EVIDENCE",
                "ledger_chain_intact": chain_ok}
    grok = gov.get("grok", {})
    mtd = ledger.month_to_date_usd()
    cap = float(gov.get("monthly_incremental_budget_usd", MONTHLY_GUARDRAIL_USD))
    return {
        "status": "WITHIN_LIMITS" if (
            float(grok.get("credits_remaining_usd", 0)) >= GROK_CREDIT_FLOOR_USD and mtd <= cap
        ) else "BLOCKED",
        "grok_credits_remaining_usd": grok.get("credits_remaining_usd"),
        "grok_credit_floor_usd": GROK_CREDIT_FLOOR_USD,
        "month_to_date_model_spend_usd": mtd,
        "monthly_cap_usd": cap,
        "metered_dispatches": len(ledger.model_entries()),
        "ledger_chain_intact": chain_ok,
        "ledger_chain_errors": chain_errs,
        "last_metered_at": gov.get("last_metered_at"),
    }


if __name__ == "__main__":   # pragma: no cover
    print(json.dumps(budget_status(), indent=2))
