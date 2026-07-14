"""HJOS gated auto-quarantine.

After read-only burn-in, may quarantine ONLY for permitted classes.
Never promotes. Never executes tasks. Never rewrites founder decisions or soak seals.

Quarantine for leases = move lock file to coordination/leases/_quarantine_hjos_<ts>/
and append a RELEASED-style history note. Does not retrofit authority digests.
"""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.jspace.charter import HJOS_CHARTER

ROOT = Path(__file__).resolve().parents[2]
LEASE_DIR = ROOT / "coordination" / "leases"
GOV_PATH = ROOT / "coordination" / "jspace" / "quarantine_governance.json"


def _governance(repo_root=None) -> Dict[str, Any]:
    """Fail-closed governance gate. Mutation is DENIED unless an approved
    authorizing_policy_id is present. A ~5-minute burn-in is NOT authorization.
    Independent audit 2026-07-14."""
    root = Path(repo_root) if repo_root else ROOT
    gp = root / "coordination" / "jspace" / "quarantine_governance.json"
    try:
        g = json.loads(gp.read_text(encoding="utf-8"))
    except Exception:
        return {"automatic_quarantine_enabled": False,
                "orphan_lease_hygiene": "manual_approval",
                "authorizing_policy_id": None, "_missing": True}
    return g


def _mutation_authorized(gov: Dict[str, Any], *, kind: str) -> bool:
    """kind in {"class_quarantine","orphan_hygiene"}. Both require an approved
    policy id. orphan_hygiene additionally requires explicit != manual_approval."""
    if not gov.get("authorizing_policy_id"):
        return False
    if kind == "orphan_hygiene":
        return gov.get("orphan_lease_hygiene") not in (None, "manual_approval", "disabled") \
               and bool(gov.get("automatic_quarantine_enabled"))
    return bool(gov.get("automatic_quarantine_enabled"))

# Map recommended_action / alert subjects → permitted quarantine class
ACTION_TO_CLASS = {
    "QUARANTINE_REQUEST_SECRET_EXPOSURE": "secret_exposure",
    "secret_exposure": "secret_exposure",
    "secret_exposure_scan": "secret_exposure",
    "evidence_tampering": "evidence_tampering",
    "founder_gate_bypass": "founder_gate_bypass",
    "destructive_action": "destructive_action",
}


def permitted_class(reason: str) -> Optional[str]:
    if reason in HJOS_CHARTER.automatic_quarantine_permitted_only_for:
        return reason
    return ACTION_TO_CLASS.get(reason)


def execute_quarantine_if_allowed(
    *,
    enabled: bool,
    reason: str,
    subject: str,
    evidence: List[str],
    cycle_id: str,
    observer: str,
    ledger_append,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute quarantine only when burn-in enabled AND reason is permitted."""
    qclass = permitted_class(reason)
    gov = _governance(repo_root)
    result: Dict[str, Any] = {
        "executed": False,
        "reason": reason,
        "class": qclass,
        "subject": subject,
        "cycle_id": cycle_id,
        "observer": observer,
    }
    if not enabled:
        result["blocked"] = "BURN_IN_INCOMPLETE"
        ledger_append({**result, "execution_authority": "NONE"})
        return result
    if not _mutation_authorized(gov, kind="class_quarantine"):
        result["blocked"] = "GOVERNANCE_DENY_NO_APPROVED_POLICY"
        result["governance_policy_id"] = gov.get("authorizing_policy_id")
        ledger_append({**result, "execution_authority": "NONE"})
        return result
    if not qclass:
        result["blocked"] = "CLASS_NOT_PERMITTED"
        ledger_append({**result, "execution_authority": "NONE"})
        return result
    if qclass not in HJOS_CHARTER.automatic_quarantine_permitted_only_for:
        result["blocked"] = "CHARTER_DENY"
        ledger_append({**result, "execution_authority": "NONE"})
        return result

    root = Path(repo_root) if repo_root else ROOT
    lease_dir = root / "coordination" / "leases"
    actions: List[str] = []

    if qclass == "secret_exposure":
        # Do not delete evidence — flag only + request human rotation
        flag = root / "coordination" / "jspace" / "SECRET_EXPOSURE_FLAG.json"
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(json.dumps({
            "flagged_at": _now(),
            "cycle_id": cycle_id,
            "subject": subject,
            "evidence": evidence,
            "action_required": "ROTATE_CREDENTIALS_HUMAN",
        }, indent=2) + "\n", encoding="utf-8")
        actions.append(str(flag.relative_to(root)) if flag.is_relative_to(root) else str(flag))
        result["executed"] = True
        result["actions"] = actions
        result["execution_authority"] = "HJOS_AUTO_QUARANTINE_POST_BURNIN"
        ledger_append(result)
        return result

    if qclass in ("evidence_tampering", "destructive_action", "founder_gate_bypass"):
        # Quarantine unreadable/corrupt lock names referenced in evidence if under leases/
        qdir = lease_dir / f"_quarantine_hjos_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        qdir.mkdir(parents=True, exist_ok=True)
        for ev in evidence:
            p = Path(ev)
            if not p.is_absolute():
                p = root / ev
            if p.exists() and p.suffix == ".lock" and p.parent == lease_dir:
                dest = qdir / p.name
                shutil.move(str(p), str(dest))
                actions.append(f"moved:{p.name}->{dest}")
        result["executed"] = bool(actions)
        result["actions"] = actions
        result["execution_authority"] = "HJOS_AUTO_QUARANTINE_POST_BURNIN"
        ledger_append(result)
        return result

    result["blocked"] = "NO_HANDLER"
    ledger_append(result)
    return result


def quarantine_expired_orphan_locks(
    *,
    enabled: bool,
    current_instance_id: Optional[str],
    ledger_append,
    repo_root: Optional[Path] = None,
    cycle_id: str = "",
) -> Dict[str, Any]:
    """Hygiene: expire orphan SOAK locks from dead instances after burn-in.

    Not one of the four security classes — recorded separately as lease hygiene.
    Only moves locks that are:
      - status ACTIVE
      - expires_at in the past
      - scheduler_instance_id missing OR != current published instance
    Never touches locks for the current live instance.
    """
    root = Path(repo_root) if repo_root else ROOT
    lease_dir = root / "coordination" / "leases"
    result: Dict[str, Any] = {
        "executed": False,
        "kind": "expired_orphan_lease_hygiene",
        "cycle_id": cycle_id,
        "moved": [],
    }
    if not enabled:
        result["blocked"] = "BURN_IN_INCOMPLETE"
        ledger_append(result)
        return result
    gov = _governance(repo_root)
    if not _mutation_authorized(gov, kind="orphan_hygiene"):
        result["blocked"] = "GOVERNANCE_DENY_ORPHAN_HYGIENE_MANUAL"
        result["governance_policy_id"] = gov.get("authorizing_policy_id")
        ledger_append(result)
        return result
    if not lease_dir.exists():
        return result

    now = datetime.now(timezone.utc)
    qdir = lease_dir / f"_quarantine_hjos_orphans_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    moved = []
    for lock in lease_dir.glob("*.lock"):
        try:
            rec = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            continue
        status = str(rec.get("status") or "").upper()
        if status not in ("ACTIVE", "ACQUIRED", "RUNNING"):
            continue
        exp_s = rec.get("expires_at")
        try:
            exp = datetime.fromisoformat(str(exp_s).replace("Z", "+00:00"))
        except Exception:
            continue
        if exp >= now:
            continue
        inst = rec.get("scheduler_instance_id")
        if current_instance_id and inst == current_instance_id:
            continue  # never touch live instance
        qdir.mkdir(parents=True, exist_ok=True)
        dest = qdir / lock.name
        rec2 = dict(rec)
        rec2["status"] = "RELEASED"
        rec2["released_at"] = _now()
        rec2["release_reason"] = "HJOS_ORPHAN_EXPIRED_QUARANTINE"
        rec2["do_not_retrofit_authority"] = True
        dest.write_text(json.dumps(rec2, indent=2) + "\n", encoding="utf-8")
        lock.unlink(missing_ok=True)
        moved.append({"task_id": rec.get("task_id"), "lease_id": rec.get("lease_id"), "from": lock.name})
        # history
        hist = lease_dir / "_lease_history.jsonl"
        with hist.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "task_id": rec.get("task_id"),
                "lease_id": rec.get("lease_id"),
                "status": "RELEASED",
                "released_at": rec2["released_at"],
                "reason": "HJOS_ORPHAN_EXPIRED_QUARANTINE",
                "scheduler_instance_id": inst,
                "cycle_id": cycle_id,
            }) + "\n")

    result["executed"] = bool(moved)
    result["moved"] = moved
    result["quarantine_dir"] = str(qdir) if moved else None
    ledger_append(result)
    return result


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
