"""mission_contract.py — HELM Mission Contract v1, enforced in code (not prose).

Adopted by EDR-0007. Template: docs/helm/mission/MISSION_TEMPLATE_v1.md
Schema:    coordination/governance/mission_schema_v1.json

WHAT THIS IS
------------
The third layer of the HELM prompt stack:

    Mission overlay   (changes constantly)  <- validated here
        v
    Role doctrine     (rarely changes)      -- coordination/governance/role_overlays/
        v
    Provider binding  (replaceable)         -- coordination/governance/role_bindings.json

A mission is an EXECUTION CONTRACT. SCOPE and TOOLS_ALLOWED are allowlists: what is
not named is denied. That is what lets one Builder doctrine serve architecture, UI,
and runtime work without minting a permanent doctrine per specialization.

TRUTH_SOURCE IS A PROJECTION, NOT A NEW VOCABULARY
--------------------------------------------------
HELM's founder-ratified truth classification lives in backend/security/proof_contract.py
(OBSERVED / DERIVED / CACHED / ASSERTED / UNKNOWN, with ADVANCING = {OBSERVED, DERIVED}).
TRUTH_SOURCE names the *mechanism* that will produce evidence and projects onto exactly
one ratified class. Consequences, by design:

  * STATIC_ANALYSIS -> ASSERTED. A clean linter reads source; it is not evidence that
    the system behaved. It cannot advance a critical node.
  * HUMAN_INPUT -> ASSERTED. Founder authority governs GATES (spend/release/submit);
    it does not manufacture evidence. The rule that stops a model's claim from
    advancing state stops a human's claim too.

FAILS CLOSED
------------
An unparseable, incomplete, or self-contradictory mission raises MissionContractError.
There is no partial acceptance and no defaulting of a missing field.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

# --- Bind to the ratified truth enum. Never redefine it here. ----------------
try:  # pragma: no cover - exercised in-repo; guarded so the module is importable standalone
    from backend.security.proof_contract import ADVANCING, Truth
except Exception:  # pragma: no cover
    try:
        from security.proof_contract import ADVANCING, Truth  # type: ignore
    except Exception:
        from enum import Enum

        class Truth(str, Enum):  # type: ignore[no-redef]
            OBSERVED = "OBSERVED"
            DERIVED = "DERIVED"
            CACHED = "CACHED"
            ASSERTED = "ASSERTED"
            UNKNOWN = "UNKNOWN"

        ADVANCING = frozenset({Truth.OBSERVED, Truth.DERIVED})  # type: ignore[assignment]


SCHEMA_NAME = "HELM_MISSION_CONTRACT_v1"

MISSION_ID_RE = re.compile(r"^M-[A-Z0-9]+-[A-Z0-9-]+$")

REQUIRED_FIELDS = (
    "MISSION_ID", "TITLE", "OWNER", "ROLE", "OBJECTIVE", "SUCCESS_CRITERIA",
    "EXPECTED_OUTPUTS", "SCOPE", "TOOLS_ALLOWED", "EDR_REQUIRED",
    "FOUNDER_GATES", "STOP_CONDITIONS", "EVIDENCE_REQUIRED", "TRUTH_SOURCE", "RETURN",
)

LIST_FIELDS = frozenset({
    "SUCCESS_CRITERIA", "INPUTS", "EXPECTED_OUTPUTS", "SCOPE", "TOOLS_ALLOWED",
    "CONSTRAINTS", "FOUNDER_GATES", "STOP_CONDITIONS", "EVIDENCE_REQUIRED",
})

# Allowlists that may legitimately be empty (a mission that approaches no founder gate).
MAY_BE_EMPTY = frozenset({"FOUNDER_GATES", "INPUTS", "CONSTRAINTS"})

OWNERS = frozenset({"founder", "orchestrator"})
ROLES = frozenset({"orchestrator", "builder", "auditor", "research", "security"})
RETURN_VALUES = frozenset({"DONE", "PARTIAL", "BLOCKED"})

FOUNDER_GATES = frozenset({
    "SPEND", "KEYS", "RELEASE", "SUBMISSION", "MONEY",
    "PRODUCTION_DEPLOY", "CREDENTIAL_CREATION", "EXTERNAL_IRREVERSIBLE",
})

# TRUTH_SOURCE (mechanism) -> ratified truth class. The single source of the mapping.
TRUTH_SOURCE_PROJECTION: Dict[str, Truth] = {
    "LIVE_RUNTIME": Truth.OBSERVED,
    "TEST_EXECUTION": Truth.OBSERVED,
    "DETERMINISTIC_SCRIPT": Truth.DERIVED,
    "STATIC_ANALYSIS": Truth.ASSERTED,
    "HUMAN_INPUT": Truth.ASSERTED,
    "UNKNOWN": Truth.UNKNOWN,
}


class MissionContractError(ValueError):
    """Raised when a mission does not satisfy the contract. Fails closed."""

    def __init__(self, violations: List[str]):
        self.violations = list(violations)
        super().__init__(
            f"MISSION_CONTRACT_FAILED ({len(self.violations)}): " + " | ".join(self.violations)
        )


def projected_truth(truth_source: str) -> Truth:
    """Map a TRUTH_SOURCE mechanism onto the founder-ratified truth class."""
    key = str(truth_source).strip().upper()
    if key not in TRUTH_SOURCE_PROJECTION:
        raise MissionContractError([f"TRUTH_SOURCE '{truth_source}' is not a known mechanism"])
    return TRUTH_SOURCE_PROJECTION[key]


def advances_state(truth_source: str) -> bool:
    """True only when the mechanism yields a truth class in ADVANCING."""
    return projected_truth(truth_source) in ADVANCING


@dataclass
class Mission:
    """A validated mission. Constructing one through `validate` is the only sanctioned path."""

    data: Dict[str, Any]

    @property
    def mission_id(self) -> str:
        return self.data["MISSION_ID"]

    @property
    def role(self) -> str:
        return self.data["ROLE"]

    @property
    def truth_source(self) -> str:
        return self.data["TRUTH_SOURCE"]

    @property
    def truth(self) -> Truth:
        return projected_truth(self.truth_source)

    @property
    def advancing(self) -> bool:
        return self.truth in ADVANCING

    @property
    def founder_gates(self) -> List[str]:
        return list(self.data.get("FOUNDER_GATES") or [])

    def permits_path(self, path: str) -> bool:
        """SCOPE is an allowlist of path prefixes. Anything else is denied."""
        norm = os.path.normpath(str(path)).lstrip("./")
        for allowed in self.data["SCOPE"]:
            a = os.path.normpath(str(allowed)).lstrip("./")
            if norm == a or norm.startswith(a.rstrip("/") + "/"):
                return True
        return False

    def permits_tool(self, tool: str) -> bool:
        return str(tool) in set(self.data["TOOLS_ALLOWED"])

    def may_return_done(self) -> tuple[bool, str]:
        """A DONE claim requires an advancing truth class. Enforces NO FAKE GREEN."""
        if not self.advancing:
            return False, (
                f"TRUTH_SOURCE={self.truth_source} projects to {self.truth.value}, which is not in "
                f"ADVANCING — this mission may return PARTIAL or BLOCKED, not DONE"
            )
        return True, "ok"


def _as_list(value: Any) -> Optional[List[Any]]:
    if isinstance(value, list):
        return value
    return None


def validate(mission: Dict[str, Any], *, strict_id: bool = True) -> Mission:
    """Validate a mission dict against the contract. Raises MissionContractError.

    Collects EVERY violation before raising, so an author fixes one round of errors
    rather than discovering them one at a time.
    """
    v: List[str] = []

    if not isinstance(mission, dict):
        raise MissionContractError(["mission must be a mapping"])

    # --- required presence -------------------------------------------------
    for f in REQUIRED_FIELDS:
        if f not in mission or mission[f] in (None, "", []):
            if f in MAY_BE_EMPTY and f in mission and mission[f] == []:
                continue
            v.append(f"missing required field: {f}")

    # --- shapes ------------------------------------------------------------
    for f in LIST_FIELDS:
        if f in mission and mission[f] not in (None, "") and _as_list(mission[f]) is None:
            v.append(f"{f} must be a list")

    # --- enums -------------------------------------------------------------
    if mission.get("MISSION_ID") and strict_id:
        if not MISSION_ID_RE.match(str(mission["MISSION_ID"])):
            v.append("MISSION_ID must match M-<FACTORY>-<SLUG> (uppercase, hyphenated)")

    owner = str(mission.get("OWNER", "")).lower()
    if owner and owner not in OWNERS:
        v.append(f"OWNER '{owner}' not in {sorted(OWNERS)}")

    role = str(mission.get("ROLE", "")).lower()
    if role and role not in ROLES:
        v.append(f"ROLE '{role}' not in {sorted(ROLES)}")

    edr = str(mission.get("EDR_REQUIRED", "")).upper()
    if edr and edr not in {"YES", "NO"}:
        v.append("EDR_REQUIRED must be YES or NO")

    ts = str(mission.get("TRUTH_SOURCE", "")).upper()
    if ts and ts not in TRUTH_SOURCE_PROJECTION:
        v.append(
            f"TRUTH_SOURCE '{ts}' not in {sorted(TRUTH_SOURCE_PROJECTION)} — "
            "it names the evidence MECHANISM"
        )

    gates = _as_list(mission.get("FOUNDER_GATES")) or []
    for g in gates:
        if str(g).upper() not in FOUNDER_GATES:
            v.append(f"FOUNDER_GATES contains unknown gate '{g}'")

    # --- allowlists may not be empty (empty != wildcard) -------------------
    for f in ("SCOPE", "TOOLS_ALLOWED", "SUCCESS_CRITERIA", "EXPECTED_OUTPUTS",
              "STOP_CONDITIONS", "EVIDENCE_REQUIRED"):
        lst = _as_list(mission.get(f))
        if lst is not None and len(lst) == 0:
            v.append(f"{f} is empty — an empty allowlist denies everything and is never a wildcard")

    # --- invariant: a declared founder gate needs a stop condition ---------
    if gates:
        stops = " ".join(str(s).lower() for s in (_as_list(mission.get("STOP_CONDITIONS")) or []))
        if "founder gate" not in stops:
            v.append(
                "FOUNDER_GATES declared but STOP_CONDITIONS does not include a founder-gate stop — "
                "declaring a gate never authorizes it"
            )

    # --- invariant: EDR_REQUIRED=YES obliges an EDR output ----------------
    if edr == "YES":
        outs = " ".join(str(o).lower() for o in (_as_list(mission.get("EXPECTED_OUTPUTS")) or []))
        if "edr" not in outs:
            v.append("EDR_REQUIRED=YES but no EDR path appears in EXPECTED_OUTPUTS")

    # --- invariant: RETURN must offer only sanctioned values --------------
    ret = str(mission.get("RETURN", ""))
    if ret:
        named = {t for t in RETURN_VALUES if t in ret.upper()}
        if not named:
            v.append(f"RETURN must reference at least one of {sorted(RETURN_VALUES)}")

    if v:
        raise MissionContractError(v)

    normalized = dict(mission)
    normalized["OWNER"] = owner
    normalized["ROLE"] = role
    normalized["EDR_REQUIRED"] = edr
    normalized["TRUTH_SOURCE"] = ts
    normalized["FOUNDER_GATES"] = [str(g).upper() for g in gates]
    return Mission(normalized)


def conformance(mission: Dict[str, Any]) -> Dict[str, Any]:
    """Non-raising report — used to survey EXISTING mission sources without migrating them."""
    try:
        m = validate(mission)
        return {
            "conforms": True,
            "violations": [],
            "truth": m.truth.value,
            "advancing": m.advancing,
        }
    except MissionContractError as e:
        present = [f for f in REQUIRED_FIELDS if f in (mission if isinstance(mission, dict) else {})]
        return {
            "conforms": False,
            "violations": e.violations,
            "required_present": present,
            "required_missing": [f for f in REQUIRED_FIELDS if f not in present],
        }


def load_schema(repo_root: str = ".") -> Dict[str, Any]:
    p = os.path.join(repo_root, "coordination", "governance", "mission_schema_v1.json")
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# EXECUTION_CONTEXT — immutable execution fingerprint (EDR-0007 amendment 1)
# ---------------------------------------------------------------------------
# Reuses the INCUMBENT correlation identifier rather than minting a new one.
# `transaction.py` already generates `correlation_id` (uuid4) for every mission
# commit; introducing a separate `run_id` would recreate exactly the dual-vocabulary
# drift that TRUTH_SOURCE was designed to avoid. EXECUTION_CONTEXT therefore carries
# `correlation_id`, not `run_id`.
#
# Lifecycles differ and are deliberately kept apart:
#   * EXECUTION_CONTEXT  — captured at mission ISSUE time; fingerprints the code and
#                          doctrine the mission runs against.
#   * transaction_id / mission_version — minted at WRITE time by MissionTransaction.
# A mission declares the former; it does not pre-declare the latter.
#
# HONESTY RULE: every capture may fail. A field that cannot be determined is
# recorded as UNKNOWN. It is never guessed, defaulted, or back-filled.

EXECUTION_CONTEXT_FIELDS = (
    "correlation_id",          # incumbent identifier (transaction.py), NOT a new run_id
    "commit_sha",              # HEAD at issue time, or UNKNOWN
    "dirty",                   # uncommitted changes present? bool, or UNKNOWN
    "runtime_version",         # HELM runtime version
    "doctrine_version",        # governing constitution/doctrine version
    "mission_schema_version",  # this contract's version
)

UNKNOWN_VALUE = "UNKNOWN"


def capture_execution_context(
    repo_root: str = ".",
    *,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture the execution fingerprint. Unknown fields are UNKNOWN, never invented."""
    import subprocess
    import uuid

    def _git(*args: str) -> Optional[str]:
        try:
            out = subprocess.run(
                ["git", *args], cwd=repo_root, capture_output=True, text=True, timeout=10
            )
            if out.returncode != 0:
                return None
            return out.stdout.strip()
        except Exception:
            return None

    sha = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    dirty: Any = UNKNOWN_VALUE if status is None else bool(status.strip())

    schema_version = UNKNOWN_VALUE
    try:
        schema_version = load_schema(repo_root).get("schema", UNKNOWN_VALUE)
    except Exception:
        pass

    doctrine_version = UNKNOWN_VALUE
    const = os.path.join(repo_root, "docs", "helm", "HELM_CONSTITUTION_v1.0.md")
    if os.path.exists(const):
        doctrine_version = "HELM_CONSTITUTION_v1.0"

    runtime_version = UNKNOWN_VALUE
    rt = os.path.join(repo_root, "backend", "helm_runtime")
    if os.path.isdir(rt):
        runtime_version = "helm_runtime/four-engine"

    return {
        "correlation_id": correlation_id or str(uuid.uuid4()),
        "commit_sha": sha or UNKNOWN_VALUE,
        "dirty": dirty,
        "runtime_version": runtime_version,
        "doctrine_version": doctrine_version,
        "mission_schema_version": schema_version,
    }


def reproducibility(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Can evidence produced under this context be reproduced?

    EDR-0006's Proof Record requires *Reproduced*. Evidence gathered against an
    unknown commit, or against a working tree with uncommitted changes, cannot be
    reproduced from the repository alone.

    This REPORTS; it does not block. The working tree is routinely dirty during
    active development, and a blocking rule would halt every mission — which would
    be governance theatre, not governance. The Auditor decides what a non-
    reproducible context is worth.
    """
    reasons: List[str] = []
    if ctx.get("commit_sha") in (None, "", UNKNOWN_VALUE):
        reasons.append("commit_sha is UNKNOWN — the code state cannot be pinned")
    if ctx.get("dirty") is True:
        reasons.append("working tree has uncommitted changes — the tree is not recoverable from git alone")
    if ctx.get("dirty") == UNKNOWN_VALUE:
        reasons.append("dirty state is UNKNOWN — cleanliness could not be determined")
    return {"reproducible": not reasons, "reasons": reasons}


def validate_execution_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Validate an EXECUTION_CONTEXT block. Fails closed on missing keys."""
    if not isinstance(ctx, dict):
        raise MissionContractError(["EXECUTION_CONTEXT must be a mapping"])
    missing = [f for f in EXECUTION_CONTEXT_FIELDS if f not in ctx]
    if missing:
        raise MissionContractError(
            [f"EXECUTION_CONTEXT missing field: {f}" for f in missing]
        )
    if "run_id" in ctx:
        raise MissionContractError([
            "EXECUTION_CONTEXT uses the incumbent 'correlation_id'; 'run_id' would fork "
            "the identifier vocabulary (see transaction.py)"
        ])
    return dict(ctx)


__all__ = [
    "SCHEMA_NAME", "Mission", "MissionContractError", "validate", "conformance",
    "projected_truth", "advances_state", "TRUTH_SOURCE_PROJECTION",
    "REQUIRED_FIELDS", "FOUNDER_GATES", "load_schema",
    "EXECUTION_CONTEXT_FIELDS", "capture_execution_context", "reproducibility",
    "validate_execution_context", "UNKNOWN_VALUE",
]
