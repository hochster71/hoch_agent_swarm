"""H1C Controlled Live-Proof Activation — fail-closed truth engine.

Builds the governed transition from ELIGIBLE + EXECUTION_BLOCKED toward
AUTHORIZED_FOR_CONTROLLED_EXECUTION without inventing founder approval.

Does not reopen H1B. Does not perform founder-only actions.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]

# --- State machine (H1C) ----------------------------------------------------
H1C_STATES = (
    "ELIGIBLE_BLOCKED",
    "LIVE_PROOF_MISSING",
    "LIVE_PROOF_STALE",
    "LIVE_PROOF_INVALID",
    "OPERATOR_HOLD_ACTIVE",
    "OPERATOR_RELEASE_PENDING",
    "AUTHORIZED_FOR_CONTROLLED_EXECUTION",
    "EXECUTION_ACTIVE",
    "EXECUTION_COMPLETE",
    "EXECUTION_FAILED",
    "AUTHORIZATION_REVOKED",
    "UNKNOWN",
    "ERROR",
)

DEFAULT_HOLD_PATH = ROOT / "has_live_project_tracker" / "data" / "ag_operator_hold.json"
DEFAULT_COUNCIL_DIR = ROOT / "coordination" / "council"
DEFAULT_LEDGER_DIR = ROOT / "coordination" / "council" / "h1c_ledgers"
DEFAULT_RELEASE_LEDGER = DEFAULT_LEDGER_DIR / "operator_hold_release_ledger.jsonl"
DEFAULT_EXEC_LEDGER = DEFAULT_LEDGER_DIR / "controlled_execution_ledger.jsonl"
DEFAULT_LIVE_PROOF_PATH = DEFAULT_COUNCIL_DIR / "h1c_live_proof.json"
DEFAULT_EXEC_STATE_PATH = DEFAULT_COUNCIL_DIR / "h1c_execution_state.json"

# Ineligible live-proof source types
INELIGIBLE_SOURCE_TYPES = frozenset(
    {
        "test",
        "fixture",
        "synthetic",
        "template",
        "mock",
        "dry_run_fixture",
        "non_runtime",
        "NON_RUNTIME_TEST_EVIDENCE",
    }
)

SUCCESS_FORBIDDEN = frozenset(
    {"GO", "AUTHORIZED", "READY", "CONFIRMED_LIVE", "YES", "PASS_EXECUTE"}
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat().replace("+00:00", "Z")


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        s = ts.strip().rstrip("Z")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _sha256_file(path: Path) -> Optional[str]:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def git_sha(cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(cwd or ROOT),
            text=True,
            timeout=5,
        ).strip()
    except Exception:
        return "UNKNOWN"


# --- Live proof contract ----------------------------------------------------

REQUIRED_LIVE_PROOF_FIELDS = (
    "proof_id",
    "candidate_id",
    "package_id",
    "package_digest",
    "execution_scope",
    "issued_at",
    "observed_at",
    "expires_at",
    "source_type",
    "source_identity",
    "environment",
    "status",
    "evidence_paths",
    "evidence_digests",
    "mock",
)


@dataclass
class LiveProofResult:
    status: str  # MISSING | INVALID | STALE | EXPIRED | INELIGIBLE | PASS
    proof_id: Optional[str] = None
    candidate_id: Optional[str] = None
    package_id: Optional[str] = None
    package_digest: Optional[str] = None
    fresh: bool = False
    age_seconds: Optional[float] = None
    expires_at: Optional[str] = None
    source_eligible: bool = False
    execution_scope: list = field(default_factory=list)
    blockers: list = field(default_factory=list)
    raw: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d


def validate_live_proof(
    proof: Optional[dict],
    *,
    expected_candidate_id: Optional[str] = None,
    expected_package_id: Optional[str] = None,
    expected_package_digest: Optional[str] = None,
    allowed_scope: Optional[list] = None,
    max_age_seconds: float = 300.0,
    now: Optional[datetime] = None,
    repo_root: Path | None = None,
) -> LiveProofResult:
    """Fail-closed live-proof validation (H1C)."""
    now = now or _now()
    root = repo_root or ROOT
    out = LiveProofResult(status="MISSING", blockers=[])

    if proof is None:
        out.blockers.append("LIVE_PROOF_MISSING")
        return out
    if not isinstance(proof, dict):
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_NOT_OBJECT")
        return out

    out.raw = proof
    missing = [f for f in REQUIRED_LIVE_PROOF_FIELDS if f not in proof]
    if missing:
        out.status = "INVALID"
        out.blockers.append(f"LIVE_PROOF_MISSING_FIELDS:{','.join(missing)}")
        return out

    out.proof_id = str(proof.get("proof_id") or "") or None
    out.candidate_id = str(proof.get("candidate_id") or "") or None
    out.package_id = str(proof.get("package_id") or "") or None
    out.package_digest = str(proof.get("package_digest") or "") or None
    out.expires_at = proof.get("expires_at")
    scope = proof.get("execution_scope")
    out.execution_scope = list(scope) if isinstance(scope, list) else []

    if proof.get("mock") is True:
        out.status = "INELIGIBLE"
        out.blockers.append("LIVE_PROOF_MOCK_TRUE")
        return out

    source_type = str(proof.get("source_type") or "").strip().lower()
    if not source_type or source_type in {s.lower() for s in INELIGIBLE_SOURCE_TYPES}:
        out.status = "INELIGIBLE"
        out.blockers.append(f"LIVE_PROOF_SOURCE_INELIGIBLE:{source_type or 'EMPTY'}")
        return out

    status = str(proof.get("status") or "").upper()
    if status in ("DENIED", "REVOKED", "SUPERSEDED", "FAILED", "INVALID"):
        out.status = "INELIGIBLE"
        out.blockers.append(f"LIVE_PROOF_STATUS_{status}")
        return out

    issued = _parse_iso(proof.get("issued_at"))
    observed = _parse_iso(proof.get("observed_at"))
    expires = _parse_iso(proof.get("expires_at"))
    if issued is None or observed is None or expires is None:
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_TIMESTAMP_MALFORMED")
        return out

    age = (now - observed).total_seconds()
    out.age_seconds = round(age, 3)
    if age < -300:
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_OBSERVED_IN_FUTURE")
        return out
    if age > max_age_seconds:
        out.status = "STALE"
        out.fresh = False
        out.blockers.append(f"LIVE_PROOF_STALE_AGE_{int(age)}s")
        return out
    if now > expires:
        out.status = "EXPIRED"
        out.fresh = False
        out.blockers.append("LIVE_PROOF_EXPIRED")
        return out

    if expected_candidate_id and out.candidate_id != expected_candidate_id:
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_CANDIDATE_MISMATCH")
        return out
    if expected_package_id and out.package_id != expected_package_id:
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_PACKAGE_MISMATCH")
        return out
    if expected_package_digest and out.package_digest != expected_package_digest:
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_DIGEST_MISMATCH")
        return out

    digests = proof.get("evidence_digests") or {}
    paths = proof.get("evidence_paths") or []
    if not isinstance(digests, dict) or not isinstance(paths, list):
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_EVIDENCE_SCHEMA_INVALID")
        return out
    if not paths:
        out.status = "INVALID"
        out.blockers.append("LIVE_PROOF_EVIDENCE_PATHS_EMPTY")
        return out

    for rel in paths:
        ep = Path(rel)
        if not ep.is_absolute():
            ep = root / rel
        if not ep.exists():
            out.status = "INVALID"
            out.blockers.append(f"LIVE_PROOF_EVIDENCE_MISSING:{rel}")
            return out
        expected = digests.get(str(rel)) or digests.get(Path(rel).name)
        actual = _sha256_file(ep)
        if expected and actual and expected != actual:
            out.status = "INVALID"
            out.blockers.append(f"LIVE_PROOF_EVIDENCE_DIGEST_MISMATCH:{rel}")
            return out
        if expected and not actual:
            out.status = "INVALID"
            out.blockers.append(f"LIVE_PROOF_EVIDENCE_UNREADABLE:{rel}")
            return out

    if allowed_scope is not None:
        allowed = set(allowed_scope)
        requested = set(out.execution_scope)
        if not requested.issubset(allowed):
            out.status = "INELIGIBLE"
            out.blockers.append("LIVE_PROOF_SCOPE_EXCEEDS_AUTHORIZATION")
            return out

    out.status = "PASS"
    out.fresh = True
    out.source_eligible = True
    return out


def load_live_proof(path: Path) -> tuple[Optional[dict], list[str]]:
    if not path.exists():
        return None, ["LIVE_PROOF_FILE_MISSING"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None, ["LIVE_PROOF_NOT_OBJECT"]
        return data, []
    except json.JSONDecodeError as e:
        return None, [f"LIVE_PROOF_MALFORMED_JSON:{e}"]
    except Exception as e:
        return None, [f"LIVE_PROOF_READ_ERROR:{type(e).__name__}"]


# --- Operator hold lifecycle ------------------------------------------------

HOLD_STATES = (
    "HOLD_ACTIVE",
    "RELEASE_REQUESTED",
    "RELEASE_VALIDATED",
    "CONTROLLED_EXECUTION_AUTHORIZED",
    "RELOCKED_AFTER_COMPLETION_OR_FAILURE",
)

# Only these actor identities may validate a release (system/test harness; not founder).
# Founder approval remains separate and is never auto-granted here.
ALLOWED_RELEASE_ACTORS = frozenset(
    {
        "helm.h1c.hold_lifecycle",
        "helm.h1c.test_harness",
        "system.controlled_activation",
    }
)


@dataclass
class HoldView:
    status: str
    reason: str
    since: Optional[str]
    release_eligible: bool
    active: bool
    blockers: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def read_operator_hold(path: Path) -> HoldView:
    """Fail-closed: missing/unreadable hold file => HOLD active."""
    if not path.exists():
        return HoldView(
            status="HOLD_ACTIVE",
            reason="hold file missing (fail-closed)",
            since=None,
            release_eligible=False,
            active=True,
            blockers=["OPERATOR_HOLD_FILE_MISSING"],
        )
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return HoldView(
            status="HOLD_ACTIVE",
            reason=f"hold unreadable:{type(e).__name__}",
            since=None,
            release_eligible=False,
            active=True,
            blockers=["OPERATOR_HOLD_UNREADABLE"],
        )

    active = True
    if doc.get("operator_hold_active") is False:
        active = False
    if str(doc.get("operator_hold") or "").upper() == "CLEAR":
        active = False

    # Manual file clear alone is insufficient for H1C controlled execution —
    # release_eligible only when a validated ledgered release exists (checked later).
    return HoldView(
        status="HOLD_ACTIVE" if active else "HOLD_CLEARED_FILE_ONLY",
        reason=str(doc.get("reason") or "operator hold"),
        since=doc.get("timestamp") or doc.get("since"),
        release_eligible=False,
        active=active,
        blockers=["OPERATOR_HOLD_ACTIVE"] if active else ["HOLD_CLEARED_WITHOUT_LEDGER_RELEASE"],
    )


def validate_release_event(
    event: Optional[dict],
    *,
    expected_candidate_id: Optional[str],
    expected_package_digest: Optional[str],
    max_age_seconds: float = 3600.0,
    now: Optional[datetime] = None,
) -> tuple[bool, list[str]]:
    now = now or _now()
    blockers: list[str] = []
    if not event or not isinstance(event, dict):
        return False, ["RELEASE_EVENT_MISSING"]

    required = (
        "event_id",
        "actor_identity",
        "candidate_id",
        "package_digest",
        "authorized_execution_scope",
        "reason",
        "timestamp",
        "expiry",
        "previous_state_digest",
        "resulting_state_digest",
        "ledger_reference",
    )
    for f in required:
        if f not in event or event.get(f) in (None, "", []):
            blockers.append(f"RELEASE_EVENT_MISSING_FIELD:{f}")
    if blockers:
        return False, blockers

    actor = str(event.get("actor_identity") or "")
    if actor not in ALLOWED_RELEASE_ACTORS:
        blockers.append(f"RELEASE_EVENT_WRONG_ACTOR:{actor}")

    if expected_candidate_id and event.get("candidate_id") != expected_candidate_id:
        blockers.append("RELEASE_EVENT_CANDIDATE_MISMATCH")
    if expected_package_digest and event.get("package_digest") != expected_package_digest:
        blockers.append("RELEASE_EVENT_DIGEST_MISMATCH")

    ts = _parse_iso(event.get("timestamp"))
    exp = _parse_iso(event.get("expiry"))
    if ts is None or exp is None:
        blockers.append("RELEASE_EVENT_TIMESTAMP_MALFORMED")
    else:
        age = (now - ts).total_seconds()
        if age > max_age_seconds:
            blockers.append("RELEASE_EVENT_STALE")
        if now > exp:
            blockers.append("RELEASE_EVENT_EXPIRED")
        if age < -300:
            blockers.append("RELEASE_EVENT_FUTURE_TIMESTAMP")

    if str(event.get("status") or "").upper() in ("REVOKED", "DENIED", "SUPERSEDED"):
        blockers.append(f"RELEASE_EVENT_STATUS_{str(event.get('status')).upper()}")

    return len(blockers) == 0, blockers


def append_ledger(path: Path, entry: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, sort_keys=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return _sha256_json(entry)


def load_latest_release(
    ledger_path: Path,
    *,
    candidate_id: Optional[str] = None,
    package_digest: Optional[str] = None,
) -> Optional[dict]:
    if not ledger_path.exists():
        return None
    latest = None
    try:
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if candidate_id and rec.get("candidate_id") != candidate_id:
                continue
            if package_digest and rec.get("package_digest") != package_digest:
                continue
            if rec.get("event_type") == "OPERATOR_HOLD_RELEASE":
                latest = rec
    except Exception:
        return None
    return latest


# --- Controlled execution (local dry-run only) ------------------------------

ALLOWED_DRY_RUN_SCOPE = frozenset(
    {
        "local_read_only_probe",
        "local_ledger_write",
        "local_evidence_emit",
        "h1c_controlled_dry_run",
    }
)


def run_controlled_dry_run(
    *,
    authorization_binding: dict,
    execution_scope: list[str],
    evidence_dir: Path,
    exec_ledger: Path,
    exec_state_path: Path,
) -> dict:
    """Non-destructive local-only mission. Never external dispatch."""
    scope = set(execution_scope or [])
    if not scope.issubset(ALLOWED_DRY_RUN_SCOPE):
        return {
            "status": "FAILED",
            "reason": "SCOPE_NOT_LOCAL_ONLY",
            "blockers": [f"SCOPE_FORBIDDEN:{s}" for s in sorted(scope - ALLOWED_DRY_RUN_SCOPE)],
        }

    mission_id = f"H1C-DRY-{uuid.uuid4().hex[:12].upper()}"
    started = _now_iso()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    result_path = evidence_dir / f"{mission_id}_result.json"
    payload = {
        "mission_id": mission_id,
        "kind": "CONTROLLED_LOCAL_DRY_RUN",
        "not_production_execution": True,
        "authorization_binding": authorization_binding,
        "execution_scope": list(execution_scope),
        "started_at": started,
        "tasks": [
            {
                "task_id": f"{mission_id}-T1",
                "agent": "helm.h1c.dry_run_agent",
                "action": "local_read_only_probe",
                "status": "COMPLETE",
            }
        ],
        "external_dispatch": False,
        "money_movement": False,
        "key_provisioning": False,
        "store_submission": False,
    }
    completed = _now_iso()
    payload["completed_at"] = completed
    payload["status"] = "COMPLETE"
    payload["output_digest"] = _sha256_json(payload)
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Relock execution state
    relock = {
        "status": "RELOCKED_AFTER_COMPLETION_OR_FAILURE",
        "mission_id": mission_id,
        "relocked_at": _now_iso(),
        "safe_to_execute": "NO",
        "promotion": "LOCKED",
        "reason": "controlled dry-run completed; gate relocked",
    }
    exec_state_path.parent.mkdir(parents=True, exist_ok=True)
    exec_state_path.write_text(json.dumps(relock, indent=2) + "\n", encoding="utf-8")
    append_ledger(
        exec_ledger,
        {
            "event_type": "CONTROLLED_EXECUTION_COMPLETE_RELOCK",
            "mission_id": mission_id,
            "timestamp": _now_iso(),
            "result_path": str(result_path),
            "output_digest": payload["output_digest"],
        },
    )
    payload["relock"] = relock
    payload["evidence_path"] = str(result_path)
    return payload


# --- Truth composition ------------------------------------------------------

def compute_h1c_truth(
    *,
    repo_root: Path | None = None,
    council_dir: Path | None = None,
    hold_path: Path | None = None,
    live_proof_path: Path | None = None,
    release_ledger: Path | None = None,
    exec_state_path: Path | None = None,
    founder_decision: Optional[dict] = None,
    now: Optional[datetime] = None,
) -> dict:
    """Compose normalized H1C runtime truth. Fail closed. Never invent GO."""
    root = repo_root or ROOT
    cdir = council_dir or (
        Path(os.environ["HELM_COUNCIL_DIR"])
        if os.environ.get("HELM_COUNCIL_DIR")
        else DEFAULT_COUNCIL_DIR
    )
    if hold_path is None:
        # Sandbox tests place hold under HELM_COUNCIL_DIR; production uses tracker path.
        sand_hold = cdir / "ag_operator_hold.json"
        hold_path = sand_hold if os.environ.get("HELM_COUNCIL_DIR") else DEFAULT_HOLD_PATH
    live_proof_path = live_proof_path or (cdir / "h1c_live_proof.json")
    release_ledger = release_ledger or (
        cdir / "h1c_ledgers" / "operator_hold_release_ledger.jsonl"
    )
    exec_state_path = exec_state_path or (cdir / "h1c_execution_state.json")
    now = now or _now()
    truth_updated_at = now.isoformat().replace("+00:00", "Z")
    blockers: list[str] = []
    overall = "ELIGIBLE_BLOCKED"

    # Candidate / package from registry reconciliation (H1B, unchanged contract)
    candidate_id = None
    package_id = None
    package_digest = None
    package_readiness = "UNKNOWN"
    try:
        import sys

        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        if str(root / "scripts") not in sys.path:
            sys.path.insert(0, str(root / "scripts"))
        import scripts.council.h1b_candidate_registry as h1b_reg

        if os.environ.get("HELM_COUNCIL_DIR"):
            h1b_reg.PACKAGES_DIR = cdir / "live_proof_packages"
        recon = h1b_reg.reconcile_candidates()
        if recon.get("status") == "RECONCILED" and recon.get("active_candidate"):
            ac = recon["active_candidate"]
            package_id = ac if isinstance(ac, str) else ac.get("package_id")
            candidate_id = package_id
            integ = recon.get("integrity") or {}
            package_digest = integ.get("combined_authorization_sha256") or integ.get(
                "package_digest"
            )
            if not package_digest and package_id:
                digests = cdir / "live_proof_packages" / package_id / "request_digests.json"
                if digests.exists():
                    try:
                        package_digest = json.loads(digests.read_text()).get(
                            "combined_authorization_sha256"
                        )
                    except Exception:
                        pass
            if integ.get("integrity_status") == "PASS" or package_digest:
                package_readiness = "PASS"
            else:
                package_readiness = "FAIL"
                blockers.append("PACKAGE_INTEGRITY_NOT_PASS")
        else:
            package_readiness = "FAIL"
            blockers.append(f"REGISTRY:{recon.get('status') or recon.get('reason') or 'UNRECONCILED'}")
    except Exception as e:
        blockers.append(f"REGISTRY_EXCEPTION:{type(e).__name__}")
        overall = "ERROR"

    # Founder authorization — never auto-grant
    authorization_status = "UNKNOWN"
    auth_scope: list[str] = []
    decision_path = cdir / "h1b_founder_decision.json"
    try:
        if founder_decision is not None:
            decision = founder_decision
        elif decision_path.exists():
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
        else:
            decision = None
        if decision is None:
            authorization_status = "NOT_GRANTED"
            blockers.append("FOUNDER_AUTHORIZATION_ABSENT")
        else:
            authorization_status = str(
                decision.get("authorization_status") or decision.get("status") or "UNKNOWN"
            ).upper()
            if authorization_status in ("REVOKED", "DENIED", "SUPERSEDED", "EXPIRED"):
                blockers.append(f"FOUNDER_AUTH_{authorization_status}")
            elif authorization_status not in ("GRANTED", "CONSUMED"):
                blockers.append(f"FOUNDER_AUTH_NOT_GRANTED:{authorization_status}")
            # Bind to package if present
            if package_id and decision.get("package_id") and decision.get("package_id") != package_id:
                blockers.append("FOUNDER_AUTH_PACKAGE_MISMATCH")
                authorization_status = "MISMATCH"
            auth_scope = list(
                decision.get("authorized_execution_scope")
                or decision.get("execution_scope")
                or []
            )
            # Controlled dry-run scope only unless founder lists more
            if not auth_scope and authorization_status in ("GRANTED", "CONSUMED"):
                auth_scope = ["h1c_controlled_dry_run", "local_read_only_probe"]
    except Exception as e:
        authorization_status = "ERROR"
        blockers.append(f"FOUNDER_AUTH_READ_ERROR:{type(e).__name__}")

    # Operator hold
    hold = read_operator_hold(hold_path)
    if hold.active:
        blockers.extend(hold.blockers)
        overall = "OPERATOR_HOLD_ACTIVE"
    else:
        # File cleared without ledger release is still a blocker for controlled auth
        if "HOLD_CLEARED_WITHOUT_LEDGER_RELEASE" in hold.blockers:
            blockers.append("HOLD_CLEARED_WITHOUT_LEDGER_RELEASE")

    release = load_latest_release(
        release_ledger, candidate_id=candidate_id, package_digest=package_digest
    )
    release_ok, release_blockers = validate_release_event(
        release,
        expected_candidate_id=candidate_id,
        expected_package_digest=package_digest,
        now=now,
    )
    if hold.active:
        hold.release_eligible = False
    elif release_ok:
        hold.status = "RELEASE_VALIDATED"
        hold.release_eligible = True
        # Remove the file-only clear blocker if ledger release is valid
        blockers = [b for b in blockers if b != "HOLD_CLEARED_WITHOUT_LEDGER_RELEASE"]
    else:
        if not hold.active:
            blockers.extend(release_blockers or ["RELEASE_EVENT_MISSING"])
        hold.release_eligible = False

    # Live proof
    proof_doc, load_blockers = load_live_proof(live_proof_path)
    if load_blockers and proof_doc is None:
        live = LiveProofResult(status="MISSING", blockers=list(load_blockers))
    else:
        live = validate_live_proof(
            proof_doc,
            expected_candidate_id=candidate_id,
            expected_package_id=package_id,
            expected_package_digest=package_digest,
            allowed_scope=auth_scope or list(ALLOWED_DRY_RUN_SCOPE),
            now=now,
            repo_root=root,
        )
    if live.status != "PASS":
        blockers.extend(live.blockers)
        if live.status == "MISSING":
            overall = "LIVE_PROOF_MISSING"
        elif live.status == "STALE":
            overall = "LIVE_PROOF_STALE"
        elif live.status in ("INVALID", "EXPIRED"):
            overall = "LIVE_PROOF_INVALID"
        elif live.status == "INELIGIBLE":
            overall = "LIVE_PROOF_INVALID"

    # Execution state (relock after mission)
    exec_state = {}
    if exec_state_path.exists():
        try:
            exec_state = json.loads(exec_state_path.read_text(encoding="utf-8"))
        except Exception:
            blockers.append("EXEC_STATE_UNREADABLE")
            overall = "ERROR"

    if str(exec_state.get("status") or "") == "EXECUTION_ACTIVE":
        overall = "EXECUTION_ACTIVE"
    elif str(exec_state.get("status") or "") == "RELOCKED_AFTER_COMPLETION_OR_FAILURE":
        if exec_state.get("last_result") == "FAILED":
            overall = "EXECUTION_FAILED"
        else:
            overall = "EXECUTION_COMPLETE"

    # Authorization decision for controlled execution
    promotion = "LOCKED"
    safe_to_execute = "NO"
    execution_scope: list[str] = []

    can_authorize = (
        package_readiness == "PASS"
        and authorization_status in ("GRANTED", "CONSUMED")
        and live.status == "PASS"
        and live.fresh
        and live.source_eligible
        and release_ok
        and not hold.active
        and str(exec_state.get("status") or "") != "EXECUTION_ACTIVE"
    )

    if can_authorize and str(exec_state.get("status") or "") not in (
        "RELOCKED_AFTER_COMPLETION_OR_FAILURE",
    ):
        # Fresh authorization window
        promotion = "LOCKED"  # production promotion never auto-unlocked by H1C
        safe_to_execute = "YES"
        execution_scope = list(live.execution_scope or auth_scope)
        overall = "AUTHORIZED_FOR_CONTROLLED_EXECUTION"
        # strip hold/live blockers that were only informational once cleared
        blockers = [b for b in blockers if not b.startswith("OPERATOR_HOLD") and not b.startswith("LIVE_PROOF") and b != "RELEASE_EVENT_MISSING"]
    else:
        safe_to_execute = "NO"
        promotion = "LOCKED"
        if hold.active:
            overall = "OPERATOR_HOLD_ACTIVE"
        elif live.status == "MISSING":
            overall = "LIVE_PROOF_MISSING"
        elif live.status == "STALE":
            overall = "LIVE_PROOF_STALE"
        elif authorization_status in ("REVOKED", "DENIED", "SUPERSEDED"):
            overall = "AUTHORIZATION_REVOKED"
        elif authorization_status not in ("GRANTED", "CONSUMED"):
            overall = "ELIGIBLE_BLOCKED"
        elif str(exec_state.get("status") or "") == "RELOCKED_AFTER_COMPLETION_OR_FAILURE":
            overall = (
                "EXECUTION_FAILED"
                if exec_state.get("last_result") == "FAILED"
                else "EXECUTION_COMPLETE"
            )
        elif not release_ok and not hold.active:
            overall = "OPERATOR_RELEASE_PENDING"

    # Hard invariants: never emit success semantics when blockers remain critical
    critical = [
        b
        for b in blockers
        if any(
            x in b
            for x in (
                "MOCK",
                "MISMATCH",
                "MALFORMED",
                "MISSING",
                "STALE",
                "EXPIRED",
                "REVOKED",
                "DENIED",
                "HOLD_ACTIVE",
                "WRONG_ACTOR",
                "INELIGIBLE",
                "ABSENT",
                "NOT_GRANTED",
            )
        )
    ]
    if critical:
        safe_to_execute = "NO"
        promotion = "LOCKED"
        if overall == "AUTHORIZED_FOR_CONTROLLED_EXECUTION":
            overall = "ELIGIBLE_BLOCKED"

    # Never allow forbidden success tokens in overall
    if overall.upper() in SUCCESS_FORBIDDEN:
        overall = "ERROR"
        blockers.append("FORBIDDEN_OVERALL_STATUS_COLLAPSED")

    return {
        "candidate_id": candidate_id,
        "package_id": package_id,
        "package_digest": package_digest,
        "package_readiness": package_readiness,
        "authorization_status": authorization_status,
        "promotion": promotion,
        "safe_to_execute": safe_to_execute,
        "operator_hold": hold.to_dict(),
        "live_proof": live.to_dict(),
        "execution_scope": execution_scope,
        "blockers": blockers,
        "truth_updated_at": truth_updated_at,
        "overall_status": overall,
        "source_revision": git_sha(root),
        "h1c_state": overall if overall in H1C_STATES else "UNKNOWN",
        "founder_action_required": authorization_status
        not in ("GRANTED", "CONSUMED"),
        "controlled_execution_state": exec_state or None,
        "release_validated": release_ok,
    }


def build_doorstep_founder_packet(
    truth: dict, out_path: Path
) -> dict:
    """Produce DOORSTEP artifact for Michael — never auto-approves."""
    packet = {
        "artifact": "H1C_FOUNDER_AUTHORIZATION_DOORSTEP",
        "schema_version": "1.0",
        "generated_at": _now_iso(),
        "source_revision": truth.get("source_revision"),
        "action_required": "FOUNDER_REVIEW_AND_OPTIONAL_GRANT",
        "do_not_auto_approve": True,
        "candidate_id": truth.get("candidate_id"),
        "package_id": truth.get("package_id"),
        "package_digest": truth.get("package_digest"),
        "requested_execution_scope": [
            "h1c_controlled_dry_run",
            "local_read_only_probe",
            "local_ledger_write",
            "local_evidence_emit",
        ],
        "explicitly_excluded": [
            "money_movement",
            "key_provisioning",
            "store_submission",
            "external_dispatch",
            "production_promotion",
        ],
        "current_blockers": truth.get("blockers"),
        "instructions": [
            "Review package digest and candidate identity.",
            "If intentional, write founder decision with authorization_status=GRANTED bound to package_id and digest.",
            "Do not clear operator hold by deleting the hold file; use H1C release lifecycle after grant.",
            "Authorization is single-scope controlled dry-run only unless expanded explicitly.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return packet
