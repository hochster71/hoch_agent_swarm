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


def dispatch_ollama(task: dict[str, Any], binding: AuthorityBinding, *,
                    model: str = "llama3.1:8b", scope: dict[str, str] | None = None,
                    timeout: int = 120) -> dict[str, Any]:
    """Enforce authority, THEN dispatch to the live local adapter. Returns a result envelope
    that carries the SAME authority_decision_id (RESULT-AUTHORITY-BINDING-CONTROL)."""
    enforce(task, binding, scope=scope)          # raises on any failure — no dispatch on deny
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
