"""HELM H1B — candidate registry, integrity recomputation, credential reference matrix.

READ-ONLY WITH RESPECT TO AUTHORITY.

This module NEVER:
  - imports or instantiates a network client
  - reads, prints, logs, hashes, or persists a secret VALUE
  - sets authorization_status to GRANTED
  - sets safe_to_execute_now / promotion_eligible / frontier quorum to true
  - disables the operator hold

It answers three questions with evidence:
  1. Which H1 package is the single authorization-eligible candidate?
  2. Does that package's stored digest chain still match a fresh recomputation?
  3. Is each provider credential reference present (existence only, never value)?
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKAGES_DIR = ROOT / "coordination" / "council" / "live_proof_packages"
ROSTER_PATH = ROOT / "coordination" / "council" / "council_roster.json"
CONTRACTS_PATH = ROOT / "coordination" / "council" / "frontier_seat_contracts.json"

CANDIDATE_PREFIX = "HELM-H1-CANDIDATE-"
TEST_TOKENS = ("TEST", "-TEST-", "TEST-H1-RUN")

# Classification vocabulary (LOCKED by the H1B mission brief).
ELIGIBLE = "AUTHORIZATION_ELIGIBLE_CANDIDATE"
SUPERSEDED = "SUPERSEDED_BLOCKED_CANDIDATE"
NON_EXECUTABLE_TEST = "NON_EXECUTABLE_TEST_PACKAGE"

CREDENTIAL_REFERENCES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
}


def canonical_digest(data: Any) -> str:
    """sort_keys JSON -> sha256. Must match scripts/council/generate_h1_package.py."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_test_package(package_id: str) -> bool:
    return any(token in package_id.upper() for token in TEST_TOKENS)


# ---------------------------------------------------------------------------
# Phase 4 — integrity recomputation
# ---------------------------------------------------------------------------

def recompute_package_integrity(package_id: str, packages_dir: Path | None = None) -> dict:
    """Independently recompute every digest and compare against the stored value.

    Any mismatch => PACKAGE_MUTATED_AFTER_REVIEW, which forces BLOCKED downstream.
    """
    packages_dir = packages_dir or PACKAGES_DIR
    pkg = packages_dir / package_id

    result: dict[str, Any] = {
        "package_id": package_id,
        "integrity_status": "PASS",
        "mismatches": [],
        "missing": [],
        "recomputed": {},
        "stored": {},
    }

    if not pkg.exists():
        result["integrity_status"] = "PACKAGE_NOT_FOUND"
        result["missing"].append(str(package_id))
        return result

    stored = _load_json(pkg / "request_digests.json")
    if not isinstance(stored, dict):
        result["integrity_status"] = "PACKAGE_MUTATED_AFTER_REVIEW"
        result["missing"].append("request_digests.json")
        return result
    result["stored"] = stored

    prompt_path = pkg / "prompt.redacted.txt"
    model_policy = _load_json(pkg / "model_policy.json")
    budget_limits = _load_json(pkg / "budget_limits.json")
    pricing_evidence = _load_json(pkg / "pricing_evidence.json")
    roster = _load_json(ROSTER_PATH) or {}
    contracts = _load_json(CONTRACTS_PATH) or {}

    recomputed: dict[str, str] = {}

    if prompt_path.exists():
        prompt = prompt_path.read_text(encoding="utf-8")
        recomputed["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    else:
        result["missing"].append("prompt.redacted.txt")

    if model_policy is not None:
        recomputed["model_policy_sha256"] = canonical_digest(model_policy)
    else:
        result["missing"].append("model_policy.json")

    if budget_limits is not None:
        recomputed["budget_policy_sha256"] = canonical_digest(budget_limits)
    else:
        result["missing"].append("budget_limits.json")

    if pricing_evidence is not None:
        recomputed["pricing_evidence_sha256"] = canonical_digest(pricing_evidence)

    recomputed["roster_sha256"] = canonical_digest(roster)
    recomputed["frontier_contract_sha256"] = canonical_digest(contracts)

    provider_requests: dict[str, Any] = {}
    for member, filename in (
        ("chatgpt", "chatgpt.request.redacted.json"),
        ("claude", "claude.request.redacted.json"),
        ("grok", "grok.request.redacted.json"),
    ):
        req = _load_json(pkg / "provider_requests" / filename)
        if req is None:
            result["missing"].append(f"provider_requests/{filename}")
            continue
        provider_requests[member] = req
        recomputed[f"{member}_request_sha256"] = canonical_digest(req)

    # Combined authorization digest — reconstructed from the same immutable fields
    # the generator covered. Only computed when every input is present.
    if (
        prompt_path.exists()
        and budget_limits is not None
        and len(provider_requests) == 3
        and pricing_evidence is not None
    ):
        auth_fields = {
            "package_id": package_id,
            "provider_list": ["openai", "anthropic", "xai"],
            "exact_models": {
                "openai": provider_requests["chatgpt"].get("model"),
                "anthropic": provider_requests["claude"].get("model"),
                "xai": provider_requests["grok"].get("model"),
            },
            "prompt": prompt_path.read_text(encoding="utf-8"),
            "chatgpt_request": provider_requests["chatgpt"],
            "claude_request": provider_requests["claude"],
            "grok_request": provider_requests["grok"],
            "budget_limits": budget_limits,
            "run_count": 1,
            "expires_in_hours": 24,
            "operator_hold_override_scope": "SINGLE_H1_PROOF_ONLY",
            "production_promotion_authorized": False,
            "pricing_evidence": pricing_evidence,
        }
        recomputed["combined_authorization_sha256"] = canonical_digest(auth_fields)

    result["recomputed"] = recomputed

    for key, value in recomputed.items():
        if key not in stored:
            result["missing"].append(f"request_digests.json:{key}")
            continue
        if stored[key] != value:
            result["mismatches"].append(
                {"field": key, "stored": stored[key], "recomputed": value}
            )

    if result["mismatches"]:
        result["integrity_status"] = "PACKAGE_MUTATED_AFTER_REVIEW"
    elif result["missing"]:
        result["integrity_status"] = "INCOMPLETE_PACKAGE"

    return result


# ---------------------------------------------------------------------------
# Phase 2 — candidate reconciliation
# ---------------------------------------------------------------------------

def _classification_evidence(package_id: str, pkg: Path) -> dict:
    validation = _load_json(pkg / "validation.json") or {}
    manifest = _load_json(pkg / "launch_manifest.json") or {}
    template = _load_json(pkg / "founder_authorization.template.json") or {}
    return {"validation": validation, "manifest": manifest, "template": template}


def reconcile_candidates(packages_dir: Path | None = None) -> dict:
    """Classify every H1 package; return exactly one authorization-eligible candidate.

    Reconciliation rule (evidence-based, deterministic):
      - any package whose ID carries a TEST token   -> NON_EXECUTABLE_TEST_PACKAGE
      - any package already flagged BLOCKED / SUPERSEDED / non-executable -> SUPERSEDED
      - any legacy HELM-H1-PACKAGE-* (pre-candidate schema, no combined digest)
                                                    -> SUPERSEDED
      - of the remaining timestamped candidates, the NEWEST timestamp is the single
        authorization-eligible candidate; all older ones -> SUPERSEDED
      - if the newest candidate fails integrity recomputation, NOTHING is eligible.

    If the rule cannot land on exactly one, status is EVIDENCE_RECONCILIATION_REQUIRED.
    """
    packages_dir = packages_dir or PACKAGES_DIR
    if not packages_dir.exists():
        return {
            "status": "EVIDENCE_RECONCILIATION_REQUIRED",
            "reason": "PACKAGES_DIR_MISSING",
            "active_candidate": None,
            "packages": [],
        }

    entries = sorted(p.name for p in packages_dir.iterdir() if p.is_dir())
    packages: list[dict] = []
    timestamped: list[str] = []

    for package_id in entries:
        pkg = packages_dir / package_id
        evidence = _classification_evidence(package_id, pkg)
        validation = evidence["validation"]
        prior_status = str(validation.get("status") or validation.get("validation_status") or "")

        if is_test_package(package_id):
            classification = NON_EXECUTABLE_TEST
            reason = "PACKAGE_ID_CARRIES_TEST_TOKEN"
        elif not package_id.startswith(CANDIDATE_PREFIX):
            classification = SUPERSEDED
            reason = "LEGACY_PRE_CANDIDATE_SCHEMA"
        elif prior_status in ("BLOCKED", "SUPERSEDED_BLOCKED_CANDIDATE", NON_EXECUTABLE_TEST):
            classification = SUPERSEDED
            reason = f"PRIOR_VALIDATION_{prior_status or 'BLOCKED'}"
        else:
            classification = None  # decided below, by recency
            reason = "TIMESTAMPED_CANDIDATE"
            timestamped.append(package_id)

        packages.append(
            {
                "package_id": package_id,
                "classification": classification,
                "reason": reason,
                "authorization_eligible": False,
                "execution_eligible": False,
                "prior_validation_status": prior_status or None,
            }
        )

    by_id = {p["package_id"]: p for p in packages}

    if not timestamped:
        return {
            "status": "EVIDENCE_RECONCILIATION_REQUIRED",
            "reason": "NO_TIMESTAMPED_CANDIDATE",
            "active_candidate": None,
            "packages": packages,
        }

    # Newest by embedded UTC timestamp (HELM-H1-CANDIDATE-YYYYmmddTHHMMSSZ-HASH).
    def _ts(pid: str) -> str:
        return pid[len(CANDIDATE_PREFIX):].split("-")[0]

    ordered = sorted(timestamped, key=_ts)
    active = ordered[-1]
    superseded = ordered[:-1]

    for pid in superseded:
        by_id[pid]["classification"] = SUPERSEDED
        by_id[pid]["reason"] = f"SUPERSEDED_BY_NEWER_CANDIDATE:{active}"
        by_id[pid]["superseded_by"] = active

    integrity = recompute_package_integrity(active, packages_dir)
    if integrity["integrity_status"] != "PASS":
        by_id[active]["classification"] = SUPERSEDED
        by_id[active]["reason"] = integrity["integrity_status"]
        return {
            "status": "BLOCKED",
            "reason": integrity["integrity_status"],
            "active_candidate": None,
            "integrity": integrity,
            "packages": packages,
        }

    by_id[active]["classification"] = ELIGIBLE
    by_id[active]["reason"] = "NEWEST_INTEGRITY_VERIFIED_CANDIDATE"
    by_id[active]["authorization_eligible"] = True

    eligible = [p for p in packages if p["authorization_eligible"]]
    if len(eligible) != 1:
        return {
            "status": "EVIDENCE_RECONCILIATION_REQUIRED",
            "reason": f"EXPECTED_ONE_ELIGIBLE_CANDIDATE_FOUND_{len(eligible)}",
            "active_candidate": None,
            "packages": packages,
        }

    return {
        "status": "RECONCILED",
        "reason": "SINGLE_AUTHORIZATION_ELIGIBLE_CANDIDATE",
        "active_candidate": active,
        "integrity": integrity,
        "packages": packages,
    }


# ---------------------------------------------------------------------------
# Phase 3 — credential reference matrix (existence only, never value)
# ---------------------------------------------------------------------------

def credential_matrix(env: dict[str, str] | None = None) -> dict:
    """Existence check ONLY. The value is never read, logged, hashed, or persisted.

    `os.environ.__contains__` does not materialize the value.
    """
    env = os.environ if env is None else env
    matrix: dict[str, dict] = {}
    for provider, reference in CREDENTIAL_REFERENCES.items():
        present = reference in env
        matrix[provider] = {
            "credential_reference": reference,
            "status": "PRESENT_UNVERIFIED" if present else "NOT_PROVISIONED",
            "value_exposed": False,
        }
    return matrix


def credential_readiness_summary(matrix: dict | None = None) -> str:
    matrix = matrix or credential_matrix()
    statuses = {v["status"] for v in matrix.values()}
    if statuses == {"NOT_PROVISIONED"}:
        return "NOT_PROVISIONED"
    if statuses == {"PRESENT_UNVERIFIED"}:
        return "PRESENT_UNVERIFIED"
    return "NOT_PROVISIONED_OR_PRESENT_UNVERIFIED"


if __name__ == "__main__":  # pragma: no cover - operator convenience
    report = reconcile_candidates()
    report["credential_matrix"] = credential_matrix()
    print(json.dumps(report, indent=2))
