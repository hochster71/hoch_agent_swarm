"""HELM H1 — PRODUCTION authorization validator, candidate registry, atomic consume ledger.

This is the ONLY authorization validator. Tests import it; they do not reimplement it.
(Grok F5: the validator previously existed only inside tests/test_h1a_corrective_validation.py.)

It imports NO network client. It never reads a credential value. It cannot grant an
authorization, lift the operator hold, set frontier quorum, or enable promotion.

Three responsibilities:
  1. CandidateRegistry   — exactly one ACTIVE_CANDIDATE, no filename inference (Grok F2)
  2. H1AuthorizationValidator — full binding of every immutable field (Grok F3, F4, F5)
  3. AuthorizationLedger — durable, append-only, atomically-consumed (Grok F6, F7)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
COUNCIL_DIR = ROOT / "coordination" / "council"
PACKAGES_DIR = COUNCIL_DIR / "live_proof_packages"
REGISTRY_PATH = COUNCIL_DIR / "h1_candidate_registry.json"
LEDGER_PATH = Path(os.environ.get("HELM_AUTH_LEDGER", COUNCIL_DIR / "authorization_ledger.jsonl"))
ROSTER_PATH = COUNCIL_DIR / "council_roster.json"
CONTRACTS_PATH = COUNCIL_DIR / "frontier_seat_contracts.json"

FOUNDER_IDENTITY = "Michael Bryan Hoch"
REQUIRED_OVERRIDE_SCOPE = "SINGLE_H1_PROOF_ONLY"
PERMITTED_RUN_COUNT = 1

ACTIVE_CANDIDATE = "ACTIVE_CANDIDATE"
NON_EXECUTABLE_TEST_PACKAGE = "NON_EXECUTABLE_TEST_PACKAGE"
SUPERSEDED_BLOCKED_CANDIDATE = "SUPERSEDED_BLOCKED_CANDIDATE"
EVIDENCE_RECONCILIATION_REQUIRED = "EVIDENCE_RECONCILIATION_REQUIRED"

CREDENTIAL_REFERENCES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
}


class AuthorizationError(Exception):
    """Raised on any authorization defect. Carries the stable block codes."""

    def __init__(self, blocks: list[str]):
        self.blocks = blocks
        super().__init__("H1_AUTHORIZATION_BLOCKED: " + ", ".join(blocks))


def canonical_digest(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


def _load(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_ts(value: Any) -> datetime.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


# ===========================================================================
# 1. CANDIDATE REGISTRY  (Grok F2)
# ===========================================================================

class CandidateRegistry:
    """The single authoritative answer to 'which package may be authorized?'

    Reads the committed registry FILE. It does NOT infer from filenames, does not
    sort a directory listing, and does not take last-write-wins. If the registry
    disagrees with itself, every package is ineligible and the registry reports
    EVIDENCE_RECONCILIATION_REQUIRED.
    """

    def __init__(self, registry_path: Path | None = None):
        self.path = registry_path or REGISTRY_PATH
        self.doc = _load(self.path) or {}
        self.errors: list[str] = []
        self._validate()

    def _validate(self) -> None:
        packages = self.doc.get("packages") or []
        if not packages:
            self.errors.append("REGISTRY_EMPTY")
            return

        actives = [p for p in packages if p.get("classification") == ACTIVE_CANDIDATE]
        if len(actives) != 1:
            self.errors.append(f"EXPECTED_ONE_ACTIVE_CANDIDATE_FOUND_{len(actives)}")

        declared = self.doc.get("authoritative_candidate_package_id")
        if len(actives) == 1 and declared != actives[0].get("package_id"):
            self.errors.append("AUTHORITATIVE_ID_DISAGREES_WITH_ACTIVE_CLASSIFICATION")

        if self.doc.get("candidate_count") != 1:
            self.errors.append("CANDIDATE_COUNT_NOT_ONE")

        for p in packages:
            cls = p.get("classification")
            pid = p.get("package_id", "<unknown>")
            # A TEST or SUPERSEDED package can NEVER be authorization eligible.
            if cls in (NON_EXECUTABLE_TEST_PACKAGE, SUPERSEDED_BLOCKED_CANDIDATE):
                if p.get("authorization_eligible"):
                    self.errors.append(f"INELIGIBLE_CLASS_MARKED_ELIGIBLE:{pid}")
            elif cls == ACTIVE_CANDIDATE:
                if not p.get("authorization_eligible"):
                    self.errors.append(f"ACTIVE_CANDIDATE_NOT_ELIGIBLE:{pid}")
            else:
                self.errors.append(f"UNKNOWN_CLASSIFICATION:{pid}:{cls}")
            # execution_eligible is false until the bounded dispatch transaction opens.
            if p.get("execution_eligible"):
                self.errors.append(f"EXECUTION_ELIGIBLE_MUST_BE_FALSE:{pid}")

    @property
    def reconciled(self) -> bool:
        return not self.errors

    @property
    def status(self) -> str:
        return "RECONCILED" if self.reconciled else EVIDENCE_RECONCILIATION_REQUIRED

    def active_candidate(self) -> str | None:
        if not self.reconciled:
            return None
        return self.doc.get("authoritative_candidate_package_id")

    def classification(self, package_id: str) -> str:
        for p in self.doc.get("packages") or []:
            if p.get("package_id") == package_id:
                return p.get("classification") or SUPERSEDED_BLOCKED_CANDIDATE
        return SUPERSEDED_BLOCKED_CANDIDATE  # unknown package: never eligible

    def is_authorization_eligible(self, package_id: str) -> bool:
        if not self.reconciled:
            return False
        return (
            self.classification(package_id) == ACTIVE_CANDIDATE
            and package_id == self.active_candidate()
        )


# ===========================================================================
# 2. PRODUCTION AUTHORIZATION VALIDATOR  (Grok F3, F4, F5)
# ===========================================================================

class H1AuthorizationValidator:
    """Binds a founder authorization to EXACTLY one package, byte for byte.

    Every immutable field is compared against a fresh recomputation of the package
    on disk. Nothing is trusted from the authorization document itself.
    """

    # Stable block codes
    B_NOT_GRANTED = "AUTHORIZATION_NOT_GRANTED"
    B_REGISTRY_UNRECONCILED = "EVIDENCE_RECONCILIATION_REQUIRED"
    B_NOT_ACTIVE_CANDIDATE = "PACKAGE_NOT_ACTIVE_CANDIDATE"
    B_TEST_PACKAGE = "NON_EXECUTABLE_TEST_PACKAGE"
    B_SUPERSEDED = "SUPERSEDED_BLOCKED_CANDIDATE"
    B_PACKAGE_ID = "PACKAGE_ID_MISMATCH"
    B_AUTHORIZATION_ID = "AUTHORIZATION_ID_MISMATCH"
    B_COMBINED_DIGEST = "COMBINED_DIGEST_MISMATCH"
    B_PROMPT_DIGEST = "PROMPT_DIGEST_MISMATCH"
    B_ROSTER_DIGEST = "ROSTER_DIGEST_MISMATCH"
    B_CONTRACT_DIGEST = "CONTRACT_DIGEST_MISMATCH"
    B_MODEL_POLICY_DIGEST = "MODEL_POLICY_DIGEST_MISMATCH"
    B_BUDGET_DIGEST = "BUDGET_DIGEST_MISMATCH"
    B_REQUEST_DIGEST = "PROVIDER_REQUEST_DIGEST_MISMATCH"
    B_PROVIDER = "PROVIDER_SUBSTITUTION_NOT_AUTHORIZED"
    B_MODEL = "MODEL_SUBSTITUTION_NOT_AUTHORIZED"
    B_RUN_COUNT = "PERMITTED_RUN_COUNT_INVALID"
    B_ISSUED_AT = "ISSUED_AT_INVALID"
    B_EXPIRED = "AUTHORIZATION_EXPIRED"
    B_FOUNDER_IDENTITY = "FOUNDER_IDENTITY_MISMATCH"
    B_APPROVAL_REFERENCE = "APPROVAL_REFERENCE_MISSING"
    B_OVERRIDE_SCOPE = "OPERATOR_HOLD_OVERRIDE_SCOPE_INVALID"
    B_PROMOTION = "PRODUCTION_PROMOTION_MUST_BE_FALSE"
    B_PROVIDER_SUBSTITUTION_FLAG = "PROVIDER_SUBSTITUTION_FLAG_MUST_BE_FALSE"
    B_MODEL_SUBSTITUTION_FLAG = "MODEL_SUBSTITUTION_FLAG_MUST_BE_FALSE"
    B_PACKAGE_MISSING = "PACKAGE_NOT_FOUND"
    B_CREDENTIAL = "MISSING_CREDENTIAL"

    def __init__(
        self,
        package_id: str,
        packages_dir: Path | None = None,
        registry: CandidateRegistry | None = None,
    ):
        self.package_id = package_id
        self.packages_dir = packages_dir or PACKAGES_DIR
        self.pkg = self.packages_dir / package_id
        self.registry = registry if registry is not None else CandidateRegistry()

    # -- fresh recomputation of the package, never trusting stored digests ----
    def recompute(self) -> dict:
        prompt_path = self.pkg / "prompt.redacted.txt"
        model_policy = _load(self.pkg / "model_policy.json")
        budget = _load(self.pkg / "budget_limits.json")
        pricing = _load(self.pkg / "pricing_evidence.json")
        roster = _load(ROSTER_PATH) or {}
        contracts = _load(CONTRACTS_PATH) or {}

        reqs = {
            m: _load(self.pkg / "provider_requests" / f"{m}.request.redacted.json")
            for m in ("chatgpt", "claude", "grok")
        }
        if not prompt_path.exists() or budget is None or any(r is None for r in reqs.values()):
            return {}

        prompt = prompt_path.read_text(encoding="utf-8")
        out = {
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "roster_sha256": canonical_digest(roster),
            "frontier_contract_sha256": canonical_digest(contracts),
            "model_policy_sha256": canonical_digest(model_policy) if model_policy is not None else None,
            "budget_policy_sha256": canonical_digest(budget),
            "pricing_evidence_sha256": canonical_digest(pricing) if pricing is not None else None,
        }
        for m, r in reqs.items():
            out[f"{m}_request_sha256"] = canonical_digest(r)

        out["combined_authorization_sha256"] = canonical_digest(
            {
                "package_id": self.package_id,
                "provider_list": ["openai", "anthropic", "xai"],
                "exact_models": {
                    "openai": reqs["chatgpt"].get("model"),
                    "anthropic": reqs["claude"].get("model"),
                    "xai": reqs["grok"].get("model"),
                },
                "prompt": prompt,
                "chatgpt_request": reqs["chatgpt"],
                "claude_request": reqs["claude"],
                "grok_request": reqs["grok"],
                "budget_limits": budget,
                "run_count": 1,
                "expires_in_hours": 24,
                "operator_hold_override_scope": REQUIRED_OVERRIDE_SCOPE,
                "production_promotion_authorized": False,
                "pricing_evidence": pricing,
            }
        )
        out["_requests"] = reqs
        return out

    def validate(
        self,
        authorization: dict,
        *,
        now: datetime.datetime | None = None,
        requested_providers: list[str] | None = None,
        requested_models: dict[str, str] | None = None,
        credentials: dict | None = None,
        require_credentials: bool = True,
    ) -> list[str]:
        """Return the list of blocks. EMPTY list == fully bound and valid."""
        now = now or _now()
        blocks: list[str] = []
        auth = authorization or {}

        # -- candidate eligibility (registry is authoritative) ----------------
        if not self.registry.reconciled:
            blocks.append(self.B_REGISTRY_UNRECONCILED)
        cls = self.registry.classification(self.package_id)
        if cls == NON_EXECUTABLE_TEST_PACKAGE:
            blocks.append(self.B_TEST_PACKAGE)
        elif cls == SUPERSEDED_BLOCKED_CANDIDATE:
            blocks.append(self.B_SUPERSEDED)
        elif not self.registry.is_authorization_eligible(self.package_id):
            blocks.append(self.B_NOT_ACTIVE_CANDIDATE)

        # -- status -----------------------------------------------------------
        if auth.get("authorization_status") != "GRANTED":
            blocks.append(self.B_NOT_GRANTED)

        # -- identity binding --------------------------------------------------
        if auth.get("package_id") != self.package_id:
            blocks.append(self.B_PACKAGE_ID)

        expected_auth_id = None
        if self.package_id.startswith("HELM-H1-CANDIDATE-"):
            expected_auth_id = self.package_id.replace("HELM-H1-CANDIDATE-", "HELM-H1-AUTH-")
        template = _load(self.pkg / "founder_authorization.template.json") or {}
        expected_auth_id = template.get("authorization_id") or expected_auth_id
        if not auth.get("authorization_id") or auth.get("authorization_id") != expected_auth_id:
            blocks.append(self.B_AUTHORIZATION_ID)

        # -- package integrity: fresh recomputation ----------------------------
        recomputed = self.recompute()
        if not recomputed:
            blocks.append(self.B_PACKAGE_MISSING)
            return sorted(set(blocks))

        stored = _load(self.pkg / "request_digests.json") or {}
        reqs = recomputed.pop("_requests")

        digest_checks = [
            ("combined_authorization_sha256", self.B_COMBINED_DIGEST),
            ("prompt_sha256", self.B_PROMPT_DIGEST),
            ("roster_sha256", self.B_ROSTER_DIGEST),
            ("frontier_contract_sha256", self.B_CONTRACT_DIGEST),
            ("model_policy_sha256", self.B_MODEL_POLICY_DIGEST),
            ("budget_policy_sha256", self.B_BUDGET_DIGEST),
            ("chatgpt_request_sha256", self.B_REQUEST_DIGEST),
            ("claude_request_sha256", self.B_REQUEST_DIGEST),
            ("grok_request_sha256", self.B_REQUEST_DIGEST),
        ]
        for field, block in digest_checks:
            if recomputed.get(field) != stored.get(field):
                blocks.append(block)

        # The authorization document must carry the SAME combined digest we just
        # recomputed from disk. This is the byte-for-byte binding.
        if auth.get("combined_authorization_sha256") != recomputed["combined_authorization_sha256"]:
            blocks.append(self.B_COMBINED_DIGEST)

        # -- exact providers ----------------------------------------------------
        permitted_providers = list(auth.get("permitted_providers") or [])
        if sorted(permitted_providers) != ["anthropic", "openai", "xai"]:
            blocks.append(self.B_PROVIDER)
        for provider in requested_providers or []:
            if provider not in permitted_providers:
                blocks.append(self.B_PROVIDER)
                break

        # -- exact models (must equal the models inside the signed requests) ----
        package_models = {
            "openai": reqs["chatgpt"].get("model"),
            "anthropic": reqs["claude"].get("model"),
            "xai": reqs["grok"].get("model"),
        }
        permitted_models = auth.get("permitted_models") or {}
        if not isinstance(permitted_models, dict) or permitted_models != package_models:
            blocks.append(self.B_MODEL)
        for provider, model in (requested_models or {}).items():
            if package_models.get(provider) != model:
                blocks.append(self.B_MODEL)
                break

        # -- run count ----------------------------------------------------------
        if auth.get("permitted_run_count") != PERMITTED_RUN_COUNT:
            blocks.append(self.B_RUN_COUNT)

        # -- issued_at / expires_at ---------------------------------------------
        issued = _parse_ts(auth.get("issued_at"))
        expires = _parse_ts(auth.get("expires_at"))
        if issued is None or issued > now:
            blocks.append(self.B_ISSUED_AT)
        if expires is None or now > expires:
            blocks.append(self.B_EXPIRED)

        # -- founder identity + approval reference ------------------------------
        if auth.get("issued_by") != FOUNDER_IDENTITY:
            blocks.append(self.B_FOUNDER_IDENTITY)
        if not auth.get("approval_reference"):
            blocks.append(self.B_APPROVAL_REFERENCE)

        # -- scope locks ---------------------------------------------------------
        if auth.get("operator_hold_override_scope") != REQUIRED_OVERRIDE_SCOPE:
            blocks.append(self.B_OVERRIDE_SCOPE)
        if auth.get("production_promotion_authorized") is not False:
            blocks.append(self.B_PROMOTION)
        if auth.get("provider_substitution_authorized") is not False:
            blocks.append(self.B_PROVIDER_SUBSTITUTION_FLAG)
        if auth.get("model_substitution_authorized") is not False:
            blocks.append(self.B_MODEL_SUBSTITUTION_FLAG)

        # -- credentials: existence only, never value -----------------------------
        if require_credentials:
            matrix = credential_matrix() if credentials is None else credentials
            for provider in ("openai", "anthropic", "xai"):
                if (matrix.get(provider) or {}).get("status") != "PRESENT_UNVERIFIED":
                    blocks.append(self.B_CREDENTIAL)
                    break

        return sorted(set(blocks))


# ===========================================================================
# 3. ATOMIC AUTHORIZATION LEDGER  (Grok F6, F7)
# ===========================================================================

class LedgerError(Exception):
    pass



class AuthorizationLedger:
    """Durable, append-only, exclusively-locked authorization consumption ledger.

    An authorization can be consumed EXACTLY ONCE, ever, across processes and reboots.
    Consumption is guarded by an O_CREAT|O_EXCL lock file (atomic on POSIX) plus an
    fcntl exclusive lock, and the ledger itself is append-only JSONL: entries are never
    rewritten, so a consumption cannot be silently rolled back.
    """

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else LEDGER_PATH
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    # -- read ---------------------------------------------------------------
    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                raise LedgerError("LEDGER_CORRUPT: non-JSON line present")
        return out

    def is_consumed(self, authorization_id: str) -> bool:
        return any(
            e.get("authorization_id") == authorization_id and e.get("status") == "CONSUMED"
            for e in self.entries()
        )

    def consumption(self, authorization_id: str) -> dict | None:
        for e in self.entries():
            if e.get("authorization_id") == authorization_id and e.get("status") == "CONSUMED":
                return e
        return None

    # -- exclusive lock -----------------------------------------------------
    def _acquire_lock(self, timeout: float = 0.0):
        import fcntl
        deadline = time.time() + timeout
        
        # O_CREAT | O_RDWR ensures the file exists and we can lock it.
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except (BlockingIOError, OSError):
                if time.time() >= deadline:
                    os.close(fd)
                    raise LedgerError("AUTHORIZATION_LOCK_HELD")
                time.sleep(0.01)

    def _release_lock(self, fd) -> None:
        import fcntl
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except Exception:
            pass

    # -- atomic consume -----------------------------------------------------
    def consume(
        self,
        *,
        authorization_id: str,
        package_id: str,
        run_id: str,
        request_digest: str,
        lock_timeout: float = 0.0,
    ) -> dict:
        """Atomically consume an authorization exactly once.

        Raises LedgerError('AUTHORIZATION_ALREADY_CONSUMED') on replay, and
        LedgerError('AUTHORIZATION_LOCK_HELD') if a concurrent worker holds the lock.
        Callers MUST have already passed H1AuthorizationValidator with zero blocks:
        a failed validation never reaches this method, so it never consumes.
        """
        fd = self._acquire_lock(timeout=lock_timeout)
        try:
            # Re-read INSIDE the lock. This is the atomicity boundary.
            if self.is_consumed(authorization_id):
                raise LedgerError("AUTHORIZATION_ALREADY_CONSUMED")

            pid = os.getpid()
            entry = {
                "authorization_id": authorization_id,
                "package_id": package_id,
                "run_id": run_id,
                "request_digest": request_digest,
                "process_id": pid,
                "consumed_at": _now().isoformat().replace("+00:00", "Z"),
                "status": "CONSUMED",
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Append-only: O_APPEND, never truncate, never rewrite a prior line.
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            return entry
        finally:
            self._release_lock(fd)


# ===========================================================================
# Credential reference matrix — existence only, value NEVER read
# ===========================================================================

def credential_matrix(env: dict[str, str] | None = None) -> dict:
    env = os.environ if env is None else env
    return {
        provider: {
            "credential_reference": ref,
            # `in` never materializes the value; os.environ.get() would.
            "status": "PRESENT_UNVERIFIED" if ref in env else "NOT_PROVISIONED",
            "value_exposed": False,
        }
        for provider, ref in CREDENTIAL_REFERENCES.items()
    }


def credential_readiness(matrix: dict | None = None) -> str:
    matrix = matrix or credential_matrix()
    statuses = {v["status"] for v in matrix.values()}
    if statuses == {"NOT_PROVISIONED"}:
        return "NOT_PROVISIONED"
    if statuses == {"PRESENT_UNVERIFIED"}:
        return "PRESENT_UNVERIFIED"
    return "NOT_PROVISIONED_OR_PRESENT_UNVERIFIED"


# ===========================================================================
# The ONLY pre-dispatch entry point.
# ===========================================================================

def authorize_and_consume(
    *,
    authorization: dict,
    package_id: str,
    run_id: str,
    packages_dir: Path | None = None,
    registry: CandidateRegistry | None = None,
    ledger: AuthorizationLedger | None = None,
    credentials: dict | None = None,
    now: datetime.datetime | None = None,
    requested_providers: list[str] | None = None,
    requested_models: dict[str, str] | None = None,
) -> dict:
    """Validate fully, THEN consume atomically. Order matters and is enforced here.

    A failed validation raises BEFORE the ledger is ever touched, so a rejected
    authorization is never consumed (Grok F6: 'failed pre-dispatch validation does
    not consume authorization').
    """
    validator = H1AuthorizationValidator(package_id, packages_dir, registry)
    blocks = validator.validate(
        authorization,
        now=now,
        requested_providers=requested_providers,
        requested_models=requested_models,
        credentials=credentials,
    )
    if blocks:
        raise AuthorizationError(blocks)

    ledger = ledger or AuthorizationLedger()
    if ledger.is_consumed(authorization["authorization_id"]):
        raise AuthorizationError(["AUTHORIZATION_REPLAY"])

    return ledger.consume(
        authorization_id=authorization["authorization_id"],
        package_id=package_id,
        run_id=run_id,
        request_digest=authorization["combined_authorization_sha256"],
    )


def dispatch_live_permitted() -> bool:
    """H1B remediation: live dispatch stays hard-blocked, unconditionally."""
    return False
