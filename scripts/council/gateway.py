"""HELM H1D.7 — CouncilDispatchGateway: universal model-dispatch choke point.

Every model, CLI, SDK, HTTP, or subprocess AI dispatch MUST pass through
``CouncilDispatchGateway.dispatch()``. Raw urllib / requests / httpx / sockets /
provider SDKs / model subprocesses outside this module (or its sole transport
backend ``spend_gate.py``) are violations.

Runtime guard (``ModelDispatchGuard``) fails closed when model binaries or
provider hosts are touched without an active gateway token.

Spend ledger fields keep estimated vs provider-reported costs separate.
Never claim an estimated balance is provider-authoritative.
"""
from __future__ import annotations

import contextvars
import datetime
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from scripts.council.spend_gate import (
    COST_GOVERNOR,
    COST_LEDGER,
    CostLedger,
    GROK_CREDIT_FLOOR_USD,
    MONTHLY_GUARDRAIL_USD,
    SubprocessSpendGate,
    estimate_cost_usd,
)

ROOT = Path(__file__).resolve().parents[2]
RELAY_DIR = ROOT / "coordination" / "council" / "relay"
GATEWAY_LEDGER = RELAY_DIR / "gateway_dispatch_ledger.jsonl"
DEFAULT_POLICY_PATH = ROOT / "coordination" / "council" / "gateway_policy.json"

# Context token set only while the gateway is actively dispatching.
_GATEWAY_TOKEN: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "helm_council_gateway_token", default=None
)

# Model CLI binaries that may not be spawned outside the gateway.
MODEL_CLI_BINARIES = frozenset(
    {"grok", "gemini", "ollama", "claude", "codex", "chatgpt"}
)

# Hosts that require a gateway token for non-loopback model traffic.
MODEL_API_HOSTS = frozenset(
    {
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
        "api.x.ai",
        "api.groq.com",
    }
)

# Loopback model endpoints (Ollama / LM Studio) for execute-class traffic.
LOCAL_MODEL_PORTS = frozenset({11434, 1234})


class DispatchType(str, Enum):
    LOCAL_OLLAMA = "LOCAL_OLLAMA"
    LOCAL_LM_STUDIO = "LOCAL_LM_STUDIO"
    CLI_GROK = "CLI_GROK"
    CLI_GEMINI = "CLI_GEMINI"
    CLI_CLAUDE = "CLI_CLAUDE"
    API_OPENAI = "API_OPENAI"
    API_ANTHROPIC = "API_ANTHROPIC"


class GatewayStatus(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED_AUTHORIZATION = "BLOCKED_AUTHORIZATION"
    BLOCKED_POLICY = "BLOCKED_POLICY"
    BLOCKED_SPEND = "BLOCKED_SPEND"
    BLOCKED_EGRESS = "BLOCKED_EGRESS"
    BLOCKED_EXECUTABLE = "BLOCKED_EXECUTABLE"
    BLOCKED_SCOPE = "BLOCKED_SCOPE"
    BLOCKED_LEDGER = "BLOCKED_LEDGER"
    BLOCKED_UNKNOWN = "BLOCKED_UNKNOWN"
    ERROR = "ERROR"


# Map adapter name / dispatch type
DISPATCH_TYPE_FOR_ADAPTER = {
    "ollama": DispatchType.LOCAL_OLLAMA,
    "lm_studio": DispatchType.LOCAL_LM_STUDIO,
    "grok": DispatchType.CLI_GROK,
    "gemini": DispatchType.CLI_GEMINI,
    "claude": DispatchType.CLI_CLAUDE,
    "openai": DispatchType.API_OPENAI,
    "anthropic": DispatchType.API_ANTHROPIC,
}

ADAPTER_FOR_DISPATCH_TYPE = {v: k for k, v in DISPATCH_TYPE_FOR_ADAPTER.items()}

LOCAL_DISPATCH_TYPES = frozenset(
    {DispatchType.LOCAL_OLLAMA, DispatchType.LOCAL_LM_STUDIO}
)
FRONTIER_DISPATCH_TYPES = frozenset(
    {
        DispatchType.CLI_GROK,
        DispatchType.CLI_GEMINI,
        DispatchType.CLI_CLAUDE,
        DispatchType.API_OPENAI,
        DispatchType.API_ANTHROPIC,
    }
)
METERED_API_TYPES = frozenset({DispatchType.API_OPENAI, DispatchType.API_ANTHROPIC})
CLI_TYPES = frozenset(
    {DispatchType.CLI_GROK, DispatchType.CLI_GEMINI, DispatchType.CLI_CLAUDE, DispatchType.LOCAL_OLLAMA}
)

DEFAULT_EXECUTABLE_ALLOWLIST = {
    DispatchType.CLI_GROK.value: ["grok"],
    DispatchType.CLI_GEMINI.value: ["gemini"],
    DispatchType.CLI_CLAUDE.value: ["claude"],
    DispatchType.LOCAL_OLLAMA.value: ["ollama"],
    DispatchType.LOCAL_LM_STUDIO.value: [],  # HTTP local only
    DispatchType.API_OPENAI.value: [],
    DispatchType.API_ANTHROPIC.value: [],
}

DEFAULT_ENDPOINT_ALLOWLIST = {
    DispatchType.LOCAL_OLLAMA.value: [
        "http://127.0.0.1:11434",
        "http://localhost:11434",
    ],
    DispatchType.LOCAL_LM_STUDIO.value: [
        "http://127.0.0.1:1234",
        "http://localhost:1234",
    ],
    DispatchType.API_OPENAI.value: ["https://api.openai.com"],
    DispatchType.API_ANTHROPIC.value: ["https://api.anthropic.com"],
    DispatchType.CLI_GROK.value: [],
    DispatchType.CLI_GEMINI.value: [],
    DispatchType.CLI_CLAUDE.value: [],
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def gateway_token_active() -> bool:
    return bool(_GATEWAY_TOKEN.get())


class UngatedDispatchError(PermissionError):
    """Raised when model I/O is attempted outside CouncilDispatchGateway."""

    def __init__(self, detail: str):
        super().__init__(f"BLOCKED_EGRESS: unguarded model dispatch — {detail}")
        self.detail = detail


# ---------------------------------------------------------------------------
# Runtime guard — patches subprocess + urllib for model targets
# ---------------------------------------------------------------------------

class ModelDispatchGuard:
    """Fail-closed intercept for model CLI binaries and provider hosts.

    Install once per process (tests and production runners). Only code holding
    an active gateway context token may touch protected targets.
    """

    _installed = False
    _orig_run: Any = None
    _orig_popen: Any = None
    _orig_urlopen: Any = None
    _orig_create_connection: Any = None

    @classmethod
    def install(cls) -> None:
        if cls._installed:
            return
        cls._orig_run = subprocess.run
        cls._orig_popen = subprocess.Popen
        cls._orig_urlopen = urllib.request.urlopen
        cls._orig_create_connection = socket.create_connection

        def _check_argv(args: Any) -> None:
            if gateway_token_active():
                return
            argv0 = ""
            if isinstance(args, (list, tuple)) and args:
                argv0 = str(Path(str(args[0])).name)
            elif isinstance(args, str):
                argv0 = Path(args.split()[0]).name if args.strip() else ""
            if argv0 in MODEL_CLI_BINARIES:
                raise UngatedDispatchError(f"subprocess binary '{argv0}'")

        def guarded_run(*a, **kw):
            args = a[0] if a else kw.get("args")
            _check_argv(args)
            return cls._orig_run(*a, **kw)

        def guarded_popen(*a, **kw):
            args = a[0] if a else kw.get("args")
            _check_argv(args)
            return cls._orig_popen(*a, **kw)

        def _host_port_from_req(req_or_url: Any) -> tuple[str, int | None]:
            if hasattr(req_or_url, "full_url"):
                url = req_or_url.full_url
            else:
                url = str(req_or_url)
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            port = parsed.port
            if port is None:
                if parsed.scheme == "https":
                    port = 443
                elif parsed.scheme == "http":
                    port = 80
            return host, port

        def guarded_urlopen(url, *a, **kw):
            if not gateway_token_active():
                host, port = _host_port_from_req(url)
                if host in MODEL_API_HOSTS:
                    raise UngatedDispatchError(f"urllib host '{host}'")
                if host in {"127.0.0.1", "localhost", "::1"} and port in LOCAL_MODEL_PORTS:
                    # Allow GET health probes; block chat/generate execute paths
                    full = getattr(url, "full_url", str(url)).lower()
                    method = getattr(url, "get_method", lambda: "GET")().upper()
                    if method != "GET" or any(
                        x in full for x in ("/chat", "/generate", "/completions", "/api/generate", "/v1/chat")
                    ):
                        raise UngatedDispatchError(f"local model execute '{host}:{port}'")
            return cls._orig_urlopen(url, *a, **kw)

        subprocess.run = guarded_run  # type: ignore[assignment]
        subprocess.Popen = guarded_popen  # type: ignore[assignment]
        urllib.request.urlopen = guarded_urlopen  # type: ignore[assignment]
        cls._installed = True

    @classmethod
    def uninstall(cls) -> None:
        if not cls._installed:
            return
        if cls._orig_run is not None:
            subprocess.run = cls._orig_run  # type: ignore[assignment]
        if cls._orig_popen is not None:
            subprocess.Popen = cls._orig_popen  # type: ignore[assignment]
        if cls._orig_urlopen is not None:
            urllib.request.urlopen = cls._orig_urlopen  # type: ignore[assignment]
        cls._installed = False


def ensure_guard() -> None:
    """Install guard unless explicitly disabled (HELM_COUNCIL_GUARD=0)."""
    if os.environ.get("HELM_COUNCIL_GUARD", "1") != "0":
        ModelDispatchGuard.install()


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

def default_policy() -> dict:
    return {
        "schema": "h1d7-gateway-policy-v1",
        "policy_version": "1.0",
        "issued_at": "2026-07-12T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "stale_after_seconds": 86400 * 365,
        "local_first": True,
        "frontier_escalation_only": True,
        "external_dispatch_allowed": True,  # frontier CLIs with justification
        "metered_api_allowed": False,  # founder gate still required
        "environment": "local_only",
        "authorized_adapters": ["grok", "gemini", "ollama"],
        "authorized_dispatch_types": [
            DispatchType.LOCAL_OLLAMA.value,
            DispatchType.CLI_GROK.value,
            DispatchType.CLI_GEMINI.value,
        ],
        "executable_allowlist": DEFAULT_EXECUTABLE_ALLOWLIST,
        "endpoint_allowlist": DEFAULT_ENDPOINT_ALLOWLIST,
        "monthly_cap_usd": MONTHLY_GUARDRAIL_USD,
        "default_per_task_cap_usd": 0.50,
        "credit_floor_usd": GROK_CREDIT_FLOOR_USD,
        "require_task_id": True,
        "require_pert_node": True,
        "require_caller_identity": True,
        "require_ledger": True,
    }


def load_policy(path: Path | None = None) -> dict | None:
    p = path or DEFAULT_POLICY_PATH
    if not p.exists():
        return default_policy()
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None  # unreadable => fail closed


# ---------------------------------------------------------------------------
# Request / result envelopes
# ---------------------------------------------------------------------------

@dataclass
class GatewayRequest:
    task_id: str
    pert_node: str
    caller_identity: str
    dispatch_type: DispatchType | str
    prompt: str
    scope: str = "read-only"
    evidence_contract: list[str] = field(default_factory=list)
    frontier_required: bool = False
    frontier_justification: str = ""
    authorization_state: str = "STANDING"  # STANDING | FOUNDER_GRANTED | NONE
    timeout_seconds: int = 300
    per_task_cap_usd: float = 0.50
    milestone_ceiling_usd: float | None = None
    environment: str = "local_only"
    external_dispatch_allowed: bool = True
    binary: str | None = None
    endpoint: str | None = None
    argv: list[str] | None = None
    cwd: str | None = None
    metadata: dict = field(default_factory=dict)

    def normalized_type(self) -> DispatchType:
        if isinstance(self.dispatch_type, DispatchType):
            return self.dispatch_type
        return DispatchType(str(self.dispatch_type))

    def adapter_name(self) -> str:
        return ADAPTER_FOR_DISPATCH_TYPE.get(self.normalized_type(), "unknown")


@dataclass
class GatewayDecision:
    status: str
    blocks: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    policy_version: str | None = None

    @property
    def allowed(self) -> bool:
        return self.status == GatewayStatus.ALLOWED.value


@dataclass
class GatewayResult:
    dispatch_id: str
    task_id: str
    pert_node: str
    adapter: str
    dispatch_type: str
    status: str  # COMPLETED | BLOCKED | FAILED | TIMEOUT | ERROR
    decision_status: str
    blocks: list[str] = field(default_factory=list)
    output: str = ""
    stderr: str = ""
    exit_code: int | None = None
    latency_ms: int = 0
    estimated_cost: float = 0.0
    provider_reported_cost: float | None = None
    billing_source: str = "estimated_from_tokens_or_request"
    credit_balance_observed: float | None = None
    credit_balance_authoritative: bool = False
    input_digest: str = ""
    output_digest: str = ""
    started_at: str = ""
    completed_at: str = ""
    external_call: bool = False
    previous_record_hash: str = ""
    record_hash: str = ""
    ledger_entry: dict | None = None


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------

class GatewayLedger:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else GATEWAY_LEDGER
        self._force_fail = False  # tests inject ledger failure

    def last_hash(self) -> str:
        if not self.path.exists():
            return "GENESIS"
        last = "GENESIS"
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                last = json.loads(line).get("record_hash") or last
            except Exception:
                continue
        return last

    def append(self, record: dict) -> dict:
        if self._force_fail:
            raise OSError("LEDGER_WRITE_FAILED")
        prev = self.last_hash()
        body = dict(record)
        body["previous_record_hash"] = prev
        body["record_hash"] = _sha(json.dumps(body, sort_keys=True))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(body, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return body


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------

class CouncilDispatchGateway:
    """Single enforceable choke point for all model dispatch."""

    def __init__(
        self,
        policy: dict | None = None,
        policy_path: Path | None = None,
        gateway_ledger: GatewayLedger | None = None,
        spend_gate: SubprocessSpendGate | None = None,
        governor_path: Path | None = None,
        transport: Callable[..., Any] | None = None,
        now_fn: Callable[[], datetime.datetime] | None = None,
    ):
        ensure_guard()
        if policy is not None:
            self.policy = policy
        else:
            self.policy = load_policy(policy_path)
        self.gateway_ledger = gateway_ledger or GatewayLedger()
        self.governor_path = governor_path or COST_GOVERNOR
        self.spend_gate = spend_gate or SubprocessSpendGate(
            governor_path=self.governor_path
        )
        self.transport = transport  # optional test double for CLI execution
        self.now_fn = now_fn or (lambda: datetime.datetime.now(datetime.timezone.utc))
        self.spent_this_run_usd = 0.0

    # -- authorize (preflight) ----------------------------------------------
    def authorize(self, req: GatewayRequest) -> GatewayDecision:
        blocks: list[str] = []
        status = GatewayStatus.ALLOWED

        if self.policy is None:
            return GatewayDecision(
                status=GatewayStatus.BLOCKED_POLICY.value,
                blocks=["POLICY_UNREADABLE_OR_MALFORMED"],
            )

        # Stale / expiry
        try:
            exp = self.policy.get("expires_at")
            if exp:
                exp_dt = datetime.datetime.fromisoformat(exp.replace("Z", "+00:00"))
                if self.now_fn() > exp_dt:
                    return GatewayDecision(
                        status=GatewayStatus.BLOCKED_POLICY.value,
                        blocks=["POLICY_EXPIRED"],
                    )
            issued = self.policy.get("issued_at")
            stale_after = int(self.policy.get("stale_after_seconds") or 0)
            if issued and stale_after > 0:
                issued_dt = datetime.datetime.fromisoformat(issued.replace("Z", "+00:00"))
                age = (self.now_fn() - issued_dt).total_seconds()
                if age > stale_after:
                    return GatewayDecision(
                        status=GatewayStatus.BLOCKED_POLICY.value,
                        blocks=["POLICY_STALE"],
                    )
        except Exception:
            return GatewayDecision(
                status=GatewayStatus.BLOCKED_POLICY.value,
                blocks=["POLICY_TIMESTAMP_MALFORMED"],
            )

        if self.policy.get("require_task_id", True) and not (req.task_id or "").strip():
            blocks.append("MISSING_TASK_ID")
            status = GatewayStatus.BLOCKED_SCOPE

        if self.policy.get("require_pert_node", True) and not (req.pert_node or "").strip():
            blocks.append("MISSING_PERT_NODE")
            status = GatewayStatus.BLOCKED_SCOPE

        if self.policy.get("require_caller_identity", True) and not (
            req.caller_identity or ""
        ).strip():
            blocks.append("MISSING_CALLER_IDENTITY")
            status = GatewayStatus.BLOCKED_AUTHORIZATION

        try:
            dtype = req.normalized_type()
        except Exception:
            return GatewayDecision(
                status=GatewayStatus.BLOCKED_UNKNOWN.value,
                blocks=["UNKNOWN_DISPATCH_TYPE"],
            )

        authorized_types = set(self.policy.get("authorized_dispatch_types") or [])
        if dtype.value not in authorized_types:
            # Unsupported adapter — typed blocker, no silent fallback
            if dtype in METERED_API_TYPES and not self.policy.get("metered_api_allowed"):
                blocks.append("FOUNDER_GATE_REQUIRED_METERED_API")
                status = GatewayStatus.BLOCKED_AUTHORIZATION
            else:
                blocks.append(f"DISPATCH_TYPE_NOT_AUTHORIZED:{dtype.value}")
                status = GatewayStatus.BLOCKED_POLICY

        authorized_adapters = set(self.policy.get("authorized_adapters") or [])
        adapter = req.adapter_name()
        if adapter not in authorized_adapters and dtype.value in authorized_types:
            # CLI type authorized but adapter name mismatch
            if adapter != "unknown":
                blocks.append(f"ADAPTER_NOT_AUTHORIZED:{adapter}")
                status = GatewayStatus.BLOCKED_POLICY

        # Local-first: frontier requires justification
        local_first = bool(self.policy.get("local_first", True))
        if local_first and dtype in FRONTIER_DISPATCH_TYPES:
            if not req.frontier_required:
                blocks.append("LOCAL_FIRST_VIOLATION_FRONTIER_NOT_REQUIRED")
                status = GatewayStatus.BLOCKED_POLICY
            elif not (req.frontier_justification or "").strip():
                blocks.append("FRONTIER_JUSTIFICATION_REQUIRED")
                status = GatewayStatus.BLOCKED_POLICY

        if dtype in FRONTIER_DISPATCH_TYPES and not req.external_dispatch_allowed:
            blocks.append("EXTERNAL_DISPATCH_PROHIBITED")
            status = GatewayStatus.BLOCKED_EGRESS

        env_pol = self.policy.get("environment") or "local_only"
        if env_pol == "local_only" and req.environment not in ("local_only", "local"):
            blocks.append("ENVIRONMENT_RESTRICTED")
            status = GatewayStatus.BLOCKED_POLICY

        # Executable allowlist
        exec_allow = (self.policy.get("executable_allowlist") or {}).get(dtype.value, [])
        binary = req.binary or (
            (req.argv[0] if req.argv else None)
            if req.argv
            else ADAPTER_FOR_DISPATCH_TYPE.get(dtype)
        )
        if dtype in CLI_TYPES or dtype == DispatchType.LOCAL_OLLAMA:
            bin_name = Path(str(binary)).name if binary else ""
            if not bin_name:
                blocks.append("EXECUTABLE_MISSING")
                status = GatewayStatus.BLOCKED_EXECUTABLE
            elif exec_allow and bin_name not in exec_allow:
                blocks.append(f"EXECUTABLE_NOT_ALLOWLISTED:{bin_name}")
                status = GatewayStatus.BLOCKED_EXECUTABLE
            elif shutil.which(bin_name) is None and self.transport is None:
                # transport double may not need real binary
                blocks.append("CLI_NOT_INSTALLED")
                status = GatewayStatus.BLOCKED_EXECUTABLE

        # Endpoint allowlist for HTTP types
        ep_allow = (self.policy.get("endpoint_allowlist") or {}).get(dtype.value, [])
        if dtype in (
            DispatchType.API_OPENAI,
            DispatchType.API_ANTHROPIC,
            DispatchType.LOCAL_LM_STUDIO,
        ) or (dtype == DispatchType.LOCAL_OLLAMA and req.endpoint):
            if req.endpoint:
                ok = any(req.endpoint.startswith(a) for a in ep_allow) if ep_allow else False
                if ep_allow and not ok:
                    blocks.append(f"ENDPOINT_NOT_ALLOWLISTED:{req.endpoint}")
                    status = GatewayStatus.BLOCKED_EGRESS

        # Authorization state for metered APIs
        if dtype in METERED_API_TYPES:
            if req.authorization_state != "FOUNDER_GRANTED":
                blocks.append("FOUNDER_GATE_REQUIRED_METERED_API")
                status = GatewayStatus.BLOCKED_AUTHORIZATION

        # Spend controls
        est = estimate_cost_usd(adapter if adapter != "unknown" else "grok", req.prompt)
        if dtype in LOCAL_DISPATCH_TYPES:
            est = 0.0
        elif dtype == DispatchType.CLI_GEMINI:
            est = 0.0
        elif dtype in METERED_API_TYPES:
            est = float("inf") if req.authorization_state != "FOUNDER_GRANTED" else 0.01

        per_cap = float(req.per_task_cap_usd or self.policy.get("default_per_task_cap_usd") or 0.5)
        if est > per_cap:
            blocks.append("PER_TASK_CAP_EXCEEDED")
            status = GatewayStatus.BLOCKED_SPEND

        # Budget evidence for non-local
        if dtype not in LOCAL_DISPATCH_TYPES:
            gov = self._load_gov()
            if gov is None:
                blocks.append("NO_BUDGET_EVIDENCE")
                status = GatewayStatus.BLOCKED_SPEND
            elif not isinstance(gov, dict):
                blocks.append("MALFORMED_BUDGET_STATE")
                status = GatewayStatus.BLOCKED_SPEND
            else:
                monthly_cap = float(
                    self.policy.get("monthly_cap_usd")
                    or gov.get("monthly_incremental_budget_usd")
                    or MONTHLY_GUARDRAIL_USD
                )
                try:
                    mtd = self.spend_gate.ledger.month_to_date_usd()
                except Exception:
                    blocks.append("LEDGER_UNREADABLE")
                    status = GatewayStatus.BLOCKED_LEDGER
                    mtd = 0.0
                if mtd + (est if est != float("inf") else 0) > monthly_cap:
                    blocks.append("MONTHLY_BUDGET_EXCEEDED")
                    status = GatewayStatus.BLOCKED_SPEND

                if dtype == DispatchType.CLI_GROK:
                    credits = gov.get("grok", {}).get("credits_remaining_usd")
                    if credits is None:
                        blocks.append("NO_BUDGET_EVIDENCE")
                        status = GatewayStatus.BLOCKED_SPEND
                    else:
                        floor = float(self.policy.get("credit_floor_usd", GROK_CREDIT_FLOOR_USD))
                        if float(credits) - est < floor:
                            blocks.append("GROK_CREDITS_BELOW_FLOOR")
                            status = GatewayStatus.BLOCKED_SPEND

        if self.policy.get("require_ledger", True):
            try:
                # Ensure ledger path is writable
                self.gateway_ledger.path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                blocks.append("LEDGER_UNAVAILABLE")
                status = GatewayStatus.BLOCKED_LEDGER

        if req.milestone_ceiling_usd is not None:
            if self.spent_this_run_usd + (0 if est == float("inf") else est) > float(
                req.milestone_ceiling_usd
            ):
                blocks.append("MILESTONE_CEILING_EXCEEDED")
                status = GatewayStatus.BLOCKED_SPEND

        if blocks and status == GatewayStatus.ALLOWED:
            status = GatewayStatus.BLOCKED_UNKNOWN

        return GatewayDecision(
            status=status.value if isinstance(status, GatewayStatus) else status,
            blocks=sorted(set(blocks)),
            estimated_cost=0.0 if est == float("inf") else est,
            policy_version=str(self.policy.get("policy_version")),
        )

    def _load_gov(self) -> Any:
        if not self.governor_path.exists():
            return None
        try:
            return json.loads(self.governor_path.read_text(encoding="utf-8"))
        except Exception:
            return "MALFORMED"

    # -- dispatch -----------------------------------------------------------
    def dispatch(self, req: GatewayRequest) -> GatewayResult:
        dispatch_id = f"GD-{secrets.token_hex(6).upper()}"
        started = _now()
        decision = self.authorize(req)
        adapter = req.adapter_name()
        dtype = (
            req.normalized_type()
            if not isinstance(req.dispatch_type, str) or req.dispatch_type in DispatchType.__members__.values() or True
            else DispatchType.CLI_GROK
        )
        try:
            dtype = req.normalized_type()
        except Exception:
            dtype = DispatchType.CLI_GROK

        input_digest = _sha(req.prompt)

        if not decision.allowed:
            return self._finalize_blocked(
                dispatch_id=dispatch_id,
                req=req,
                adapter=adapter,
                dtype=dtype,
                decision=decision,
                started=started,
                input_digest=input_digest,
            )

        # Ledger write must succeed before live I/O
        token = secrets.token_hex(16)
        token_handle = _GATEWAY_TOKEN.set(token)
        try:
            # Pre-write attempt to detect ledger failure (fail closed before I/O)
            if self.gateway_ledger._force_fail:
                return GatewayResult(
                    dispatch_id=dispatch_id,
                    task_id=req.task_id,
                    pert_node=req.pert_node,
                    adapter=adapter,
                    dispatch_type=dtype.value,
                    status="BLOCKED",
                    decision_status=GatewayStatus.BLOCKED_LEDGER.value,
                    blocks=["LEDGER_WRITE_FAILED"],
                    started_at=started,
                    completed_at=_now(),
                    input_digest=input_digest,
                )

            if self.transport is not None:
                # Test double — no real provider call
                out = self.transport(req)
                stdout = out.get("stdout", "") if isinstance(out, dict) else str(out)
                stderr = out.get("stderr", "") if isinstance(out, dict) else ""
                code = out.get("exit_code", 0) if isinstance(out, dict) else 0
                status = out.get("status", "COMPLETED" if code == 0 else "FAILED")
                latency = int(out.get("latency_ms", 0)) if isinstance(out, dict) else 0
                external = dtype in FRONTIER_DISPATCH_TYPES
                est = decision.estimated_cost
            elif dtype in CLI_TYPES or dtype == DispatchType.LOCAL_OLLAMA:
                from scripts.council.spend_gate import DispatchRequest as SGReq

                argv = req.argv or self._default_argv(req, dtype)
                sg_req = SGReq(
                    task_id=req.task_id,
                    adapter=adapter,
                    prompt=req.prompt,
                    binary=req.binary or (argv[0] if argv else adapter),
                    frontier_required=req.frontier_required,
                    timeout_seconds=req.timeout_seconds,
                    per_task_cap_usd=req.per_task_cap_usd,
                    cwd=req.cwd,
                    milestone_ceiling_usd=req.milestone_ceiling_usd,
                    metadata={"gateway_dispatch_id": dispatch_id, "pert_node": req.pert_node},
                )
                # spend_gate.preflight may double-check; gateway already authorized
                res = self.spend_gate.dispatch(sg_req, argv)
                stdout, stderr, code = res.stdout, res.stderr, res.exit_code
                status = res.status
                latency = res.latency_ms
                external = res.external_call
                est = res.estimated_cost_usd
                if status == "TIMEOUT":
                    # fail closed already
                    pass
            elif dtype in METERED_API_TYPES:
                # No silent HTTP: metered APIs remain founder-gated even if allowed in policy
                return self._finalize_blocked(
                    dispatch_id=dispatch_id,
                    req=req,
                    adapter=adapter,
                    dtype=dtype,
                    decision=GatewayDecision(
                        status=GatewayStatus.BLOCKED_AUTHORIZATION.value,
                        blocks=["FOUNDER_GATE_REQUIRED_METERED_API", "API_TRANSPORT_NOT_ENABLED"],
                    ),
                    started=started,
                    input_digest=input_digest,
                )
            else:
                return self._finalize_blocked(
                    dispatch_id=dispatch_id,
                    req=req,
                    adapter=adapter,
                    dtype=dtype,
                    decision=GatewayDecision(
                        status=GatewayStatus.BLOCKED_UNKNOWN.value,
                        blocks=["NO_TRANSPORT_FOR_DISPATCH_TYPE"],
                    ),
                    started=started,
                    input_digest=input_digest,
                )

            completed = _now()
            output_digest = _sha(stdout)
            credit_obs = None
            gov = self._load_gov()
            if isinstance(gov, dict) and adapter == "grok":
                credit_obs = gov.get("grok", {}).get("credits_remaining_usd")

            record = {
                "dispatch_id": dispatch_id,
                "task_id": req.task_id,
                "pert_node": req.pert_node,
                "adapter": adapter,
                "dispatch_type": dtype.value,
                "estimated_cost": est,
                "provider_reported_cost": None,
                "billing_source": "estimated_from_tokens_or_request",
                "credit_balance_observed": credit_obs,
                "credit_balance_authoritative": False,
                "input_digest": input_digest,
                "output_digest": output_digest,
                "started_at": started,
                "completed_at": completed,
                "status": status,
                "caller_identity": req.caller_identity,
                "decision_status": GatewayStatus.ALLOWED.value,
            }
            try:
                ledger_entry = self.gateway_ledger.append(record)
            except OSError:
                return GatewayResult(
                    dispatch_id=dispatch_id,
                    task_id=req.task_id,
                    pert_node=req.pert_node,
                    adapter=adapter,
                    dispatch_type=dtype.value,
                    status="BLOCKED",
                    decision_status=GatewayStatus.BLOCKED_LEDGER.value,
                    blocks=["LEDGER_WRITE_FAILED"],
                    started_at=started,
                    completed_at=_now(),
                    input_digest=input_digest,
                )

            self.spent_this_run_usd += float(est or 0)
            return GatewayResult(
                dispatch_id=dispatch_id,
                task_id=req.task_id,
                pert_node=req.pert_node,
                adapter=adapter,
                dispatch_type=dtype.value,
                status=status,
                decision_status=GatewayStatus.ALLOWED.value,
                blocks=[],
                output=stdout,
                stderr=stderr,
                exit_code=code,
                latency_ms=latency,
                estimated_cost=float(est or 0),
                provider_reported_cost=None,
                billing_source="estimated_from_tokens_or_request",
                credit_balance_observed=credit_obs,
                credit_balance_authoritative=False,
                input_digest=input_digest,
                output_digest=output_digest,
                started_at=started,
                completed_at=completed,
                external_call=external,
                previous_record_hash=ledger_entry.get("previous_record_hash", ""),
                record_hash=ledger_entry.get("record_hash", ""),
                ledger_entry=ledger_entry,
            )
        except subprocess.TimeoutExpired:
            return GatewayResult(
                dispatch_id=dispatch_id,
                task_id=req.task_id,
                pert_node=req.pert_node,
                adapter=adapter,
                dispatch_type=dtype.value,
                status="TIMEOUT",
                decision_status=GatewayStatus.ERROR.value,
                blocks=["ADAPTER_TIMEOUT"],
                started_at=started,
                completed_at=_now(),
                input_digest=input_digest,
            )
        except Exception as e:
            return GatewayResult(
                dispatch_id=dispatch_id,
                task_id=req.task_id,
                pert_node=req.pert_node,
                adapter=adapter,
                dispatch_type=dtype.value,
                status="ERROR",
                decision_status=GatewayStatus.ERROR.value,
                blocks=[f"DISPATCH_ERROR:{type(e).__name__}"],
                stderr=str(e)[:400],
                started_at=started,
                completed_at=_now(),
                input_digest=input_digest,
            )
        finally:
            _GATEWAY_TOKEN.reset(token_handle)

    def _default_argv(self, req: GatewayRequest, dtype: DispatchType) -> list[str]:
        if dtype == DispatchType.CLI_GROK:
            return [
                "grok",
                "-p",
                req.prompt,
                "--permission-mode",
                "plan",
                "--output-format",
                "plain",
                "--no-subagents",
                "--cwd",
                str(ROOT),
            ]
        if dtype == DispatchType.CLI_GEMINI:
            return [
                "gemini",
                "-p",
                req.prompt,
                "--approval-mode",
                "plan",
                "--skip-trust",
            ]
        if dtype == DispatchType.LOCAL_OLLAMA:
            model = (req.metadata or {}).get("model", "llama3.1:8b")
            return ["ollama", "run", model, req.prompt]
        if dtype == DispatchType.CLI_CLAUDE:
            return ["claude", "-p", req.prompt]
        return [req.binary or "false"]

    def _finalize_blocked(
        self,
        *,
        dispatch_id: str,
        req: GatewayRequest,
        adapter: str,
        dtype: DispatchType,
        decision: GatewayDecision,
        started: str,
        input_digest: str,
    ) -> GatewayResult:
        completed = _now()
        record = {
            "dispatch_id": dispatch_id,
            "task_id": req.task_id,
            "pert_node": req.pert_node,
            "adapter": adapter,
            "dispatch_type": getattr(dtype, "value", str(dtype)),
            "estimated_cost": 0.0,
            "provider_reported_cost": None,
            "billing_source": "none_blocked",
            "credit_balance_observed": None,
            "credit_balance_authoritative": False,
            "input_digest": input_digest,
            "output_digest": _sha(""),
            "started_at": started,
            "completed_at": completed,
            "status": "BLOCKED",
            "blocks": decision.blocks,
            "decision_status": decision.status,
            "caller_identity": req.caller_identity,
        }
        ledger_entry = None
        try:
            if not self.gateway_ledger._force_fail:
                ledger_entry = self.gateway_ledger.append(record)
        except OSError:
            pass
        return GatewayResult(
            dispatch_id=dispatch_id,
            task_id=req.task_id,
            pert_node=req.pert_node,
            adapter=adapter,
            dispatch_type=getattr(dtype, "value", str(dtype)),
            status="BLOCKED",
            decision_status=decision.status,
            blocks=decision.blocks,
            estimated_cost=0.0,
            provider_reported_cost=None,
            billing_source="none_blocked",
            credit_balance_authoritative=False,
            input_digest=input_digest,
            output_digest=_sha(""),
            started_at=started,
            completed_at=completed,
            previous_record_hash=(ledger_entry or {}).get("previous_record_hash", ""),
            record_hash=(ledger_entry or {}).get("record_hash", ""),
            ledger_entry=ledger_entry,
        )


def result_to_dict(r: GatewayResult) -> dict:
    return asdict(r)
