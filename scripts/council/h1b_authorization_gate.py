"""HELM H1B — authorization gate.

The single choke point every H1 live dispatch must pass through. It is a PURE
DECISION FUNCTION: it returns blocks, it never opens a socket. This module
deliberately imports no HTTP client, no SDK, and no socket library — see
tests/test_h1b_founder_decision.py::test_20_no_network_client_imported.

Doctrine (no fake green): the gate returns ALLOWED only when every single check
passes. Absence of evidence is a block, never a pass.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from scripts.council.h1b_candidate_registry import (
    ELIGIBLE,
    NON_EXECUTABLE_TEST,
    SUPERSEDED,
    credential_matrix,
    is_test_package,
    recompute_package_integrity,
    reconcile_candidates,
)

ROOT = Path(__file__).resolve().parents[2]

# Block codes — stable vocabulary, asserted by the test suite.
BLOCK_AUTHORIZATION_NOT_GRANTED = "AUTHORIZATION_NOT_GRANTED"
BLOCK_MISSING_CREDENTIAL = "MISSING_CREDENTIAL"
BLOCK_PACKAGE_ID_MISMATCH = "PACKAGE_ID_MISMATCH"
BLOCK_AUTHORIZATION_ID_MISMATCH = "AUTHORIZATION_ID_MISMATCH"
BLOCK_DIGEST_MISMATCH = "COMBINED_DIGEST_MISMATCH"
BLOCK_PACKAGE_MUTATED = "PACKAGE_MUTATED_AFTER_REVIEW"
BLOCK_AUTHORIZATION_EXPIRED = "AUTHORIZATION_EXPIRED"
BLOCK_AUTHORIZATION_REPLAY = "AUTHORIZATION_REPLAY"
BLOCK_RUN_COUNT_EXHAUSTED = "RUN_COUNT_EXHAUSTED"
BLOCK_PROVIDER_SUBSTITUTION = "PROVIDER_SUBSTITUTION_NOT_AUTHORIZED"
BLOCK_MODEL_SUBSTITUTION = "MODEL_SUBSTITUTION_NOT_AUTHORIZED"
BLOCK_PROVIDER_COST_ABOVE_CAP = "PROVIDER_COST_ABOVE_CAP"
BLOCK_TOTAL_COST_ABOVE_CAP = "TOTAL_COST_ABOVE_CAP"
BLOCK_NON_EXECUTABLE_TEST_PACKAGE = "NON_EXECUTABLE_TEST_PACKAGE"
BLOCK_SUPERSEDED_CANDIDATE = "SUPERSEDED_BLOCKED_CANDIDATE"
BLOCK_PROMOTION_NOT_AUTHORIZED = "PRODUCTION_PROMOTION_NOT_AUTHORIZED"
BLOCK_OPERATOR_HOLD = "OPERATOR_HOLD_ACTIVE"

# The authorization override is scoped to exactly one proof and nothing else.
PERMITTED_OVERRIDE_SCOPE = "SINGLE_H1_PROOF_ONLY"


def _parse_ts(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def evaluate_launch(
    *,
    authorization: dict,
    package_id: str,
    packages_dir: Path | None = None,
    credentials: dict | None = None,
    now: datetime.datetime | None = None,
    consumed_authorization_ids: set[str] | frozenset[str] | None = None,
    executed_run_count: int = 0,
    requested_providers: list[str] | None = None,
    requested_models: dict[str, str] | None = None,
    estimated_costs_usd: dict[str, float] | None = None,
    classification: str | None = None,
) -> dict:
    """Return the launch decision for one H1 proof attempt.

    `allowed` is True only if `blocks` is empty. Callers MUST NOT dispatch on a
    non-empty `blocks` list.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    consumed = set(consumed_authorization_ids or ())
    blocks: list[str] = []

    # --- 1. Founder authorization must be explicitly GRANTED -----------------
    if authorization.get("authorization_status") != "GRANTED":
        blocks.append(BLOCK_AUTHORIZATION_NOT_GRANTED)

    # --- 2. Candidate classification ----------------------------------------
    if classification is None:
        if is_test_package(package_id):
            classification = NON_EXECUTABLE_TEST
        else:
            reconciliation = reconcile_candidates(packages_dir)
            entry = next(
                (p for p in reconciliation["packages"] if p["package_id"] == package_id),
                None,
            )
            classification = entry["classification"] if entry else SUPERSEDED

    if classification == NON_EXECUTABLE_TEST:
        blocks.append(BLOCK_NON_EXECUTABLE_TEST_PACKAGE)
    elif classification != ELIGIBLE:
        blocks.append(BLOCK_SUPERSEDED_CANDIDATE)

    # --- 3. Identity binding: authorization <-> package ----------------------
    if authorization.get("package_id") != package_id:
        blocks.append(BLOCK_PACKAGE_ID_MISMATCH)

    auth_id = authorization.get("authorization_id")
    if not auth_id or not str(auth_id).startswith("HELM-H1-AUTH-"):
        blocks.append(BLOCK_AUTHORIZATION_ID_MISMATCH)
    elif package_id.startswith("HELM-H1-CANDIDATE-") and str(auth_id) != package_id.replace(
        "HELM-H1-CANDIDATE-", "HELM-H1-AUTH-"
    ):
        blocks.append(BLOCK_AUTHORIZATION_ID_MISMATCH)

    # --- 4. Package integrity (Phase 4) -------------------------------------
    integrity = recompute_package_integrity(package_id, packages_dir)
    if integrity["integrity_status"] == "PACKAGE_MUTATED_AFTER_REVIEW":
        blocks.append(BLOCK_PACKAGE_MUTATED)
    elif integrity["integrity_status"] != "PASS":
        blocks.append(BLOCK_PACKAGE_MUTATED)

    recomputed_combined = integrity["recomputed"].get("combined_authorization_sha256")
    auth_digest = authorization.get("combined_authorization_sha256")
    if not auth_digest or auth_digest != recomputed_combined:
        blocks.append(BLOCK_DIGEST_MISMATCH)

    # --- 5. Expiry and replay ------------------------------------------------
    expires_at = _parse_ts(authorization.get("expires_at"))
    if authorization.get("authorization_status") == "GRANTED":
        if expires_at is None or now > expires_at:
            blocks.append(BLOCK_AUTHORIZATION_EXPIRED)

    if auth_id and auth_id in consumed:
        blocks.append(BLOCK_AUTHORIZATION_REPLAY)

    permitted_runs = int(authorization.get("permitted_run_count") or 0)
    if executed_run_count >= permitted_runs or permitted_runs != 1:
        blocks.append(BLOCK_RUN_COUNT_EXHAUSTED)

    # --- 6. Provider / model substitution ------------------------------------
    permitted_providers = list(authorization.get("permitted_providers") or [])
    permitted_models = dict(authorization.get("permitted_models") or {})

    for provider in requested_providers or []:
        if provider not in permitted_providers:
            blocks.append(BLOCK_PROVIDER_SUBSTITUTION)
            break

    for provider, model in (requested_models or {}).items():
        if provider not in permitted_models:
            blocks.append(BLOCK_PROVIDER_SUBSTITUTION)
            break
        if permitted_models[provider] != model:
            blocks.append(BLOCK_MODEL_SUBSTITUTION)
            break

    # --- 7. Cost caps ---------------------------------------------------------
    caps = authorization.get("maximum_cost_per_provider_usd") or {}
    total_cap = authorization.get("maximum_total_cost_usd")
    costs = estimated_costs_usd or {}

    for provider, cost in costs.items():
        cap = caps.get(provider) if isinstance(caps, dict) else caps
        if cap is None or float(cost) > float(cap):
            blocks.append(BLOCK_PROVIDER_COST_ABOVE_CAP)
            break

    if costs:
        if total_cap is None or sum(float(c) for c in costs.values()) > float(total_cap):
            blocks.append(BLOCK_TOTAL_COST_ABOVE_CAP)

    # --- 8. Scope locks: an authorization can never widen itself --------------
    if authorization.get("production_promotion_authorized") is True:
        blocks.append(BLOCK_PROMOTION_NOT_AUTHORIZED)
    if authorization.get("operator_hold_override_scope") != PERMITTED_OVERRIDE_SCOPE:
        blocks.append(BLOCK_OPERATOR_HOLD)

    # --- 9. Credentials: existence only, never value --------------------------
    matrix = credential_matrix() if credentials is None else credentials
    for provider in permitted_providers or ["openai", "anthropic", "xai"]:
        entry = matrix.get(provider, {})
        if entry.get("status") != "PRESENT_UNVERIFIED":
            blocks.append(BLOCK_MISSING_CREDENTIAL)
            break

    allowed = not blocks

    return {
        "allowed": allowed,
        "blocks": sorted(set(blocks)),
        "package_id": package_id,
        "authorization_id": auth_id,
        "classification": classification,
        "package_integrity": integrity["integrity_status"],
        # An authorization NEVER confers these. Hard-coded false, by construction.
        "promotion_eligible": False,
        "safe_to_execute_now": False,
        "frontier_council_quorum": False,
        "external_provider_calls": 0,
        "credential_readiness": {
            provider: entry.get("status") for provider, entry in matrix.items()
        },
    }


def assert_dispatch_allowed(**kwargs) -> dict:
    """Raise unless every gate passes. The only supported entry to live dispatch.

    Even on a clean pass this raises today: live dispatch remains hard-disabled
    until the founder grants authorization AND an operator explicitly lifts the
    hold. There is no code path in this repo that calls a provider.
    """
    decision = evaluate_launch(**kwargs)
    if not decision["allowed"]:
        raise PermissionError(
            "H1_LAUNCH_BLOCKED: " + ", ".join(decision["blocks"])
        )
    raise PermissionError(
        "FOUNDER_GATE_REQUIRED: live frontier dispatch is disabled in this build."
    )


def evidence_is_secret_free(evidence: Any, env_var_names: list[str] | None = None) -> bool:
    """Structural proof that no credential VALUE can enter retained evidence.

    We check the shape of the evidence, not the secret: any key whose name looks
    like a credential must carry only a reference name, never a value.
    """
    env_var_names = env_var_names or ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"]
    blob = json.dumps(evidence, sort_keys=True)

    forbidden_keys = ("api_key", "apikey", "secret", "token", "credential_value", "authorization_header")
    def walk(node: Any) -> bool:
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = str(key).lower()
                if lowered in forbidden_keys:
                    return False
                if lowered == "value_exposed" and value is not False:
                    return False
                if not walk(value):
                    return False
        elif isinstance(node, list):
            return all(walk(item) for item in node)
        return True

    if not walk(evidence):
        return False

    # A credential REFERENCE (the env var name) is allowed; a value is not.
    # Any bearer-token-shaped string is rejected outright.
    for marker in ("sk-", "xai-", "Bearer "):
        if marker in blob:
            return False
    return True
