"""HJOS gated containment.

Containment is DENIED unless a founder-approved authorizing_policy_id is present
in coordination/jspace/quarantine_governance.json. A burn-in is NOT authorization.
Independent audit 2026-07-14.

Guarantees enforced here (negative battery, tests/test_jspace_negative.py):
  - FAIL CLOSED   : no policy id / non-string id / invalid governance doc => DENY.
  - NO FALSE-POSITIVE MUTATION : a containment that matches nothing touches nothing
                    (not even an empty quarantine directory).
  - EVIDENCE PRESERVING : quarantined bytes are captured VERBATIM; annotations go
                    to a sidecar, never over the artifact under audit.
  - NO CLOBBER    : a destination collision never overwrites prior evidence.
  - REVERSIBLE    : every artifact carries sha256_before + source_path, so rollback
                    restores exact bytes to the exact path — or refuses.
  - NO SELF-VERIFICATION : the observer that contained cannot certify the containment.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.jspace.charter import HJOS_CHARTER

ROOT = Path(__file__).resolve().parents[2]
LEASE_DIR = ROOT / "coordination" / "leases"
GOV_PATH = ROOT / "coordination" / "jspace" / "quarantine_governance.json"

GOV_SCHEMA = "HJOS_QUARANTINE_GOVERNANCE_v1"
CONTAINMENT_SCHEMA = "HJOS_CONTAINMENT_v1"
VERIFICATION_SCHEMA = "HJOS_CONTAINMENT_VERIFICATION_v1"
ROLLBACK_SCHEMA = "HJOS_CONTAINMENT_ROLLBACK_v1"

EXECUTION_AUTHORITY = "HJOS_CONTAINMENT_UNDER_POLICY"

# Actors that are HJOS itself and therefore may NEVER attest to their own containment.
_SELF_ACTOR_PREFIXES = ("jspace", "hjos")


def _governance(repo_root=None) -> Dict[str, Any]:
    """Fail-closed governance gate. Mutation is DENIED unless an approved
    authorizing_policy_id is present. A ~5-minute burn-in is NOT authorization."""
    root = Path(repo_root) if repo_root else ROOT
    gp = root / "coordination" / "jspace" / "quarantine_governance.json"
    if not gp.exists():
        return {"automatic_quarantine_enabled": False,
                "orphan_lease_hygiene": "manual_approval",
                "authorizing_policy_id": None, "_missing": True}
    try:
        g = json.loads(gp.read_text(encoding="utf-8"))
    except Exception:
        # A governance document we cannot read is not a governance document.
        return {"automatic_quarantine_enabled": False,
                "orphan_lease_hygiene": "manual_approval",
                "authorizing_policy_id": None, "_unreadable": True}
    if not isinstance(g, dict):
        return {"automatic_quarantine_enabled": False,
                "orphan_lease_hygiene": "manual_approval",
                "authorizing_policy_id": None, "_unreadable": True}
    return g


def validate_governance(gov: Dict[str, Any]) -> Dict[str, Any]:
    """Structural validation of the governance document.

    An invalid document can never authorize mutation. An unknown schema version is
    not a licence to move files — it is an unknown contract, and unknown fails closed.
    """
    reasons: List[str] = []
    warnings: List[str] = []
    if not isinstance(gov, dict):
        return {"valid": False, "reasons": ["NOT_AN_OBJECT"], "warnings": []}
    if gov.get("_missing"):
        reasons.append("MISSING_FILE")
    if gov.get("_unreadable"):
        reasons.append("UNREADABLE")

    schema = gov.get("schema")
    if schema is None:
        warnings.append("SCHEMA_ABSENT")  # legacy/unversioned doc — tolerated, not trusted
    elif schema != GOV_SCHEMA:
        reasons.append(f"UNKNOWN_SCHEMA:{schema}")

    pid = gov.get("authorizing_policy_id")
    if pid is not None and (not isinstance(pid, str) or not pid.strip()):
        reasons.append("POLICY_ID_NOT_STRING")

    if gov.get("automatic_quarantine_enabled") and not _valid_policy_id(pid):
        # enabled with no approved policy: contradictory, and DENY is the only safe read
        reasons.append("ENABLED_WITHOUT_APPROVED_POLICY")

    return {"valid": not reasons, "reasons": reasons, "warnings": warnings,
            "authorizing_policy_id": pid if _valid_policy_id(pid) else None}


def _valid_policy_id(pid: Any) -> bool:
    return isinstance(pid, str) and bool(pid.strip())


def _mutation_authorized(gov: Dict[str, Any], *, kind: str) -> bool:
    """kind in {"class_quarantine","orphan_hygiene"}. Both require an approved
    policy id. orphan_hygiene additionally requires explicit != manual_approval."""
    if not isinstance(gov, dict):
        return False
    if gov.get("_missing") or gov.get("_unreadable"):
        return False
    if not _valid_policy_id(gov.get("authorizing_policy_id")):
        return False
    if kind == "orphan_hygiene":
        return gov.get("orphan_lease_hygiene") not in (None, "manual_approval", "disabled") \
               and bool(gov.get("automatic_quarantine_enabled"))
    return bool(gov.get("automatic_quarantine_enabled"))


def _gov_block_reason(gov: Dict[str, Any], *, kind: str) -> Optional[str]:
    """Why containment is denied, distinguishing 'no policy' from 'broken document'."""
    if not _valid_policy_id(gov.get("authorizing_policy_id")):
        return ("GOVERNANCE_DENY_ORPHAN_HYGIENE_MANUAL" if kind == "orphan_hygiene"
                else "GOVERNANCE_DENY_NO_APPROVED_POLICY")
    check = validate_governance(gov)
    if not check["valid"]:
        return "GOVERNANCE_DENY_INVALID_POLICY_DOC"
    if not _mutation_authorized(gov, kind=kind):
        return ("GOVERNANCE_DENY_ORPHAN_HYGIENE_MANUAL" if kind == "orphan_hygiene"
                else "GOVERNANCE_DENY_NO_APPROVED_POLICY")
    return None


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


# ------------------------------------------------------------------ provenance utils
def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rel(path: Path, root: Path) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _collision_safe_dest(qdir: Path, name: str) -> tuple[Path, bool]:
    """Never overwrite an artifact already in quarantine — that is evidence destruction."""
    dest = qdir / name
    if not dest.exists():
        return dest, False
    n = 1
    while True:
        cand = qdir / f"{name}.dup{n}"
        if not cand.exists():
            return cand, True
        n += 1


def _capture(src: Path, qdir: Path, root: Path, annotation: Optional[dict] = None) -> Dict[str, Any]:
    """Move src into quarantine VERBATIM. Bytes are never edited; any annotation is
    written to a sidecar so the captured evidence stays digest-stable and reversible."""
    sha_before = _sha256(src)
    size = src.stat().st_size
    qdir.mkdir(parents=True, exist_ok=True)
    dest, collided = _collision_safe_dest(qdir, src.name)
    shutil.move(str(src), str(dest))
    sha_after = _sha256(dest)
    art: Dict[str, Any] = {
        "source_path": _rel(src, root),
        "dest_path": _rel(dest, root),
        "original_name": src.name,
        "collision": collided,
        "sha256_before": sha_before,
        "sha256_after": sha_after,
        "bytes": size,
        "captured_at": _now(),
    }
    if annotation:
        side = Path(str(dest) + ".hjos.json")
        side.write_text(json.dumps({**annotation,
                                    "quarantined_from": art["source_path"],
                                    "sha256_before": sha_before,
                                    "captured_at": art["captured_at"]},
                                   indent=2, sort_keys=True) + "\n", encoding="utf-8")
        art["sidecar_path"] = _rel(side, root)
    return art


def _base_record(**kw) -> Dict[str, Any]:
    return {
        "schema": CONTAINMENT_SCHEMA,
        "containment_id": f"JQAR-{time.strftime('%Y%m%d', time.gmtime())}-{uuid.uuid4().hex[:6].upper()}",
        "executed": False,
        "artifacts": [],
        "started_at": _now(),
        "host": socket.gethostname(),
        "pid": os.getpid(),
        # HJOS can contain. It can NEVER certify its own containment.
        "independently_verified": False,
        "verification_authority": "EXTERNAL_REQUIRED",
        "rollback_supported": True,
        **kw,
    }


def _finish(result: Dict[str, Any], ledger_append: Callable[[dict], Any]) -> Dict[str, Any]:
    result["completed_at"] = _now()
    ledger_append(dict(result))
    return result


# --------------------------------------------------------------------- containment
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
    observation_id: Optional[str] = None,
    quarantine_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute containment only when burn-in enabled AND governance authorizes AND
    the reason maps to a charter-permitted class. Otherwise: touch nothing."""
    qclass = permitted_class(reason)
    gov = _governance(repo_root)
    root = Path(repo_root) if repo_root else ROOT

    result = _base_record(
        reason=reason,
        **{"class": qclass},
        subject=subject,
        evidence=list(evidence),
        cycle_id=cycle_id,
        observer=observer,
        observation_id=observation_id,
        execution_authority="NONE",
        governance_policy_id=gov.get("authorizing_policy_id")
        if _valid_policy_id(gov.get("authorizing_policy_id")) else None,
    )

    if not enabled:
        result["blocked"] = "BURN_IN_INCOMPLETE"
        return _finish(result, ledger_append)

    gov_block = _gov_block_reason(gov, kind="class_quarantine")
    if gov_block:
        result["blocked"] = gov_block
        return _finish(result, ledger_append)

    if not qclass:
        result["blocked"] = "CLASS_NOT_PERMITTED"
        return _finish(result, ledger_append)
    if qclass not in HJOS_CHARTER.automatic_quarantine_permitted_only_for:
        result["blocked"] = "CHARTER_DENY"
        return _finish(result, ledger_append)

    lease_dir = root / "coordination" / "leases"

    if qclass == "secret_exposure":
        # Do not delete evidence — flag only + request human rotation.
        flag = root / "coordination" / "jspace" / "SECRET_EXPOSURE_FLAG.json"
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(json.dumps({
            "flagged_at": _now(),
            "cycle_id": cycle_id,
            "subject": subject,
            "evidence": list(evidence),
            "containment_id": result["containment_id"],
            "action_required": "ROTATE_CREDENTIALS_HUMAN",
        }, indent=2) + "\n", encoding="utf-8")
        result["executed"] = True
        result["execution_authority"] = EXECUTION_AUTHORITY
        result["artifacts"] = [{
            "source_path": None,
            "dest_path": _rel(flag, root),
            "kind": "flag_only",
            "sha256_before": None,
            "sha256_after": _sha256(flag),
            "collision": False,
        }]
        result["rollback_supported"] = False  # nothing was moved; nothing to restore
        return _finish(result, ledger_append)

    if qclass in ("evidence_tampering", "destructive_action", "founder_gate_bypass"):
        # Resolve evidence FIRST. A containment that matches nothing must mutate
        # nothing — not even an empty quarantine directory.
        targets: List[Path] = []
        for ev in evidence:
            p = Path(ev)
            if not p.is_absolute():
                p = root / ev
            if p.exists() and p.suffix == ".lock" and p.parent == lease_dir:
                targets.append(p)

        if not targets:
            result["blocked"] = "NO_MATCHING_EVIDENCE"
            result["executed"] = False
            return _finish(result, ledger_append)

        qdir = Path(quarantine_dir) if quarantine_dir else (
            lease_dir / f"_quarantine_hjos_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        )
        artifacts = []
        for p in targets:
            artifacts.append(_capture(p, qdir, root, annotation={
                "schema": "HJOS_QUARANTINE_ANNOTATION_v1",
                "containment_id": result["containment_id"],
                "cycle_id": cycle_id,
                "observer": observer,
                "class": qclass,
                "reason": reason,
                "release_reason": f"HJOS_{qclass.upper()}_QUARANTINE",
                "do_not_retrofit_authority": True,
                "governance_policy_id": result["governance_policy_id"],
            }))
        result["executed"] = True
        result["artifacts"] = artifacts
        result["quarantine_dir"] = _rel(qdir, root)
        result["execution_authority"] = EXECUTION_AUTHORITY
        result["actions"] = [f"moved:{a['original_name']}->{a['dest_path']}" for a in artifacts]
        return _finish(result, ledger_append)

    result["blocked"] = "NO_HANDLER"
    return _finish(result, ledger_append)


# -------------------------------------------------------------------- lease hygiene
def quarantine_expired_orphan_locks(
    *,
    enabled: bool,
    current_instance_id: Optional[str],
    ledger_append,
    repo_root: Optional[Path] = None,
    cycle_id: str = "",
    quarantine_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Hygiene: expire orphan SOAK locks from dead instances after burn-in.

    Not one of the four security classes — recorded separately as lease hygiene.
    A lock is an orphan ONLY when ALL of these hold:
      - STATUS_ACTIVE          : status is ACTIVE/ACQUIRED/RUNNING
      - EXPIRED                : expires_at is in the past
      - INSTANCE_NOT_CURRENT   : it is not the live scheduler instance's lock

    A MISSING scheduler_instance_id is NOT by itself evidence of orphan-hood.
    Absence of an authority id is absence of evidence, not evidence of death.
    """
    root = Path(repo_root) if repo_root else ROOT
    lease_dir = root / "coordination" / "leases"
    gov = _governance(repo_root)

    result = _base_record(
        kind="expired_orphan_lease_hygiene",
        cycle_id=cycle_id,
        observer="jspace_lease_hygiene",
        moved=[],
        skipped=[],
        execution_authority="NONE",
        governance_policy_id=gov.get("authorizing_policy_id")
        if _valid_policy_id(gov.get("authorizing_policy_id")) else None,
    )

    if not enabled:
        result["blocked"] = "BURN_IN_INCOMPLETE"
        return _finish(result, ledger_append)

    gov_block = _gov_block_reason(gov, kind="orphan_hygiene")
    if gov_block:
        result["blocked"] = gov_block
        return _finish(result, ledger_append)

    if not lease_dir.exists():
        result["blocked"] = "NO_LEASE_DIR"
        return _finish(result, ledger_append)

    now = datetime.now(timezone.utc)
    qdir = Path(quarantine_dir) if quarantine_dir else (
        lease_dir / f"_quarantine_hjos_orphans_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
    )
    artifacts: List[Dict[str, Any]] = []
    moved: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    for lock in sorted(lease_dir.glob("*.lock")):
        try:
            rec = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            skipped.append({"lock": lock.name, "reason": "UNREADABLE"})
            continue

        criteria: List[str] = []
        status = str(rec.get("status") or "").upper()
        if status not in ("ACTIVE", "ACQUIRED", "RUNNING"):
            skipped.append({"lock": lock.name, "reason": "NOT_ACTIVE", "status": status})
            continue
        criteria.append("STATUS_ACTIVE")

        try:
            exp = datetime.fromisoformat(str(rec.get("expires_at")).replace("Z", "+00:00"))
        except Exception:
            skipped.append({"lock": lock.name, "reason": "UNPARSEABLE_EXPIRY"})
            continue
        if exp >= now:
            # Not expired. Even with NO authority id, this is not an orphan.
            skipped.append({"lock": lock.name, "reason": "NOT_EXPIRED",
                            "has_instance_id": rec.get("scheduler_instance_id") is not None})
            continue
        criteria.append("EXPIRED")

        inst = rec.get("scheduler_instance_id")
        if current_instance_id and inst == current_instance_id:
            skipped.append({"lock": lock.name, "reason": "CURRENT_LIVE_INSTANCE"})
            continue  # never touch live instance
        criteria.append("INSTANCE_NOT_CURRENT")

        art = _capture(lock, qdir, root, annotation={
            "schema": "HJOS_QUARANTINE_ANNOTATION_v1",
            "containment_id": result["containment_id"],
            "cycle_id": cycle_id,
            "task_id": rec.get("task_id"),
            "lease_id": rec.get("lease_id"),
            "scheduler_instance_id": inst,
            "status_after_release": "RELEASED",
            "released_at": _now(),
            "release_reason": "HJOS_ORPHAN_EXPIRED_QUARANTINE",
            "do_not_retrofit_authority": True,
            "criteria": criteria,
            "governance_policy_id": result["governance_policy_id"],
        })
        art["criteria"] = criteria
        art["task_id"] = rec.get("task_id")
        art["lease_id"] = rec.get("lease_id")
        artifacts.append(art)
        moved.append({"task_id": rec.get("task_id"), "lease_id": rec.get("lease_id"),
                      "from": lock.name, "criteria": criteria})

        hist = lease_dir / "_lease_history.jsonl"
        with hist.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "task_id": rec.get("task_id"),
                "lease_id": rec.get("lease_id"),
                "status": "RELEASED",
                "released_at": _now(),
                "reason": "HJOS_ORPHAN_EXPIRED_QUARANTINE",
                "scheduler_instance_id": inst,
                "cycle_id": cycle_id,
                "containment_id": result["containment_id"],
                "criteria": criteria,
            }) + "\n")

    result["executed"] = bool(artifacts)
    result["artifacts"] = artifacts
    result["moved"] = moved
    result["skipped"] = skipped
    result["quarantine_dir"] = _rel(qdir, root) if artifacts else None
    result["execution_authority"] = EXECUTION_AUTHORITY if artifacts else "NONE"
    return _finish(result, ledger_append)


# ----------------------------------------------------------------- verification ban
def _is_self_actor(actor: str) -> bool:
    a = str(actor or "").strip().lower()
    if not a:
        return True  # an anonymous attestation is not an independent one
    return any(a.startswith(p) for p in _SELF_ACTOR_PREFIXES)


def attest_containment_verification(
    record: Dict[str, Any],
    *,
    actor: str,
    ledger_append: Optional[Callable[[dict], Any]] = None,
    note: str = "",
) -> Dict[str, Any]:
    """Independent verification of a containment.

    HJOS — the swarm that performed the containment — cannot certify it. Any actor
    inside the observer boundary is refused. Verification is an append-only row; it
    never edits the containment record.
    """
    if _is_self_actor(actor):
        raise PermissionError(
            "HJOS_SELF_VERIFICATION_PROHIBITED: the observer that contained cannot "
            f"independently verify its own containment (actor={actor!r})"
        )
    if str(actor).strip().lower() == str(record.get("observer") or "").strip().lower():
        raise PermissionError(
            "HJOS_SELF_VERIFICATION_PROHIBITED: acting observer cannot verify itself"
        )
    row = {
        "schema": VERIFICATION_SCHEMA,
        "containment_id": record.get("containment_id"),
        "cycle_id": record.get("cycle_id"),
        "observer": record.get("observer"),
        "independently_verified": True,
        "verified_by": actor,
        "verified_at": _now(),
        "note": note,
        "artifacts_verified": [a.get("dest_path") for a in (record.get("artifacts") or [])],
    }
    if ledger_append:
        ledger_append(dict(row))
    return row


# --------------------------------------------------------------------------- rollback
def rollback_containment(
    *,
    record: Dict[str, Any],
    repo_root: Optional[Path] = None,
    actor: str,
    ledger_append: Optional[Callable[[dict], Any]] = None,
) -> Dict[str, Any]:
    """Restore every quarantined artifact to its EXACT original path with its EXACT
    original bytes. If the quarantined bytes no longer match the recorded digest,
    refuse — restoring evidence we cannot vouch for is worse than not restoring."""
    root = Path(repo_root) if repo_root else ROOT
    out: Dict[str, Any] = {
        "schema": ROLLBACK_SCHEMA,
        "containment_id": record.get("containment_id"),
        "cycle_id": record.get("cycle_id"),
        "actor": actor,
        "rolled_back": False,
        "artifacts": [],
        "started_at": _now(),
    }
    arts = [a for a in (record.get("artifacts") or []) if a.get("source_path")]
    if not arts:
        out["blocked"] = "NOTHING_TO_ROLL_BACK"
        out["completed_at"] = _now()
        if ledger_append:
            ledger_append(dict(out))
        return out

    # Verify EVERY artifact before restoring ANY (all-or-nothing).
    planned = []
    for a in arts:
        dest = root / a["dest_path"]
        src = root / a["source_path"]
        if not dest.exists():
            out["blocked"] = "ARTIFACT_MISSING"
            out["detail"] = a["dest_path"]
            out["completed_at"] = _now()
            if ledger_append:
                ledger_append(dict(out))
            return out
        actual = _sha256(dest)
        if actual != a.get("sha256_before"):
            out["blocked"] = "ARTIFACT_DIGEST_MISMATCH"
            out["detail"] = {"artifact": a["dest_path"],
                             "expected": a.get("sha256_before"), "actual": actual}
            out["completed_at"] = _now()
            if ledger_append:
                ledger_append(dict(out))
            return out
        if src.exists():
            out["blocked"] = "SOURCE_PATH_OCCUPIED"
            out["detail"] = a["source_path"]
            out["completed_at"] = _now()
            if ledger_append:
                ledger_append(dict(out))
            return out
        planned.append((a, src, dest, actual))

    restored = []
    for a, src, dest, digest in planned:
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest), str(src))
        after = _sha256(src)
        side = Path(str(dest) + ".hjos.json")
        if side.exists():
            side.unlink()
        restored.append({
            "restored_to": a["source_path"],
            "from": a["dest_path"],
            "sha256_before": a.get("sha256_before"),
            "sha256_after": after,
            "sha256_verified": after == a.get("sha256_before") == digest,
        })
    out["rolled_back"] = all(r["sha256_verified"] for r in restored)
    out["artifacts"] = restored
    out["completed_at"] = _now()
    if ledger_append:
        ledger_append(dict(out))
    return out
