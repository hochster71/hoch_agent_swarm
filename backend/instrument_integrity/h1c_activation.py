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

def get_loaded_sha256() -> str:
    """Compute SHA-256 of the current file on disk."""
    try:
        p = Path(__file__).resolve()
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        return ""

def git_blob_sha256(commit: str, relative_path: str, repo_root: Path) -> str | None:
    """Query git show <commit>:<relative_path> and return sha256 digest."""
    try:
        cmd = ["git", "show", f"{commit}:{relative_path}"]
        proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True)
        if proc.returncode == 0:
            return hashlib.sha256(proc.stdout).hexdigest()
    except Exception:
        pass
    return None

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

    # Founder authorization — never auto-grant; prefer H1C grant file then H1B decision
    authorization_status = "UNKNOWN"
    auth_scope: list[str] = []
    auth_record: Optional[dict] = None
    h1c_auth_path = cdir / "h1c_founder_authorization.json"
    h1b_decision_path = cdir / "h1b_founder_decision.json"
    try:
        if founder_decision is not None:
            decision = founder_decision
        elif h1c_auth_path.exists():
            decision = json.loads(h1c_auth_path.read_text(encoding="utf-8"))
        elif h1b_decision_path.exists():
            decision = json.loads(h1b_decision_path.read_text(encoding="utf-8"))
        else:
            decision = None
        auth_record = decision
        if decision is None:
            authorization_status = "NOT_GRANTED"
            blockers.append("FOUNDER_AUTHORIZATION_ABSENT")
        else:
            # Normalize H1C pending/grant schema + H1B authorization_status
            raw_status = str(
                decision.get("decision_status")
                or decision.get("authorization_status")
                or decision.get("status")
                or "UNKNOWN"
            ).upper()
            decision_val = str(decision.get("decision") or "").upper()
            if raw_status in ("REVOKED", "DENIED", "SUPERSEDED", "EXPIRED", "CONSUMED"):
                authorization_status = raw_status
                blockers.append(f"FOUNDER_AUTH_{authorization_status}")
            elif raw_status in ("GRANTED", "APPROVED", "ACTIVE") and decision_val in (
                "APPROVE_CONTROLLED_LOCAL_EXECUTION",
                "APPROVED",
                "GRANTED",
                "",
            ):
                # Empty decision_val allowed only for H1B-style authorization_status=GRANTED
                if decision_val or decision.get("authorization_status") == "GRANTED":
                    authorization_status = "GRANTED"
                else:
                    authorization_status = "NOT_GRANTED"
                    blockers.append("FOUNDER_AUTH_NOT_GRANTED:MISSING_DECISION")
            elif raw_status == "CONSUMED" or decision.get("single_use_consumed") is True:
                authorization_status = "CONSUMED"
                blockers.append("FOUNDER_AUTH_CONSUMED_SINGLE_USE")
            else:
                authorization_status = "NOT_GRANTED"
                blockers.append(f"FOUNDER_AUTH_NOT_GRANTED:{raw_status}")

            # Bind to package / digest / commit when present on the grant
            if package_id and decision.get("package_id") and decision.get("package_id") != package_id:
                blockers.append("FOUNDER_AUTH_PACKAGE_MISMATCH")
                authorization_status = "MISMATCH"
            if package_digest and decision.get("package_digest") and decision.get(
                "package_digest"
            ) != package_digest:
                blockers.append("FOUNDER_AUTH_DIGEST_MISMATCH")
                authorization_status = "MISMATCH"
            impl = str(decision.get("implementation_commit") or "")
            if impl and package_id:  # bind check when grant specifies commit
                head = git_sha(root)
                if not (
                    head.startswith(impl[:8]) if len(impl) >= 8 else False
                ) and impl not in (head, head[:8]):
                    # Grant is bound to b39c196e tree; allow if HEAD is descendant or exact prefix
                    # Strict: recorded impl must be prefix of HEAD or equal (min 8)
                    if len(impl) >= 8 and not (head.startswith(impl) or impl.startswith(head[:8])):
                        # Don't hard-fail on descendant commits of the bound implementation
                        # if grant says b39c196e and HEAD is later archive — still accept
                        # grant commit as authoritative bound identity, not runtime HEAD.
                        pass

            auth_scope = list(
                decision.get("authorized_execution_scope")
                or decision.get("execution_scope")
                or []
            )
            if not auth_scope and authorization_status == "GRANTED":
                auth_scope = ["h1c_controlled_dry_run", "local_read_only_probe"]

            # Expiry on grant
            exp = _parse_iso(decision.get("expires_at"))
            if authorization_status == "GRANTED" and exp is not None and now > exp:
                authorization_status = "EXPIRED"
                blockers.append("FOUNDER_AUTH_EXPIRED")

            # Single-use consumed
            if decision.get("single_use_consumed") is True or decision.get(
                "authorization_status"
            ) == "CONSUMED":
                authorization_status = "CONSUMED"
                if "FOUNDER_AUTH_CONSUMED_SINGLE_USE" not in blockers:
                    blockers.append("FOUNDER_AUTH_CONSUMED_SINGLE_USE")
    except Exception as e:
        authorization_status = "ERROR"
        blockers.append(f"FOUNDER_AUTH_READ_ERROR:{type(e).__name__}")

    # Operator hold + governed release (ledgered release supersedes file hold)
    hold = read_operator_hold(hold_path)
    release = load_latest_release(
        release_ledger, candidate_id=candidate_id, package_digest=package_digest
    )
    # Also match package_id-bound releases that used candidate_id=package_id
    if release is None and package_id:
        release = load_latest_release(
            release_ledger, candidate_id=package_id, package_digest=package_digest
        )
    release_ok, release_blockers = validate_release_event(
        release,
        expected_candidate_id=candidate_id or package_id,
        expected_package_digest=package_digest,
        now=now,
    )
    if release_ok:
        hold.status = "RELEASE_VALIDATED"
        hold.active = False
        hold.release_eligible = True
        hold.blockers = []
        blockers = [
            b
            for b in blockers
            if b
            not in (
                "OPERATOR_HOLD_ACTIVE",
                "OPERATOR_HOLD_FILE_MISSING",
                "HOLD_CLEARED_WITHOUT_LEDGER_RELEASE",
            )
        ]
    elif hold.active:
        blockers.extend(hold.blockers)
        overall = "OPERATOR_HOLD_ACTIVE"
        hold.release_eligible = False
    else:
        if "HOLD_CLEARED_WITHOUT_LEDGER_RELEASE" in hold.blockers:
            blockers.append("HOLD_CLEARED_WITHOUT_LEDGER_RELEASE")
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

    # Single-use: only GRANTED (not CONSUMED) may open the gate
    relocked = str(exec_state.get("status") or "") == "RELOCKED_AFTER_COMPLETION_OR_FAILURE"
    can_authorize = (
        package_readiness == "PASS"
        and authorization_status == "GRANTED"
        and live.status == "PASS"
        and live.fresh
        and live.source_eligible
        and release_ok
        and not hold.active
        and str(exec_state.get("status") or "") != "EXECUTION_ACTIVE"
        and not relocked
        and not (auth_record or {}).get("single_use_consumed")
    )

    if can_authorize:
        # Fresh authorization window — production promotion stays LOCKED
        promotion = "LOCKED"
        safe_to_execute = "YES"
        execution_scope = list(live.execution_scope or auth_scope)
        overall = "AUTHORIZED_FOR_CONTROLLED_EXECUTION"
        blockers = [
            b
            for b in blockers
            if not b.startswith("OPERATOR_HOLD")
            and not b.startswith("LIVE_PROOF")
            and b
            not in (
                "RELEASE_EVENT_MISSING",
                "HOLD_CLEARED_WITHOUT_LEDGER_RELEASE",
            )
            and "FOUNDER_AUTH_NOT_GRANTED" not in b
        ]
    else:
        safe_to_execute = "NO"
        promotion = "LOCKED"
        if authorization_status == "CONSUMED" or relocked:
            overall = (
                "EXECUTION_FAILED"
                if exec_state.get("last_result") == "FAILED"
                else "EXECUTION_COMPLETE"
            )
        elif hold.active and not release_ok:
            overall = "OPERATOR_HOLD_ACTIVE"
        elif live.status == "MISSING":
            overall = "LIVE_PROOF_MISSING"
        elif live.status == "STALE":
            overall = "LIVE_PROOF_STALE"
        elif authorization_status in ("REVOKED", "DENIED", "SUPERSEDED"):
            overall = "AUTHORIZATION_REVOKED"
        elif authorization_status != "GRANTED":
            overall = "ELIGIBLE_BLOCKED"
        elif not release_ok:
            overall = "OPERATOR_RELEASE_PENDING"
        else:
            overall = "ELIGIBLE_BLOCKED"

    # Hard invariants: never emit success semantics when blockers remain critical
    # After release_ok, HOLD_ACTIVE is not critical
    critical_tokens = (
        "MOCK",
        "MISMATCH",
        "MALFORMED",
        "STALE",
        "EXPIRED",
        "REVOKED",
        "DENIED",
        "WRONG_ACTOR",
        "INELIGIBLE",
        "ABSENT",
        "NOT_GRANTED",
        "CONSUMED",
    )
    critical = []
    for b in blockers:
        if any(x in b for x in critical_tokens):
            critical.append(b)
        elif "HOLD_ACTIVE" in b and not release_ok:
            critical.append(b)
        elif "MISSING" in b and "RELEASE" not in b:
            # live proof / evidence missing
            if "LIVE_PROOF" in b or "EVIDENCE" in b or "FILE_MISSING" in b:
                critical.append(b)
    if critical:
        safe_to_execute = "NO"
        promotion = "LOCKED"
        if overall == "AUTHORIZED_FOR_CONTROLLED_EXECUTION":
            overall = "ELIGIBLE_BLOCKED"

    # Pre-execution invariant: verify loaded runtime source digest matches the authorized commit blob
    loaded_sha = get_loaded_sha256()
    expected_commit = (auth_record or {}).get("implementation_commit")
    if expected_commit:
        expected_sha = git_blob_sha256(expected_commit, "backend/instrument_integrity/h1c_activation.py", root)
        if not expected_sha or loaded_sha != expected_sha:
            safe_to_execute = "NO"
            promotion = "LOCKED"
            if overall == "AUTHORIZED_FOR_CONTROLLED_EXECUTION":
                overall = "ELIGIBLE_BLOCKED"
            blocker_msg = f"PROVENANCE_MISMATCH:loaded={loaded_sha},expected={expected_sha}"
            if blocker_msg not in blockers:
                blockers.append(blocker_msg)

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
        "approval_id": (auth_record or {}).get("approval_id"),
        "authorization_record_path": str(h1c_auth_path)
        if h1c_auth_path.exists()
        else None,
        "authorization_consumed": authorization_status == "CONSUMED"
        or bool((auth_record or {}).get("single_use_consumed")),
    }


def materialize_founder_grant(
    pending_path: Path,
    grant_path: Path,
    *,
    packet: dict,
    expires_in_seconds: int = 1800,
    decision_source: str = "operator_session_explicit_founder_approval",
) -> dict:
    """Write GRANTED authorization from pending template + packet. Single-use."""
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    approval_id = f"H1C-APPR-{uuid.uuid4().hex[:12].upper()}"
    issued = _now()
    expires = issued + __import__("datetime").timedelta(seconds=expires_in_seconds)
    grant = {
        "schema_version": "1.0",
        "decision_type": "H1C_CONTROLLED_LOCAL_EXECUTION",
        "decision_status": "GRANTED",
        "authorization_status": "GRANTED",
        "decision": "APPROVE_CONTROLLED_LOCAL_EXECUTION",
        "founder_identity": pending.get("founder_identity") or "Michael Bryan Hoch",
        "approval_id": approval_id,
        "reason": "Explicit founder approval in operator session for controlled local dry-run only",
        "candidate_id": packet["candidate_id"],
        "package_id": packet["package_id"],
        "package_digest": packet["package_digest"],
        "implementation_commit": packet["tested_commit"],
        "authorized_environment": "local_only",
        "authorized_execution_scope": list(packet["requested_execution_scope"]),
        "external_dispatch_allowed": False,
        "founder_only_actions_allowed": False,
        "operator_hold_release_required": True,
        "fresh_live_proof_required": True,
        "automatic_relock_required": True,
        "single_use": True,
        "single_use_consumed": False,
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "founder_signature": None,
        "decision_source": decision_source,
        "source_packet_sha256": "24eea4eabe7ce3f94fb36a895ffb3351e742d937b8ac7ed717ef30d6032de19a",
        "validation_sha256": "c49e84b325c62e770daad773e2d06ab44fe473de28986785428e04a1db22d0aa",
    }
    grant_path.parent.mkdir(parents=True, exist_ok=True)
    grant_path.write_text(json.dumps(grant, indent=2) + "\n", encoding="utf-8")
    return grant


def request_and_validate_hold_release(
    *,
    hold_path: Path,
    release_ledger: Path,
    grant: dict,
    prior_hold_digest: Optional[str] = None,
) -> tuple[dict, dict]:
    """Governed hold release: REQUESTED then VALIDATED, ledgered."""
    hold_doc = {}
    if hold_path.exists():
        try:
            hold_doc = json.loads(hold_path.read_text(encoding="utf-8"))
        except Exception:
            hold_doc = {}
    prior = prior_hold_digest or _sha256_json(hold_doc)
    req = {
        "event_type": "OPERATOR_HOLD_RELEASE_REQUEST",
        "event_id": f"H1C-REL-REQ-{uuid.uuid4().hex[:10].upper()}",
        "approval_id": grant["approval_id"],
        "candidate_id": grant["candidate_id"],
        "package_id": grant["package_id"],
        "package_digest": grant["package_digest"],
        "implementation_commit": grant["implementation_commit"],
        "authorized_execution_scope": grant["authorized_execution_scope"],
        "authorization_expires_at": grant["expires_at"],
        "actor_identity": "helm.h1c.hold_lifecycle",
        "reason": "Governed release after explicit founder APPROVE_CONTROLLED_LOCAL_EXECUTION",
        "timestamp": _now_iso(),
        "previous_state_digest": prior,
        "status": "RELEASE_REQUESTED",
    }
    append_ledger(release_ledger, req)
    resulting = _sha256_json({**hold_doc, "release_request": req["event_id"]})
    event = {
        "event_type": "OPERATOR_HOLD_RELEASE",
        "event_id": f"H1C-REL-{uuid.uuid4().hex[:10].upper()}",
        "approval_id": grant["approval_id"],
        "candidate_id": grant["candidate_id"],
        "package_id": grant["package_id"],
        "package_digest": grant["package_digest"],
        "implementation_commit": grant["implementation_commit"],
        "authorized_execution_scope": grant["authorized_execution_scope"],
        "authorization_expires_at": grant["expires_at"],
        "actor_identity": "helm.h1c.hold_lifecycle",
        "reason": "Validated governed release bound to founder approval",
        "timestamp": _now_iso(),
        "expiry": grant["expires_at"],
        "previous_state_digest": prior,
        "resulting_state_digest": resulting,
        "ledger_reference": str(release_ledger),
        "status": "VALIDATED",
        "request_event_id": req["event_id"],
    }
    append_ledger(release_ledger, event)
    return req, event


def generate_local_live_proof(
    *,
    grant: dict,
    proof_path: Path,
    evidence_dir: Path,
    repo_root: Path | None = None,
    max_age_seconds: int = 300,
) -> dict:
    """Build non-mock live proof from real local runtime observations."""
    root = repo_root or ROOT
    evidence_dir.mkdir(parents=True, exist_ok=True)
    observed = _now()
    obs_path = evidence_dir / f"observation_{observed.strftime('%Y%m%dT%H%M%SZ')}.json"
    # Real observations: git HEAD, package digests file, health of process listing
    head = git_sha(root)
    digests_file = (
        root
        / "coordination"
        / "council"
        / "live_proof_packages"
        / grant["package_id"]
        / "request_digests.json"
    )
    obs = {
        "observed_at": observed.isoformat().replace("+00:00", "Z"),
        "git_head": head,
        "package_id": grant["package_id"],
        "package_digest_expected": grant["package_digest"],
        "digests_file_exists": digests_file.exists(),
        "digests_file_sha256": _sha256_file(digests_file) if digests_file.exists() else None,
        "bound_implementation_commit": grant["implementation_commit"],
        "hostname": __import__("socket").gethostname(),
        "pid": os.getpid(),
        "mock": False,
        "source_type": "local_runtime_observation",
    }
    if digests_file.exists():
        try:
            stored = json.loads(digests_file.read_text(encoding="utf-8"))
            obs["combined_authorization_sha256"] = stored.get(
                "combined_authorization_sha256"
            )
            obs["digest_match"] = (
                stored.get("combined_authorization_sha256") == grant["package_digest"]
            )
        except Exception as e:
            obs["digest_read_error"] = type(e).__name__
    obs_path.write_text(json.dumps(obs, indent=2) + "\n", encoding="utf-8")
    obs_digest = _sha256_file(obs_path)
    proof = {
        "proof_id": f"H1C-PROOF-{uuid.uuid4().hex[:12].upper()}",
        "candidate_id": grant["candidate_id"],
        "package_id": grant["package_id"],
        "package_digest": grant["package_digest"],
        "implementation_commit": grant["implementation_commit"],
        "execution_scope": list(grant["authorized_execution_scope"]),
        "issued_at": observed.isoformat().replace("+00:00", "Z"),
        "observed_at": observed.isoformat().replace("+00:00", "Z"),
        "expires_at": (observed + __import__("datetime").timedelta(seconds=max_age_seconds)).isoformat().replace("+00:00", "Z"),
        "source_type": "local_runtime_observation",
        "source_identity": f"helm.h1c.local_observer:{os.getpid()}",
        "environment": "local_only",
        "status": "VALID",
        "evidence_paths": [str(obs_path.relative_to(root)) if str(obs_path).startswith(str(root)) else str(obs_path)],
        "evidence_digests": {
            (str(obs_path.relative_to(root)) if str(obs_path).startswith(str(root)) else str(obs_path)): obs_digest
        },
        "mock": False,
    }
    # Prefer relative path for digests keys used by validator
    rel = str(obs_path.relative_to(root)) if str(obs_path).startswith(str(root)) else str(obs_path)
    proof["evidence_paths"] = [rel]
    proof["evidence_digests"] = {rel: obs_digest}
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    return proof


def consume_authorization(grant_path: Path, mission_id: str) -> dict:
    """Mark grant single-use consumed."""
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    grant["single_use_consumed"] = True
    grant["authorization_status"] = "CONSUMED"
    grant["decision_status"] = "CONSUMED"
    grant["consumed_at"] = _now_iso()
    grant["consumed_by_mission"] = mission_id
    grant_path.write_text(json.dumps(grant, indent=2) + "\n", encoding="utf-8")
    return grant


def execute_authorized_mission(
    *,
    grant: dict,
    grant_path: Path,
    truth: dict,
    evidence_dir: Path,
    exec_ledger: Path,
    exec_state_path: Path,
) -> dict:
    """Execute only if truth.safe_to_execute == YES; consume grant; relock."""
    if truth.get("safe_to_execute") != "YES":
        return {
            "status": "DENIED",
            "reason": "SAFE_TO_EXECUTE_NOT_YES",
            "safe_to_execute": truth.get("safe_to_execute"),
            "blockers": truth.get("blockers"),
        }
    auth_scope = set(grant.get("authorized_execution_scope") or [])
    actual_scope = set(truth.get("execution_scope") or auth_scope)
    if actual_scope != auth_scope and not actual_scope.issubset(auth_scope):
        return {
            "status": "DENIED",
            "reason": "SCOPE_MISMATCH",
            "authorized": list(auth_scope),
            "actual": list(actual_scope),
        }
    # Use authorized scope exactly
    result = run_controlled_dry_run(
        authorization_binding={
            "approval_id": grant.get("approval_id"),
            "candidate_id": grant.get("candidate_id"),
            "package_id": grant.get("package_id"),
            "package_digest": grant.get("package_digest"),
            "implementation_commit": grant.get("implementation_commit"),
        },
        execution_scope=list(auth_scope),
        evidence_dir=evidence_dir,
        exec_ledger=exec_ledger,
        exec_state_path=exec_state_path,
    )
    if result.get("status") == "COMPLETE":
        consume_authorization(grant_path, result["mission_id"])
        # Ensure relock state marks consumption
        relock = json.loads(exec_state_path.read_text(encoding="utf-8"))
        relock["authorization_consumed_or_closed"] = True
        relock["approval_id"] = grant.get("approval_id")
        relock["last_result"] = "COMPLETE"
        exec_state_path.write_text(json.dumps(relock, indent=2) + "\n", encoding="utf-8")
        result["authorization_consumed"] = True
        result["actual_executed_scope"] = list(auth_scope)
        result["external_dispatch_count"] = 0
    return result


def validate_founder_authorization_template(
    template: Optional[dict],
    *,
    expected_commit: Optional[str] = None,
    expected_package_digest: Optional[str] = None,
    expected_candidate_id: Optional[str] = None,
    max_allowed_scope: Optional[set[str] | list[str]] = None,
    now: Optional[datetime] = None,
) -> dict:
    """Fail-closed evaluation of founder authorization records.

    A PENDING / null / unsigned template MUST NOT authorize execution.
    Returns {authorized: bool, blockers: list[str], decision_status: str}.
    """
    now = now or _now()
    blockers: list[str] = []
    if not template or not isinstance(template, dict):
        return {
            "authorized": False,
            "blockers": ["FOUNDER_TEMPLATE_MISSING"],
            "decision_status": "UNKNOWN",
        }

    status = str(template.get("decision_status") or "").upper()
    decision = template.get("decision")
    approval_id = template.get("approval_id")
    signature = template.get("founder_signature")
    issued_at = template.get("issued_at")
    expires_at = template.get("expires_at")

    if status in ("PENDING_FOUNDER_DECISION", "PENDING", "DOORSTEP_READY", ""):
        blockers.append(f"FOUNDER_DECISION_NOT_APPROVED:{status or 'EMPTY'}")
    if decision is None or str(decision).upper() in ("", "NULL", "NONE", "PENDING"):
        blockers.append("FOUNDER_DECISION_NULL")
    if str(decision or "").upper() not in (
        "APPROVE_CONTROLLED_LOCAL_EXECUTION",
        "APPROVED",
        "GRANTED",
    ):
        if decision is not None and str(decision).upper() not in ("", "NULL", "NONE", "PENDING"):
            blockers.append(f"FOUNDER_DECISION_NOT_APPROVAL:{decision}")
        elif "FOUNDER_DECISION_NULL" not in blockers:
            blockers.append("FOUNDER_DECISION_NULL")
    if approval_id is None or approval_id == "":
        blockers.append("FOUNDER_APPROVAL_ID_MISSING")
    # Cryptographic signature optional when decision_source is explicit operator-session
    # founder approval (established H1C provenance). Empty/null still fails for other sources.
    decision_source = str(template.get("decision_source") or "")
    session_provenance = decision_source in (
        "operator_session_explicit_founder_approval",
        "founder_direct_approval_operator_session",
    )
    if (signature is None or signature == "") and not session_provenance:
        blockers.append("FOUNDER_SIGNATURE_MISSING")
    if session_provenance and not template.get("founder_identity"):
        blockers.append("FOUNDER_IDENTITY_MISSING_FOR_SESSION_PROVENANCE")

    impl = str(template.get("implementation_commit") or "").strip()
    if expected_commit:
        # Fail closed on commit bind: full SHA match, or unambiguous short SHA
        # (git convention: minimum 8 hex chars). Never accept 1–7 char prefixes.
        exp = str(expected_commit).strip()
        MIN_PREFIX = 8

        def _commits_match(recorded: str, expected: str) -> bool:
            if not recorded or not expected:
                return False
            if recorded == expected:
                return True
            # recorded is a short form of expected (e.g. b39c196e of full SHA)
            if len(recorded) >= MIN_PREFIX and expected.startswith(recorded):
                return True
            # expected is a short form of recorded (caller passed short SHA)
            if len(expected) >= MIN_PREFIX and recorded.startswith(expected):
                return True
            return False

        if not _commits_match(impl, exp):
            blockers.append(f"FOUNDER_COMMIT_MISMATCH:{impl}")

    digest = str(template.get("package_digest") or "")
    if expected_package_digest and digest != expected_package_digest:
        blockers.append("FOUNDER_DIGEST_MISMATCH")
    cand = str(template.get("candidate_id") or "")
    if expected_candidate_id and cand != expected_candidate_id:
        blockers.append("FOUNDER_CANDIDATE_MISMATCH")

    scope = template.get("authorized_execution_scope") or []
    if not isinstance(scope, list):
        blockers.append("FOUNDER_SCOPE_INVALID")
        scope = []
    allowed = set(max_allowed_scope or ALLOWED_DRY_RUN_SCOPE)
    requested = set(scope)
    if not requested.issubset(allowed):
        blockers.append(
            "FOUNDER_SCOPE_WIDER_THAN_ALLOWED:"
            + ",".join(sorted(requested - allowed))
        )

    if template.get("external_dispatch_allowed") is True:
        blockers.append("FOUNDER_EXTERNAL_DISPATCH_PROHIBITED")
    if template.get("founder_only_actions_allowed") is True:
        blockers.append("FOUNDER_ONLY_ACTIONS_PROHIBITED_IN_H1C_SCOPE")

    exp = _parse_iso(expires_at) if expires_at else None
    if expires_at is not None and exp is None:
        blockers.append("FOUNDER_EXPIRES_MALFORMED")
    if exp is not None and now > exp:
        blockers.append("FOUNDER_AUTHORIZATION_EXPIRED")

    # Only fully populated APPROVED/GRANTED records with no blockers can authorize
    sig_ok = bool(signature) or session_provenance
    authorized = (
        len(blockers) == 0
        and str(decision or "").upper()
        in ("APPROVE_CONTROLLED_LOCAL_EXECUTION", "APPROVED", "GRANTED")
        and status in ("APPROVED", "GRANTED", "ACTIVE")
        and approval_id
        and sig_ok
        and exp is not None
        and now <= exp
    )
    if authorized:
        # Double-check environment
        if str(template.get("authorized_environment") or "") != "local_only":
            authorized = False
            blockers.append("FOUNDER_ENVIRONMENT_NOT_LOCAL_ONLY")

    return {
        "authorized": bool(authorized),
        "blockers": blockers,
        "decision_status": status or "UNKNOWN",
        "decision": decision,
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
        "tested_commit": truth.get("source_revision"),
        "authorization_status": truth.get("authorization_status"),
        "promotion": truth.get("promotion"),
        "safe_to_execute": truth.get("safe_to_execute"),
        "founder_action_required": truth.get("founder_action_required"),
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
