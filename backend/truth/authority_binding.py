"""Immutable authority binding for LEASED / RUNNING / VERIFYING tasks.

Required fields (every active stage):
  task_id, lease_id, authority_class, authority_decision_id, authority_status,
  decision_digest, dispatch_digest, scheduler_instance_id

Propagation chain:
  decision record → task envelope → lease → dispatch → adapter result
  → validator → artifact manifest → terminal record

Fail-closed:
  active + missing authority_decision_id → AUTHORITY_INCOMPLETE
  decision digest mismatch               → AUTHORITY_BINDING_MISMATCH
  dispatch digest mismatch               → DISPATCH_BINDING_MISMATCH
  scheduler instance mismatch            → RUNTIME_SOURCE_MISMATCH
  revoked / expired decision             → dispatch prohibited

Historical records without proof remain UNPROVEN — never retrofit.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
BINDING_LEDGER = ROOT / "coordination" / "founder" / "authority_binding_ledger.jsonl"
DECISION_LEDGER = ROOT / "coordination" / "founder" / "autonomous_decision_ledger.jsonl"

UNKNOWN = "UNKNOWN"


class AuthorityPanelStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    MISMATCH = "MISMATCH"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    UNPROVEN = "UNPROVEN"
    EMPTY_OK = "EMPTY_OK"  # idle only


class BindingError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha(obj: Any) -> str:
    if isinstance(obj, (bytes, bytearray)):
        raw = bytes(obj)
    elif isinstance(obj, str):
        raw = obj.encode("utf-8")
    else:
        raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def task_identity_digest(task: dict[str, Any]) -> str:
    """Digest of the task identity at classification (not the whole mutable row)."""
    canon = {
        "task_id": task.get("task_id"),
        "name": task.get("name"),
        "target_pod": task.get("target_pod") or task.get("factory"),
        "mission_prompt_sha": _sha(task.get("mission_prompt") or task.get("prompt") or ""),
        "dispatch_type": task.get("dispatch_type", "LOCAL_OLLAMA"),
        "required_capability": task.get("required_capability"),
    }
    return _sha(canon)


@dataclass
class AuthorityBinding:
    task_id: str
    lease_id: str
    authority_class: str
    authority_decision_id: str
    authority_status: str  # ACTIVE | REVOKED | EXPIRED | SUPERSEDED | UNPROVEN
    decision_digest: str
    dispatch_digest: str
    scheduler_instance_id: str
    task_digest: str
    decision_id: str = ""
    created_at: str = field(default_factory=_now)
    lease_status: str = "LEASED"  # LEASED | RUNNING | VERIFYING | COMPLETE | FAILED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def required_fields_present(self) -> bool:
        req = (
            self.task_id, self.lease_id, self.authority_class,
            self.authority_decision_id, self.authority_status,
            self.decision_digest, self.dispatch_digest, self.scheduler_instance_id,
        )
        return all(x not in (None, "", UNKNOWN) for x in req)


def create_autonomous_decision(
    *,
    task: dict[str, Any],
    authority_class: str,
    scheduler_instance_id: str,
    expires_at: Optional[str] = None,
    status: str = "ACTIVE",
    ledger: Optional[Path] = None,
) -> dict[str, Any]:
    """Persist a decision record for this dispatch (standing AUTONOMOUS or test fixtures)."""
    task_id = str(task.get("task_id") or "")
    task_digest = task_identity_digest(task)
    body = {
        "schema_version": "authority-binding-v1",
        "decision_id": f"DEC-{_sha(task_id + scheduler_instance_id + _now())[:16]}",
        "task_id": task_id,
        "task_digest": task_digest,
        "authority_class": authority_class,
        "status": status,  # ACTIVE | REVOKED | EXPIRED
        "scheduler_instance_id": scheduler_instance_id,
        "created_at": _now(),
        "expires_at": expires_at,
        "scope": {
            "factory_ids": [task.get("target_pod") or task.get("factory") or "*"],
            "product_ids": ["*"],
            "mission_ids": ["*"],
            "environments": ["local_only", "*"],
            "action_types": ["LOCAL_OLLAMA", "dispatch", "*"],
        },
    }
    body["decision_digest"] = _sha({k: v for k, v in body.items() if k != "decision_digest"})
    body["authority_decision_id"] = "AUTH-" + _sha(
        body["decision_id"] + body["decision_digest"] + task_id
    )[:16]

    path = ledger or DECISION_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(body, sort_keys=True) + "\n")
    return body


def compute_dispatch_digest(
    *,
    task_id: str,
    authority_decision_id: str,
    decision_digest: str,
    envelope_hash: str,
    scheduler_instance_id: str,
) -> str:
    return _sha({
        "task_id": task_id,
        "authority_decision_id": authority_decision_id,
        "decision_digest": decision_digest,
        "envelope_hash": envelope_hash,
        "scheduler_instance_id": scheduler_instance_id,
    })


def mint_binding(
    *,
    task: dict[str, Any],
    lease_id: str,
    authority_class: str,
    scheduler_instance_id: str,
    envelope_hash: str,
    decision: Optional[dict[str, Any]] = None,
    decision_ledger: Optional[Path] = None,
) -> AuthorityBinding:
    """Create binding after lease acquisition; persist to binding ledger."""
    if not decision:
        decision = create_autonomous_decision(
            task=task,
            authority_class=authority_class,
            scheduler_instance_id=scheduler_instance_id,
            ledger=decision_ledger,
        )
    task_id = str(task.get("task_id") or "")
    task_digest = task_identity_digest(task)
    if decision.get("task_digest") and decision["task_digest"] != task_digest:
        raise BindingError(
            "AUTHORITY_BINDING_MISMATCH",
            "decision task_digest does not match live task identity",
        )
    if decision.get("task_id") and decision["task_id"] != task_id:
        raise BindingError(
            "AUTHORITY_BINDING_MISMATCH",
            "decision bound to a different task_id",
        )
    st = str(decision.get("status") or "ACTIVE").upper()
    if st == "REVOKED":
        raise BindingError("AUTHORITY_REVOKED", decision.get("decision_id", ""))
    if st == "EXPIRED" or _is_expired(decision.get("expires_at")):
        raise BindingError("AUTHORITY_EXPIRED", decision.get("decision_id", ""))

    adid = str(decision.get("authority_decision_id") or "")
    if not adid:
        raise BindingError("AUTHORITY_INCOMPLETE", "decision missing authority_decision_id")

    ddigest = str(decision.get("decision_digest") or "")
    if not ddigest:
        raise BindingError("AUTHORITY_INCOMPLETE", "decision missing decision_digest")

    # Recompute decision digest over the decision body (without digest field) if present
    # For minted decisions, decision_digest was set correctly at creation.

    dispatch_digest = compute_dispatch_digest(
        task_id=task_id,
        authority_decision_id=adid,
        decision_digest=ddigest,
        envelope_hash=envelope_hash,
        scheduler_instance_id=scheduler_instance_id,
    )

    binding = AuthorityBinding(
        task_id=task_id,
        lease_id=lease_id,
        authority_class=authority_class,
        authority_decision_id=adid,
        authority_status=st if st in ("ACTIVE", "REVOKED", "EXPIRED") else "ACTIVE",
        decision_digest=ddigest,
        dispatch_digest=dispatch_digest,
        scheduler_instance_id=scheduler_instance_id,
        task_digest=task_digest,
        decision_id=str(decision.get("decision_id") or ""),
        lease_status="LEASED",
    )
    persist_binding(binding)
    return binding


def persist_binding(binding: AuthorityBinding, ledger: Optional[Path] = None) -> None:
    path = ledger or BINDING_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(binding.to_dict(), sort_keys=True) + "\n")


def load_decision(authority_decision_id: str, ledger: Optional[Path] = None) -> Optional[dict]:
    path = ledger or DECISION_LEDGER
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("authority_decision_id") == authority_decision_id:
            return d
    return None


def _is_expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        t = time.strptime(str(expires_at).split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
        return time.mktime(t) <= time.time()
    except Exception:
        return True


def assert_active_binding(binding: Optional[dict[str, Any]] | AuthorityBinding) -> None:
    """Reject active-stage work without a complete binding."""
    if binding is None:
        raise BindingError("AUTHORITY_INCOMPLETE", "no binding present")
    d = binding.to_dict() if isinstance(binding, AuthorityBinding) else dict(binding)
    for field in (
        "task_id", "lease_id", "authority_class", "authority_decision_id",
        "authority_status", "decision_digest", "dispatch_digest", "scheduler_instance_id",
    ):
        if not d.get(field) or d.get(field) == UNKNOWN:
            raise BindingError("AUTHORITY_INCOMPLETE", f"missing {field}")
    st = str(d.get("authority_status") or "").upper()
    if st == "REVOKED":
        raise BindingError("AUTHORITY_REVOKED", d.get("authority_decision_id", ""))
    if st == "EXPIRED":
        raise BindingError("AUTHORITY_EXPIRED", d.get("authority_decision_id", ""))


def assert_decision_digest(binding: dict[str, Any], decision: dict[str, Any]) -> None:
    expected = decision.get("decision_digest")
    actual = binding.get("decision_digest")
    if not expected or expected != actual:
        raise BindingError("AUTHORITY_BINDING_MISMATCH", "decision_digest mismatch")
    if decision.get("task_id") and decision.get("task_id") != binding.get("task_id"):
        raise BindingError("AUTHORITY_BINDING_MISMATCH", "decision bound to another task")
    if decision.get("authority_decision_id") != binding.get("authority_decision_id"):
        raise BindingError("AUTHORITY_BINDING_MISMATCH", "authority_decision_id mismatch")


def assert_dispatch_digest(binding: dict[str, Any], *, envelope_hash: str) -> None:
    expected = compute_dispatch_digest(
        task_id=str(binding.get("task_id")),
        authority_decision_id=str(binding.get("authority_decision_id")),
        decision_digest=str(binding.get("decision_digest")),
        envelope_hash=envelope_hash,
        scheduler_instance_id=str(binding.get("scheduler_instance_id")),
    )
    if expected != binding.get("dispatch_digest"):
        raise BindingError("DISPATCH_BINDING_MISMATCH", "dispatch_digest does not match envelope")


def assert_scheduler_instance(binding: dict[str, Any], scheduler_instance_id: str) -> None:
    if binding.get("scheduler_instance_id") != scheduler_instance_id:
        raise BindingError("RUNTIME_SOURCE_MISMATCH", "scheduler_instance_id mismatch on binding")


def assert_lease_owns_decision(binding: dict[str, Any], lease_id: str) -> None:
    if binding.get("lease_id") != lease_id:
        raise BindingError("AUTHORITY_BINDING_MISMATCH", "decision/binding owned by another lease")


def assert_artifact_does_not_infer_authority(
    *,
    artifact_meta: dict[str, Any],
    binding: dict[str, Any],
) -> None:
    """Artifact may only carry authority fields identical to the binding — never invent."""
    for field in ("authority_decision_id", "decision_digest", "dispatch_digest"):
        if field in artifact_meta and artifact_meta[field] != binding.get(field):
            raise BindingError(
                "AUTHORITY_BINDING_MISMATCH",
                f"artifact {field} does not match binding (inference prohibited)",
            )
    # If artifact omits authority, that is incomplete for COMPLETE status
    if not artifact_meta.get("authority_decision_id"):
        raise BindingError(
            "AUTHORITY_INCOMPLETE",
            "artifact manifest missing authority_decision_id (cannot infer from task_id)",
        )


def panel_status_from_workers(
    workers: list[dict[str, Any]],
    *,
    idle: bool,
) -> dict[str, Any]:
    """Wall authority panel aggregation."""
    if idle and not workers:
        return {
            "panel_status": AuthorityPanelStatus.EMPTY_OK.value,
            "reason": "no LEASED/RUNNING/VERIFYING tasks",
            "bindings": [],
            "missing_bindings": [],
            "mismatches": [],
            "revoked": [],
            "expired": [],
            "unproven": [],
        }

    complete, incomplete, mismatch, revoked, expired, unproven = [], [], [], [], [], []
    for w in workers:
        adid = w.get("authority_decision_id")
        st = str(w.get("authority_status") or "").upper()
        entry = {
            "task_id": w.get("task_id") or w.get("lease"),
            "lease_id": w.get("lease_id"),
            "authority_decision_id": adid,
            "authority_class": w.get("authority_class"),
            "authority_status": st or UNKNOWN,
            "decision_digest": w.get("decision_digest"),
            "dispatch_digest": w.get("dispatch_digest"),
            "scheduler_instance_id": w.get("scheduler_instance_id"),
        }
        if not adid:
            incomplete.append(entry)
        elif st == "REVOKED":
            revoked.append(entry)
        elif st == "EXPIRED":
            expired.append(entry)
        elif st == "UNPROVEN" or w.get("unproven"):
            unproven.append(entry)
        elif w.get("binding_mismatch") or w.get("dispatch_mismatch"):
            mismatch.append(entry)
        elif all(entry.get(f) for f in (
            "lease_id", "authority_class", "authority_decision_id",
            "decision_digest", "dispatch_digest", "scheduler_instance_id",
        )):
            complete.append(entry)
        else:
            incomplete.append(entry)

    if revoked:
        status = AuthorityPanelStatus.REVOKED.value
    elif expired:
        status = AuthorityPanelStatus.EXPIRED.value
    elif mismatch:
        status = AuthorityPanelStatus.MISMATCH.value
    elif incomplete:
        status = AuthorityPanelStatus.INCOMPLETE.value
    elif unproven and not complete:
        status = AuthorityPanelStatus.UNPROVEN.value
    elif complete and not incomplete and not mismatch:
        status = AuthorityPanelStatus.COMPLETE.value
    else:
        status = AuthorityPanelStatus.INCOMPLETE.value

    return {
        "panel_status": status,
        "reason": {
            AuthorityPanelStatus.COMPLETE.value: "all active workers fully authority-bound",
            AuthorityPanelStatus.INCOMPLETE.value: "active work missing authority fields",
            AuthorityPanelStatus.MISMATCH.value: "authority or dispatch digest mismatch",
            AuthorityPanelStatus.REVOKED.value: "active work references revoked decision",
            AuthorityPanelStatus.EXPIRED.value: "active work references expired decision",
            AuthorityPanelStatus.UNPROVEN.value: "historical/unproven binding only",
        }.get(status, status),
        "bindings": complete,
        "missing_bindings": incomplete,
        "mismatches": mismatch,
        "revoked": revoked,
        "expired": expired,
        "unproven": unproven,
        "active_work_count": len(workers),
        "authoritative_pass_prohibited": status != AuthorityPanelStatus.COMPLETE.value,
    }
