"""authority_gateway.py — no authority decision id => no lease => no dispatch => no transition.

The gateway enforces authority INDEPENDENTLY of the scheduler. Even if a caller reaches
the gateway with a task, the gateway re-checks the authority binding and rejects any task
whose binding is missing, unknown, expired, revoked, superseded, out of scope, single-use-
consumed, or whose canonical digest no longer matches what was classified.

Typed denials (no silent pass):
    AUTHORITY_ID_MISSING
    AUTHORITY_RECORD_NOT_FOUND
    AUTHORITY_SCOPE_MISMATCH
    AUTHORITY_EXPIRED
    AUTHORITY_REVOKED
    AUTHORITY_SUPERSEDED
    AUTHORITY_SINGLE_USE_CONSUMED
    TASK_MUTATED_AFTER_CLASSIFICATION
    SUPPLY_CHAIN_PROVENANCE_DENIED     (SR-3)

SR-3 SUPPLY CHAIN. Authority answers "is this task allowed?". Provenance answers a
question the gateway never used to ask: "is the thing I am about to talk to the thing I
think it is?". A model tag can be re-pointed at different weights and a CLI binary can be
swapped on $PATH; both were previously invoked on the strength of a NAME. Now every
dispatch verifies the sha256 of the tool binary and the digest/identity of the model
endpoint against coordination/security/supply_chain_attestations.json, BEFORE the
subprocess is spawned or the HTTP request is made, and FAILS CLOSED on anything it cannot
observe. See backend/truth/supply_chain.py for what this does and does not prove.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.council.decision_record import load_corpus, apply_supersession
from backend.truth import supply_chain as sc         # SR-3 provenance attestation

ROOT = Path(__file__).resolve().parents[2]
OLLAMA = "http://127.0.0.1:11434/api/generate"

# fields that define the canonical, classification-bound identity of a task. If ANY change
# after classification, the digest changes and the gateway rejects (TASK-MUTATION-CONTROL).
CANONICAL_FIELDS = ("task_id", "action_text", "environment", "adapter", "target",
                    "data_classification", "side_effects")


class AuthorityDenied(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def canonical_task_digest(task: dict[str, Any]) -> str:
    """Stable digest over ONLY the canonical fields, order-independent."""
    canon = {k: task.get(k) for k in CANONICAL_FIELDS}
    return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()


@dataclass
class AuthorityBinding:
    """Immutable classification record. Produced once, at classification time."""
    authority_decision_id: str
    classified_task_sha256: str
    classified_at: str
    classifier_version: str
    authority_matrix_sha256: str
    decision_id: str | None = None          # the RATIFIED decision that authorizes it
    single_use: bool = False

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _matrix_sha() -> str:
    m = ROOT / "coordination" / "founder" / "authority_matrix.json"
    return hashlib.sha256(m.read_bytes()).hexdigest() if m.exists() else "NO_MATRIX"


def bind_classification(task: dict[str, Any], *, decision_id: str | None,
                        single_use: bool = False,
                        classifier_version: str = "founder_model@v2") -> AuthorityBinding:
    """Create the immutable authority binding for a task the scheduler classified AUTONOMOUS."""
    adid = "AUTH-" + hashlib.sha256(
        f"{task.get('task_id')}|{decision_id}|{time.time()}".encode()
    ).hexdigest()[:16]
    return AuthorityBinding(
        authority_decision_id=adid,
        classified_task_sha256=canonical_task_digest(task),
        classified_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        classifier_version=classifier_version,
        authority_matrix_sha256=_matrix_sha(),
        decision_id=decision_id,
        single_use=single_use,
    )


# durable single-use consumption ledger — a bound single-use decision spends exactly once
_CONSUMED = ROOT / "coordination" / "founder" / "gateway_consumed_bindings.jsonl"


def _already_consumed(adid: str) -> bool:
    if not _CONSUMED.exists():
        return False
    return any(json.loads(l).get("authority_decision_id") == adid
               for l in _CONSUMED.read_text().splitlines() if l.strip())


def _mark_consumed(adid: str) -> None:
    _CONSUMED.parent.mkdir(parents=True, exist_ok=True)
    with open(_CONSUMED, "a", encoding="utf-8") as f:
        f.write(json.dumps({"authority_decision_id": adid,
                            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")


def enforce(task: dict[str, Any], binding: AuthorityBinding, *,
            scope: dict[str, str] | None = None) -> None:
    """GATEWAY-AUTHORITY-CONTROL. Raises AuthorityDenied on any failure. Returns None on pass.

    The gateway does NOT infer or look up the id after dispatch begins — the binding is
    passed in explicitly and must internally verify against the corpus + the live task."""
    if not binding or not binding.authority_decision_id:
        raise AuthorityDenied("AUTHORITY_ID_MISSING", "no authority_decision_id on the task")

    # TASK-MUTATION-CONTROL: the live task must still hash to what was classified.
    if canonical_task_digest(task) != binding.classified_task_sha256:
        raise AuthorityDenied("TASK_MUTATED_AFTER_CLASSIFICATION",
                              "canonical task digest changed since classification")

    # if a RATIFIED decision backs this binding, it must still authorize.
    if binding.decision_id:
        recs = {r.raw["decision_id"]: r for r in apply_supersession(load_corpus())}
        rec = recs.get(binding.decision_id)
        if rec is None:
            raise AuthorityDenied("AUTHORITY_RECORD_NOT_FOUND", binding.decision_id)
        st = rec.raw.get("status")
        if st == "REVOKED":
            raise AuthorityDenied("AUTHORITY_REVOKED", binding.decision_id)
        if st == "SUPERSEDED" or rec.raw.get("superseded_by"):
            raise AuthorityDenied("AUTHORITY_SUPERSEDED", binding.decision_id)
        if rec.is_expired():
            raise AuthorityDenied("AUTHORITY_EXPIRED", binding.decision_id)
        sc = scope or {}
        ok, why = rec.authorizes(
            factory=sc.get("factory", "*"), product=sc.get("product", "*"),
            mission=sc.get("mission", "*"), environment=sc.get("environment", "*"),
            action_type=sc.get("action_type", "*"))
        if not ok:
            raise AuthorityDenied("AUTHORITY_SCOPE_MISMATCH", why)

    # SINGLE-USE-CONSUMPTION-CONTROL
    if binding.single_use and _already_consumed(binding.authority_decision_id):
        raise AuthorityDenied("AUTHORITY_SINGLE_USE_CONSUMED", binding.authority_decision_id)


REGISTRY = ROOT / "coordination" / "council" / "adapter_registry.json"

# A task carrying (or fishing for) a secret must NEVER reach an external model.
_SECRET_PATTERNS = (
    "sk_live", "sk_test", "whsec_", "service_role", "private key", "BEGIN RSA",
    "auth.json", ".env", "credential", "password", "api_key", "apikey",
    "bearer ", "refresh_token", "access_token",
)
_SECRET_CLASSES = {"SECRET", "CREDENTIAL", "RESTRICTED", "PII"}


def _registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text())["adapters"] if REGISTRY.exists() else {}


def enforce_adapter(task: dict[str, Any], adapter_id: str) -> None:
    """ADAPTER-REGISTRY + DATA-CLASSIFICATION controls. Raises AuthorityDenied."""
    reg = _registry()
    a = reg.get(adapter_id)
    if a is None:
        raise AuthorityDenied("ADAPTER_NOT_REGISTERED", adapter_id)
    if a.get("health") != "READY":
        raise AuthorityDenied("ADAPTER_NOT_READY", f"{adapter_id} health={a.get('health')}")

    # the adapter may not receive secret-classified data
    dc = str(task.get("data_classification", "")).upper()
    if dc in _SECRET_CLASSES and not a.get("credential_exposure_allowed", False):
        raise AuthorityDenied("DATA_CLASSIFICATION_VIOLATION",
                              f"{adapter_id} may not receive {dc} data")

    # ...and the prompt itself must not carry or fish for a secret
    blob = f"{task.get('action_text','')} {task.get('target','')}".lower()
    for pat in _SECRET_PATTERNS:
        if pat.lower() in blob:
            raise AuthorityDenied("SECRET_BEARING_TASK_DENIED",
                                  f"task references '{pat}' — refusing to send to {adapter_id}")


def dispatch_grok(task: dict[str, Any], binding: AuthorityBinding, *,
                  scope: dict[str, str] | None = None, model: str | None = None,
                  timeout: int = 180) -> dict[str, Any]:
    """Governed GROK_CLI dispatch. Authority + adapter + secret checks BEFORE the subprocess.

    Hardened invocation: headless single-turn, EMPTY tool allowlist (zero tool execution =>
    it cannot read the filesystem, so ~/.grok/auth.json and .env are unreachable), no
    subagents, no memory, no web egress, bounded cwd. `always-approve` is irrelevant when
    there are no tools to approve."""
    import subprocess

    enforce(task, binding, scope=scope)          # authority binding
    enforce_adapter(task, "GROK_CLI")            # registry + data classification + secret scan

    a = _registry()["GROK_CLI"]
    # SR-3 SUPPLY CHAIN. Verify the sha256 of the binary we are ABOUT TO EXECUTE and the
    # identity of the model flag BEFORE the subprocess is spawned. A swapped binary on
    # $PATH or an unattested `-m` model is a supply-chain substitution — fail closed.
    ok, reason = sc.verify_provenance(
        tool_id="GROK_CLI", adapter_id="GROK_CLI", model=model or "grok-default",
        registry_path=sc.REGISTRY, binary_path=a.get("binary"))
    if not ok:
        raise AuthorityDenied("SUPPLY_CHAIN_PROVENANCE_DENIED", reason)

    if binding.single_use:
        _mark_consumed(binding.authority_decision_id)

    cwd = Path(a["hardening"]["bounded_cwd"])
    cwd.mkdir(parents=True, exist_ok=True)

    # --max-turns 1 CANCELLED Grok mid-thought: it spent the single turn reasoning and was
    # killed before it could answer (stopReason: "Cancelled", "Error: max turns reached").
    # The output came back EMPTY and auto_council read that as "0 findings — clean".
    # A strangled model is not a clean audit. Give it room to think AND answer.
    cmd = [a["binary"], "-p", task["action_text"], "--output-format", "json",
           "--tools", "", "--no-subagents", "--no-memory", "--disable-web-search",
           "--max-turns", "4", "--verbatim", "--cwd", str(cwd)]
    if model:
        cmd += ["-m", model]

    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd))
    out = proc.stdout.strip()
    stop_reason = None
    try:
        parsed = json.loads(out)
        text = parsed.get("result") or parsed.get("response") or parsed.get("text") or ""
        stop_reason = parsed.get("stopReason")
    except json.JSONDecodeError:
        text = out

    # FAIL LOUDLY. An empty adapter response must NEVER be read downstream as "nothing to
    # report". Silence is not agreement; a strangled model is not a clean audit.
    if not text.strip() or stop_reason in ("Cancelled", "MaxTurns"):
        raise RuntimeError(
            f"GROK_DISPATCH_EMPTY: stopReason={stop_reason} exit={proc.returncode} "
            f"stderr={(proc.stderr or '')[:160]} — refusing to report an empty audit as clean")

    return {
        "result_envelope_version": "1.0",
        "authority_decision_id": binding.authority_decision_id,
        "classified_task_sha256": binding.classified_task_sha256,
        "task_id": task["task_id"],
        "adapter": "GROK_CLI",
        "model": model or "grok-default",
        "output": text,
        "exit_code": proc.returncode,
        "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latency_s": round(time.time() - t0, 3),
    }


def dispatch_ollama(task: dict[str, Any], binding: AuthorityBinding, *,
                    model: str = "llama3.1:8b", scope: dict[str, str] | None = None,
                    timeout: int = 120) -> dict[str, Any]:
    """Enforce authority, THEN dispatch to the live local adapter. Returns a result envelope
    that carries the SAME authority_decision_id (RESULT-AUTHORITY-BINDING-CONTROL)."""
    enforce(task, binding, scope=scope)          # raises on any failure — no dispatch on deny

    # SR-3 SUPPLY CHAIN. Verify the LIVE weights digest the ollama daemon would serve for
    # this tag matches what was attested, BEFORE the prompt is sent. A re-pointed tag
    # (`ollama create llama3.1:8b -f ./evil`) or an unknown model id is denied here — the
    # HTTP request is never made. Fails closed if the endpoint is unobservable.
    ok, reason = sc.verify_provenance(
        adapter_id="LOCAL_OLLAMA", model=model, registry_path=sc.REGISTRY)
    if not ok:
        raise AuthorityDenied("SUPPLY_CHAIN_PROVENANCE_DENIED", reason)

    if binding.single_use:
        _mark_consumed(binding.authority_decision_id)

    body = json.dumps({"model": model, "prompt": task["action_text"], "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = json.loads(resp.read().decode())
    return {
        "result_envelope_version": "1.0",
        "authority_decision_id": binding.authority_decision_id,   # SAME id echoed back
        "classified_task_sha256": binding.classified_task_sha256,
        "task_id": task["task_id"],
        "model": model,
        "output": raw.get("response", ""),
        "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "latency_s": round(time.time() - t0, 3),
    }
