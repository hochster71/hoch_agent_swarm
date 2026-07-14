"""ONE canonical runtime evidence source. The API must not invent its own scheduler context.

Previously the API instantiated a PersistentScheduler pointed at coordination/council while
the live daemon wrote to its own soak evidence dir. The API then reported
`observed_peak: UNKNOWN` -- which was *honest* but *wrong-headed*: it wasn't unknown, it was
looking at the wrong ledger. A divergence between the daemon's ledger and the API's ledger is
not an absence of truth, it is a SOURCE MISMATCH, and it must say so.

Negative controls (F-A1):
  missing declared ledger path          → RUNTIME_SOURCE_UNPUBLISHED
  declared path exists but instance ID differs → RUNTIME_SOURCE_MISMATCH
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
LEASE_DIR = ROOT / "coordination" / "leases"
POINTER = ROOT / "coordination" / "council" / "active_runtime_source.json"
INSTANCE_SIDECAR_NAME = "scheduler_instance.json"

UNKNOWN = "UNKNOWN"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def publish(evidence_dir: Path, instance_id: str) -> None:
    """The DAEMON declares which ledger is canonical. Written at scheduler start."""
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    ledger = evidence_dir / "task_lease_ledger.jsonl"
    # Ensure the declared ledger path exists (even if empty) so API does not
    # immediately report UNPUBLISHED for a freshly started daemon.
    if not ledger.exists():
        ledger.touch()
    sidecar = evidence_dir / INSTANCE_SIDECAR_NAME
    sidecar.write_text(json.dumps({
        "scheduler_instance_id": instance_id,
        "ledger_path": str(ledger),
        "evidence_dir": str(evidence_dir),
        "pid": os.getpid(),
        "published_at": _now(),
    }, indent=2) + "\n", encoding="utf-8")
    POINTER.parent.mkdir(parents=True, exist_ok=True)
    POINTER.write_text(json.dumps({
        "scheduler_instance_id": instance_id,
        "ledger_path": str(ledger),
        "evidence_dir": str(evidence_dir),
        "instance_sidecar": str(sidecar),
        "pid": os.getpid(),
        "published_at": _now(),
    }, indent=2) + "\n", encoding="utf-8")


def _digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else UNKNOWN


def _read_sidecar_instance(evidence_dir: Optional[Path], ledger: Path) -> Optional[str]:
    """Authoritative instance id recorded beside the ledger by publish()."""
    candidates = []
    if evidence_dir is not None:
        candidates.append(Path(evidence_dir) / INSTANCE_SIDECAR_NAME)
    candidates.append(ledger.parent / INSTANCE_SIDECAR_NAME)
    for c in candidates:
        if not c.exists():
            continue
        try:
            d = json.loads(c.read_text(encoding="utf-8"))
            sid = d.get("scheduler_instance_id")
            if sid:
                return str(sid)
        except Exception:
            continue
    return None


def _peak_from(ledger: Path):
    """Peak from AUTHORITATIVE lease intervals, paired by lease_id.

    A release at time T does NOT overlap an acquire at T (sort release before
    acquire on equal timestamps — never round in the flattering direction).
    """
    if not ledger.exists():
        return UNKNOWN
    opened, closed, last = {}, {}, ""
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        lid, st, ts = e.get("lease_id"), e.get("status"), e.get("ts")
        if not lid or not ts:
            continue
        last = max(last, ts)
        if st == "ACQUIRED":
            opened.setdefault(lid, ts)
        elif st in ("RELEASED", "COMPLETED", "FAILED"):
            closed.setdefault(lid, ts)
    if not opened:
        return UNKNOWN
    # +1 acquire, -1 release; on same timestamp process releases first (-1 before +1)
    ev = []
    for lid, a in opened.items():
        ev.append((a, +1, 1))          # tie-break: acquire after release
        rel = closed.get(lid, last)
        ev.append((rel, -1, 0))
    ev.sort(key=lambda x: (x[0], x[2], x[1]))
    cur = peak = 0
    for _, d, _ in ev:
        cur += d
        if cur < 0:
            cur = 0
        peak = max(peak, cur)
    return peak if peak > 0 else UNKNOWN


def classify_active_leases() -> dict[str, Any]:
    """`currently_active: 5` against capacity 4 must be EXPLAINED, never normalised away.

    Worker leases (real dispatched tasks) are counted against capacity. Recovery / injection /
    administrative leases are NOT worker slots. If the WORKER count alone exceeds capacity,
    that is a genuine capacity violation and we say so.
    """
    if not LEASE_DIR.exists():
        return {"total_active_records": 0, "worker_leases_active": 0,
                "recovery_or_injection_leases": 0, "expired_but_present": 0,
                "leases": []}

    worker = recovery = expired = 0
    detail = []
    now = time.time()
    for lock in LEASE_DIR.glob("*.lock"):
        try:
            d = json.loads(lock.read_text(encoding="utf-8"))
        except Exception:
            recovery += 1
            detail.append({"lease": lock.name, "class": "MALFORMED"})
            continue
        tid = str(d.get("task_id", ""))
        is_expired = False
        try:
            exp = d.get("expires_at", "")
            is_expired = bool(exp) and time.mktime(time.strptime(
                exp.split(".")[0].replace("Z", ""), "%Y-%m-%dT%H:%M:%S")) <= now
        except Exception:
            is_expired = False
        admin = any(k in tid.upper() for k in
                    ("KILLED-WORKER", "CORRUPT", "TOKREG", "DUP", "TIMEOUT", "MUT", "EXP"))
        if is_expired:
            expired += 1
            detail.append({"lease": tid, "class": "STALE_REQUIRES_RECOVERY",
                           "counts_toward_worker_concurrency": False})
        elif admin:
            recovery += 1
            detail.append({"lease": tid, "class": "RECOVERY_OR_INJECTION"})
        else:
            worker += 1
            detail.append({"lease": tid, "class": "WORKER",
                           "authority_decision_id": d.get("authority_decision_id"),
                           "status": d.get("status"),
                           "task_id": tid})
    return {"total_active_records": worker + recovery + expired,
            "worker_leases_active": worker,
            "recovery_or_injection_leases": recovery,
            "expired_but_present": expired,
            "leases": detail}


def concurrency_truth(configured_capacity: int = 4) -> dict[str, Any]:
    """The single canonical concurrency fact set for API + UI + daemon.

    F-A1 semantics:
      * no pointer                        → RUNTIME_SOURCE_UNPUBLISHED
      * declared ledger path missing      → RUNTIME_SOURCE_UNPUBLISHED
      * ledger exists, instance ID differs → RUNTIME_SOURCE_MISMATCH
      * otherwise                         → OBSERVED_RUNTIME
    """
    base = {
        "configured_capacity": configured_capacity,
        "observed_peak": UNKNOWN,
        "lease_mode": "PER_TASK",
        "observed_at": _now(),
    }

    if not POINTER.exists():
        return {**base,
                "truth_source": "RUNTIME_SOURCE_UNPUBLISHED",
                "status": "UNPUBLISHED",
                "reason": "no daemon has declared a canonical ledger",
                "observed_peak": UNKNOWN}

    try:
        ptr = json.loads(POINTER.read_text(encoding="utf-8"))
    except Exception as e:
        return {**base,
                "truth_source": "RUNTIME_SOURCE_UNPUBLISHED",
                "status": "UNPUBLISHED",
                "reason": f"pointer unreadable: {type(e).__name__}"}

    ledger = Path(str(ptr.get("ledger_path") or ""))
    evidence_dir = Path(str(ptr.get("evidence_dir") or ledger.parent)) if ptr.get("evidence_dir") or ledger.name else None
    declared_id = str(ptr.get("scheduler_instance_id") or UNKNOWN)

    if not ledger or str(ledger) in (".", "") or not ledger.exists():
        return {**base,
                "truth_source": "RUNTIME_SOURCE_UNPUBLISHED",
                "status": "UNPUBLISHED",
                "reason": "declared ledger path does not exist",
                "scheduler_instance_id": declared_id,
                "ledger_path": str(ledger) if ledger else UNKNOWN,
                "mismatch": "RUNTIME_SOURCE_UNPUBLISHED: declared ledger does not exist"}

    sidecar_id = _read_sidecar_instance(evidence_dir, ledger)
    if sidecar_id is not None and declared_id != UNKNOWN and sidecar_id != declared_id:
        return {**base,
                "truth_source": "RUNTIME_SOURCE_MISMATCH",
                "status": "MISMATCH",
                "reason": "declared scheduler_instance_id differs from ledger sidecar",
                "scheduler_instance_id": declared_id,
                "ledger_instance_id": sidecar_id,
                "ledger_path": str(ledger),
                "ledger_digest": _digest(ledger),
                "mismatch": "RUNTIME_SOURCE_MISMATCH: scheduler ID differs"}

    # Sidecar missing after a ledger exists: still a mismatch (cannot verify binding)
    if sidecar_id is None and declared_id != UNKNOWN:
        # Soft: if sidecar missing but pointer digest-consistent, report MISMATCH for verifyability
        # User negative control is specifically "exists but ID differs". Missing sidecar is
        # incomplete binding — treat as MISMATCH so it stays visible.
        return {**base,
                "truth_source": "RUNTIME_SOURCE_MISMATCH",
                "status": "MISMATCH",
                "reason": "ledger exists but scheduler_instance sidecar is absent; cannot verify binding",
                "scheduler_instance_id": declared_id,
                "ledger_instance_id": UNKNOWN,
                "ledger_path": str(ledger),
                "ledger_digest": _digest(ledger),
                "mismatch": "RUNTIME_SOURCE_MISMATCH: instance sidecar missing"}

    leases = classify_active_leases()
    peak = _peak_from(ledger)
    worker_active = leases["worker_leases_active"]
    violation = isinstance(worker_active, int) and worker_active > configured_capacity

    out = {
        "configured_capacity": configured_capacity,
        "worker_leases_active": worker_active,
        "recovery_or_injection_leases": leases["recovery_or_injection_leases"],
        "expired_but_present": leases["expired_but_present"],
        "total_active_records": leases["total_active_records"],
        "capacity_violation": violation,
        "observed_peak": peak,
        "lease_mode": "PER_TASK",
        "scheduler_instance_id": declared_id,
        "ledger_instance_id": sidecar_id or declared_id,
        "ledger_path": str(ledger),
        "ledger_digest": _digest(ledger),
        "api_reads_same_ledger": True,
        "truth_source": "OBSERVED_RUNTIME (canonical daemon ledger)",
        "status": ("DEGRADED" if violation else
                   "OK" if isinstance(peak, int) and peak >= 2 else "UNPROVEN"),
        "observed_at": _now(),
        "lease_detail": leases.get("leases", []),
    }
    return out
