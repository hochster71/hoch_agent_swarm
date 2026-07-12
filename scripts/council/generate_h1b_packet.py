"""HELM H1B — founder decision packet generator (REVIEW-ONLY).

Writes three evidence artifacts and NOTHING else:
  coordination/council/h1b_candidate_reconciliation.json
  coordination/council/h1b_credential_matrix.json
  coordination/council/h1b_founder_decision.json

It does not grant authorization, does not provision credentials, does not lift
the operator hold, and makes zero external calls. Running it twice is safe.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.council.h1b_candidate_registry import (  # noqa: E402
    ELIGIBLE,
    NON_EXECUTABLE_TEST,
    PACKAGES_DIR,
    SUPERSEDED,
    credential_matrix,
    credential_readiness_summary,
    reconcile_candidates,
    recompute_package_integrity,
)

COUNCIL_DIR = ROOT / "coordination" / "council"
RECONCILIATION_PATH = COUNCIL_DIR / "h1b_candidate_reconciliation.json"
CREDENTIAL_PATH = COUNCIL_DIR / "h1b_credential_matrix.json"
DECISION_PATH = COUNCIL_DIR / "h1b_founder_decision.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def build_decision_statement(template: dict, digest: str, budget: dict) -> str:
    caps = template.get("maximum_cost_per_provider_usd", {})
    models = template.get("permitted_models", {})
    return "\n".join(
        [
            "AUTHORIZE HELM H1 SINGLE-RUN FRONTIER PROOF",
            f"Authorization ID: {template.get('authorization_id')}",
            f"Package ID: {template.get('package_id')}",
            f"Combined authorization SHA-256: {digest}",
            "Permitted providers and models:",
            f"- OpenAI: {models.get('openai')}",
            f"- Anthropic: {models.get('anthropic')}",
            f"- xAI: {models.get('xai')}",
            "Permitted run count: 1",
            "Maximum spend:",
            f"- OpenAI: ${caps.get('openai')}",
            f"- Anthropic: ${caps.get('anthropic')}",
            f"- xAI: ${caps.get('xai')}",
            f"- Aggregate: ${template.get('maximum_total_cost_usd')}",
            "Issued at: <filled only on founder approval>",
            "Expires at: <filled only on founder approval>",
            "Operator-hold override: SINGLE_H1_PROOF_ONLY",
            "Production promotion: NOT AUTHORIZED",
            "Additional runs: NOT AUTHORIZED",
            "Provider substitution: NOT AUTHORIZED",
            "Model substitution: NOT AUTHORIZED",
            "Approval reference: <founder-supplied>",
        ]
    )


def generate(write: bool = True) -> dict:
    reconciliation = reconcile_candidates(PACKAGES_DIR)
    matrix = credential_matrix()
    summary = credential_readiness_summary(matrix)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    reconciliation_artifact = {
        "schema": "HELM_H1B_CANDIDATE_RECONCILIATION_v1",
        "generated_at": now,
        "status": reconciliation["status"],
        "reason": reconciliation["reason"],
        "active_candidate": reconciliation["active_candidate"],
        "classification_vocabulary": [ELIGIBLE, SUPERSEDED, NON_EXECUTABLE_TEST],
        "retention_policy": "ALL_PRIOR_CANDIDATES_RETAINED_NEVER_DELETED",
        "packages": reconciliation["packages"],
    }

    active = reconciliation["active_candidate"]
    if not active:
        decision = {
            "schema": "HELM_H1B_FOUNDER_DECISION_v1",
            "generated_at": now,
            "h1_candidate": "BLOCKED",
            "package_integrity": "FAIL",
            "credential_readiness": summary,
            "authorization_status": "NOT_GRANTED",
            "external_provider_calls": 0,
            "frontier_council_quorum": False,
            "promotion_eligible": False,
            "safe_to_execute_now": False,
            "final_status": reconciliation["status"],
        }
    else:
        pkg = PACKAGES_DIR / active
        template = _load(pkg / "founder_authorization.template.json") or {}
        budget = _load(pkg / "budget_limits.json") or {}
        digests = _load(pkg / "request_digests.json") or {}
        integrity = reconciliation["integrity"]
        combined = digests.get("combined_authorization_sha256")

        decision = {
            "schema": "HELM_H1B_FOUNDER_DECISION_v1",
            "generated_at": now,
            "h1_candidate": "READY_FOR_FOUNDER_DECISION",
            "package_integrity": "PASS" if integrity["integrity_status"] == "PASS" else "FAIL",
            "integrity_recomputation": {
                "status": integrity["integrity_status"],
                "fields_verified": sorted(integrity["recomputed"].keys()),
                "mismatches": integrity["mismatches"],
            },
            # --- what the founder is being asked to authorize -----------------
            "authorization_id": template.get("authorization_id"),
            "package_id": active,
            "combined_authorization_sha256": combined,
            "permitted_providers": template.get("permitted_providers"),
            "permitted_models": template.get("permitted_models"),
            "permitted_run_count": 1,
            "maximum_cost_per_provider_usd": template.get("maximum_cost_per_provider_usd"),
            "maximum_total_cost_usd": template.get("maximum_total_cost_usd"),
            "pricing_status": budget.get("pricing_status"),
            # --- unset until the founder signs. Never auto-filled. ------------
            "issued_at": None,
            "expires_at": None,
            "approval_reference": None,
            "authorization_status": "NOT_GRANTED",
            # --- hard scope locks ---------------------------------------------
            "operator_hold_override_scope": "SINGLE_H1_PROOF_ONLY",
            "production_promotion_authorized": False,
            "additional_runs_authorized": False,
            "provider_substitution_authorized": False,
            "model_substitution_authorized": False,
            # --- truthful state ------------------------------------------------
            "credential_readiness": summary,
            "credential_matrix": matrix,
            "external_provider_calls": 0,
            "paid_provider_calls": 0,
            "frontier_council_quorum": False,
            "promotion_eligible": False,
            "safe_to_execute_now": False,
            "operator_hold_state": "ACTIVE",
            "superseded_candidates": [
                p["package_id"]
                for p in reconciliation["packages"]
                if p["classification"] == SUPERSEDED
            ],
            "non_executable_test_packages": [
                p["package_id"]
                for p in reconciliation["packages"]
                if p["classification"] == NON_EXECUTABLE_TEST
            ],
            "decision_statement": build_decision_statement(template, combined, budget),
            "final_status": "H1B_FOUNDER_DECISION_PACKET_READY",
        }

    if write:
        COUNCIL_DIR.mkdir(parents=True, exist_ok=True)
        RECONCILIATION_PATH.write_text(
            json.dumps(reconciliation_artifact, indent=2) + "\n", encoding="utf-8"
        )
        CREDENTIAL_PATH.write_text(
            json.dumps(
                {
                    "schema": "HELM_H1B_CREDENTIAL_MATRIX_v1",
                    "generated_at": now,
                    "policy": "EXISTENCE_CHECK_ONLY_VALUE_NEVER_READ",
                    "credential_readiness": summary,
                    "providers": matrix,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        DECISION_PATH.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")

        # Stamp the classification back onto each retained package (never delete).
        for entry in reconciliation["packages"]:
            vpath = PACKAGES_DIR / entry["package_id"] / "validation.json"
            existing = _load(vpath) or {}
            existing.update(
                {
                    "status": entry["classification"],
                    "execution_eligible": False,
                    "authorization_eligible": bool(entry["authorization_eligible"]),
                    "classification_reason": entry["reason"],
                    "reconciled_at": now,
                }
            )
            if entry.get("superseded_by"):
                existing["superseded_by"] = entry["superseded_by"]
            vpath.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    return decision


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(generate(write="--dry-run" not in sys.argv), indent=2))
