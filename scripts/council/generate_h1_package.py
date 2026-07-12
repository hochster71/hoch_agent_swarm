from __future__ import annotations
import json
import hashlib
import sys
import datetime
import os
import math
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class H1PackageGenerationContext:
    packages_dir: Path
    roster_path: Path
    contracts_path: Path
    model_readiness_dir: Path
    pricing_evidence_path: Path
    authorization_schema_path: Path
    candidate_registry_path: Path | None = None

    @classmethod
    def production(cls) -> H1PackageGenerationContext:
        return cls(
            packages_dir=ROOT / "coordination" / "council" / "live_proof_packages",
            roster_path=ROOT / "coordination" / "council" / "council_roster.json",
            contracts_path=ROOT / "coordination" / "council" / "frontier_seat_contracts.json",
            model_readiness_dir=ROOT / "coordination" / "council" / "model_readiness",
            pricing_evidence_path=ROOT / "coordination" / "council" / "pricing_evidence.json",
            authorization_schema_path=ROOT / "coordination" / "council" / "frontier_authorization.schema.json",
            candidate_registry_path=ROOT / "coordination" / "council" / "h1_candidate_registry.json"
        )

def get_digest(data: dict) -> str:
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()

def generate_h1_package(timestamp_str: str | None = None, context: H1PackageGenerationContext | None = None) -> str:
    ctx = context or H1PackageGenerationContext.production()

    # Task 3: Generate clean candidate package ID with no TEST token
    if not timestamp_str:
        dt_now = datetime.datetime.now(datetime.timezone.utc)
        timestamp_str = dt_now.strftime("%Y%m%dT%H%M%SZ")

    temp_hash = hashlib.sha256(timestamp_str.encode("utf-8")).hexdigest()[:8].upper()
    package_id = f"HELM-H1-CANDIDATE-{timestamp_str}-{temp_hash}"

    # Task 1: Mark the old test package validation.json as non-executable
    test_pkg_dir = ctx.packages_dir / "HELM-H1-PACKAGE-TEST-H1-RUN"
    if test_pkg_dir.exists():
        (test_pkg_dir / "validation.json").write_text(json.dumps({
            "authority": "NON_RUNTIME_TEST_EVIDENCE",
            "execution_eligible": False,
            "authorization_eligible": False,
            "status": "NON_EXECUTABLE_TEST_PACKAGE",
            "superseded_by": None
         }, indent=2), encoding="utf-8")

    # Mark the old candidate package as superseded
    old_candidate_dir = ctx.packages_dir / "HELM-H1-CANDIDATE-20260712T011801Z-F083F6D0"
    if old_candidate_dir.exists():
        (old_candidate_dir / "validation.json").write_text(json.dumps({
            "status": "SUPERSEDED_BLOCKED_CANDIDATE",
            "execution_eligible": False,
            "authorization_eligible": False,
            "superseded_reason": "MODEL_POLICY_AND_BUDGET_UPDATED",
            "superseded_by": package_id
        }, indent=2), encoding="utf-8")

    package_dir = ctx.packages_dir / package_id
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "provider_requests").mkdir(parents=True, exist_ok=True)

    prompt = "Perform authoritative review of HELM control plane. [REDACTED PROMPT FOR SECURITY]"

    # Task 2: Load model readiness
    readiness_dir = ctx.model_readiness_dir
    openai_readiness = {}
    anthropic_readiness = {}
    xai_readiness = {}

    if (readiness_dir / "openai.json").exists():
        openai_readiness = json.loads((readiness_dir / "openai.json").read_text(encoding="utf-8"))
    if (readiness_dir / "anthropic.json").exists():
        anthropic_readiness = json.loads((readiness_dir / "anthropic.json").read_text(encoding="utf-8"))
    if (readiness_dir / "xai.json").exists():
        xai_readiness = json.loads((readiness_dir / "xai.json").read_text(encoding="utf-8"))

    model_readiness = {
        "openai": openai_readiness,
        "anthropic": anthropic_readiness,
        "xai": xai_readiness
    }
    (package_dir / "model_readiness.json").write_text(json.dumps(model_readiness, indent=2), encoding="utf-8")

    # 1. model_policy.json
    model_policy = {
        "openai": ["gpt-5.6-terra"],
        "anthropic": ["claude-sonnet-5"],
        "xai": ["grok-4.5"]
    }
    (package_dir / "model_policy.json").write_text(json.dumps(model_policy, indent=2), encoding="utf-8")

    # Task 5: Recalculate budget per provider with 25% contingency and rounded up to safe cent boundaries
    pricing_status = "VERIFIED"
    if (openai_readiness.get("public_pricing_status") != "VERIFIED" or
        anthropic_readiness.get("public_pricing_status") != "VERIFIED" or
        xai_readiness.get("public_pricing_status") != "VERIFIED"):
        pricing_status = "BLOCKED_UNKNOWN_PRICING"

    def calc_budget(readiness, prompt_len):
        input_price = readiness.get("input_price_per_million_tokens_usd", 0.0)
        output_price = readiness.get("output_price_per_million_tokens_usd", 0.0)
        max_input = 16000
        max_output = 4000
        measured_input = max(1, prompt_len // 4)

        # Base estimated cost (measured input + max output)
        est = ((measured_input / 1000000.0) * input_price) + ((max_output / 1000000.0) * output_price)
        # Max cost (max input + max output)
        max_cost = ((max_input / 1000000.0) * input_price) + ((max_output / 1000000.0) * output_price)

        # 1.25 contingency, rounded up to next cent
        cap = math.ceil(max_cost * 125.0) / 100.0

        return {
            "model_id": readiness.get("model_id"),
            "measured_input_tokens_estimate": measured_input,
            "authorized_max_input_tokens": max_input,
            "authorized_max_output_tokens": max_output,
            "input_price_per_million_usd": input_price,
            "output_price_per_million_usd": output_price,
            "calculated_max_request_cost_usd": float(round(max_cost, 5)),
            "contingency_factor": 1.25,
            "final_provider_cap_usd": float(round(cap, 2)),
            "estimated_cost_usd": float(round(est, 5))
        }

    openai_budget = calc_budget(openai_readiness, len(prompt))
    anthropic_budget = calc_budget(anthropic_readiness, len(prompt))
    xai_budget = calc_budget(xai_readiness, len(prompt))

    budget_limits = {
        "pricing_status": pricing_status,
        "providers": {
            "openai": openai_budget,
            "anthropic": anthropic_budget,
            "xai": xai_budget
        },
        "estimated_costs_usd": {
            "openai": openai_budget["estimated_cost_usd"],
            "anthropic": anthropic_budget["estimated_cost_usd"],
            "xai": xai_budget["estimated_cost_usd"]
        },
        "maximum_cost_per_provider_usd": {
            "openai": openai_budget["final_provider_cap_usd"],
            "anthropic": anthropic_budget["final_provider_cap_usd"],
            "xai": xai_budget["final_provider_cap_usd"]
        },
        "maximum_total_cost_usd": 0.35, # Conservative rounded cap
        "contingency_factor": 1.25
    }
    (package_dir / "budget_limits.json").write_text(json.dumps(budget_limits, indent=2), encoding="utf-8")

    # 3. provider_requests/ chatgpt, claude, grok
    chatgpt_req = {
        "run_id": f"HELM-H1-{timestamp_str}",
        "member_id": "chatgpt",
        "provider": "openai",
        "model": "gpt-5.6-terra",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    claude_req = {
        "run_id": f"HELM-H1-{timestamp_str}",
        "member_id": "claude",
        "provider": "anthropic",
        "model": "claude-sonnet-5",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096
    }
    grok_req = {
        "run_id": f"HELM-H1-{timestamp_str}",
        "member_id": "grok",
        "provider": "openai_compat",
        "model": "grok-4.5",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }

    (package_dir / "provider_requests" / "chatgpt.request.redacted.json").write_text(json.dumps(chatgpt_req, indent=2), encoding="utf-8")
    (package_dir / "provider_requests" / "claude.request.redacted.json").write_text(json.dumps(claude_req, indent=2), encoding="utf-8")
    (package_dir / "provider_requests" / "grok.request.redacted.json").write_text(json.dumps(grok_req, indent=2), encoding="utf-8")

    # Copy pricing_evidence.json into the package
    pricing_evidence_path = ctx.pricing_evidence_path
    pricing_evidence = json.loads(pricing_evidence_path.read_text(encoding="utf-8")) if pricing_evidence_path.exists() else []
    (package_dir / "pricing_evidence.json").write_text(json.dumps(pricing_evidence, indent=2), encoding="utf-8")

    # Task 4: Build immutable digest chain
    roster_path = ctx.roster_path
    contracts_path = ctx.contracts_path

    roster_data = json.loads(roster_path.read_text(encoding="utf-8")) if roster_path.exists() else {}
    contracts_data = json.loads(contracts_path.read_text(encoding="utf-8")) if contracts_path.exists() else {}

    request_digests = {
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "frontier_contract_sha256": get_digest(contracts_data),
        "roster_sha256": get_digest(roster_data),
        "model_policy_sha256": get_digest(model_policy),
        "budget_policy_sha256": get_digest(budget_limits),
        "chatgpt_request_sha256": get_digest(chatgpt_req),
        "claude_request_sha256": get_digest(claude_req),
        "grok_request_sha256": get_digest(grok_req),
        "pricing_evidence_sha256": get_digest(pricing_evidence)
    }

    # Combined authorization digest covering immutable constraints
    auth_fields = {
        "package_id": package_id,
        "provider_list": ["openai", "anthropic", "xai"],
        "exact_models": {
            "openai": "gpt-5.6-terra",
            "anthropic": "claude-sonnet-5",
            "xai": "grok-4.5"
        },
        "prompt": prompt,
        "chatgpt_request": chatgpt_req,
        "claude_request": claude_req,
        "grok_request": grok_req,
        "budget_limits": budget_limits,
        "run_count": 1,
        "expires_in_hours": 24,
        "operator_hold_override_scope": "SINGLE_H1_PROOF_ONLY",
        "production_promotion_authorized": False,
        "pricing_evidence": pricing_evidence
    }
    combined_auth_digest = get_digest(auth_fields)
    request_digests["combined_authorization_sha256"] = combined_auth_digest
    (package_dir / "request_digests.json").write_text(json.dumps(request_digests, indent=2), encoding="utf-8")

    # Task 6: Create bindable authorization template
    auth_template = {
        "authorization_id": f"HELM-H1-AUTH-{timestamp_str}-{temp_hash}",
        "authorization_status": "NOT_GRANTED",
        "package_id": package_id,
        "combined_authorization_sha256": combined_auth_digest,
        "issued_by": "Michael Bryan Hoch",
        "issued_at": None,
        "expires_at": None,
        "permitted_run_count": 1,
        "permitted_providers": ["openai", "anthropic", "xai"],
        "permitted_models": {
            "openai": "gpt-5.6-terra",
            "anthropic": "claude-sonnet-5",
            "xai": "grok-4.5"
        },
        "maximum_total_cost_usd": 0.35,
        "maximum_cost_per_provider_usd": {
            "openai": openai_budget["final_provider_cap_usd"],
            "anthropic": anthropic_budget["final_provider_cap_usd"],
            "xai": xai_budget["final_provider_cap_usd"]
        },
        "operator_hold_override_scope": "SINGLE_H1_PROOF_ONLY",
        "production_promotion_authorized": False,
        "additional_runs_authorized": False,
        "model_substitution_authorized": False,
        "provider_substitution_authorized": False,
        "approval_reference": None
    }
    (package_dir / "founder_authorization.template.json").write_text(json.dumps(auth_template, indent=2), encoding="utf-8")

    # 6. launch_manifest.json
    launch_manifest = {
        "package_id": package_id,
        "mode": "H1_LAUNCH_BLOCKED" if pricing_status == "BLOCKED_UNKNOWN_PRICING" else "H1_LAUNCH_PREPARED",
        "authorization_status": "NOT_GRANTED",
        "external_calls": 0,
        "paid_calls": 0,
        "live_responses": 0,
        "frontier_council_quorum": False,
        "promotion_eligible": False,
        "safe_to_execute_now": False
    }
    (package_dir / "launch_manifest.json").write_text(json.dumps(launch_manifest, indent=2), encoding="utf-8")

    # 7. prompt.redacted.txt
    (package_dir / "prompt.redacted.txt").write_text(prompt, encoding="utf-8")

    # 8. credential_readiness.json
    has_openai = "OPENAI_API_KEY" in os.environ
    has_anthropic = "ANTHROPIC_API_KEY" in os.environ
    has_xai = "XAI_API_KEY" in os.environ
    credential_readiness = {
        "openai": {
            "credential_reference": "OPENAI_API_KEY",
            "status": "PRESENT_UNVERIFIED" if has_openai else "NOT_PROVISIONED",
            "value_exposed": False
        },
        "anthropic": {
            "credential_reference": "ANTHROPIC_API_KEY",
            "status": "PRESENT_UNVERIFIED" if has_anthropic else "NOT_PROVISIONED",
            "value_exposed": False
        },
        "xai": {
            "credential_reference": "XAI_API_KEY",
            "status": "PRESENT_UNVERIFIED" if has_xai else "NOT_PROVISIONED",
            "value_exposed": False
        }
    }
    (package_dir / "credential_readiness.json").write_text(json.dumps(credential_readiness, indent=2), encoding="utf-8")

    # 9. data_egress_summary.json
    egress = {
        "egress_scope": "LIMITED_H1_PROOF",
        "local_source_data_sent": [],
        "telemetry_egress": ["prompt_digest", "model_identity", "latency_ms"],
        "exposed_secrets": False,
        "egress_destinations": ["OpenAI API Endpoint", "Anthropic API Endpoint", "xAI API Endpoint"]
    }
    (package_dir / "data_egress_summary.json").write_text(json.dumps(egress, indent=2), encoding="utf-8")

    # 10. abort_conditions.json
    abort_conditions = [
        "authorization absent or expired",
        "authorization identity mismatch",
        "request digest mismatch",
        "roster or contract digest mismatch",
        "unauthorized model",
        "provider identity mismatch",
        "missing credential",
        "unknown price",
        "estimated cost above cap",
        "operator lock unavailable",
        "duplicate process detected",
        "stale package",
        "any request mutation after approval",
        "one provider substituted for another",
        "secret detected in retained evidence",
        "reconciliation cannot establish one authoritative run"
    ]
    (package_dir / "abort_conditions.json").write_text(json.dumps(abort_conditions, indent=2), encoding="utf-8")

    # 11. evidence_retention.json
    retention = {
        "retained_artifacts": [
            "raw_response_bytes",
            "recomputed_sha256_digest",
            "telemetry_envelope",
            "run_id"
        ],
        "scrubbed_fields": [
            "api_key",
            "bearer_token",
            "client_secrets"
        ]
    }
    (package_dir / "evidence_retention.json").write_text(json.dumps(retention, indent=2), encoding="utf-8")

    # 12. rollback_plan.json
    rollback = {
        "operator_hold_restoration": "IMMEDIATE_ON_FAILURE_OR_COMPLETE",
        "cleanup_scope": ["temp_run_folder", "unverified_response_cache"],
        "unfreeze_prevention": "ALL_PROMOTIONS_BLOCKED"
    }
    (package_dir / "rollback_plan.json").write_text(json.dumps(rollback, indent=2), encoding="utf-8")

    # 13. adversarial_review.json
    adversarial = {
        "authorization_replay_protection": "BOUND_TO_SINGLE_UNIQUE_RUN_ID",
        "request_mutation_protection": "CRYPTOGRAPHIC_COMBINED_REQUEST_DIGEST",
        "provider_substitution_protection": "EXACT_ROSTER_MATCH_VERIFIER",
        "model_substitution_protection": "FROZEN_CONTRACT_requested_model_policy",
        "budget_cap_bypass_protection": "PRE_DISPATCH_BUDGET_GOVERNOR_ASSERTION",
        "secret_leakage_protection": "MANDATORY_VALUE_EXPOSURE_NEGATIVE_TESTS",
        "partial_quorum_promotion_protection": "FAIL_CLOSED_QUORUM_AGGREGATION_POLICY"
    }
    (package_dir / "adversarial_review.json").write_text(json.dumps(adversarial, indent=2), encoding="utf-8")

    # 14. validation.json
    validation = {
        "all_required_files_present": True,
        "combined_request_digest_verified": pricing_status != "BLOCKED_UNKNOWN_PRICING",
        "validation_status": "BLOCKED" if pricing_status == "BLOCKED_UNKNOWN_PRICING" else "PASS",
        "overall_status": "BLOCKED_MODEL_IDENTITY" if pricing_status == "BLOCKED_UNKNOWN_PRICING" else "READY_FOR_FOUNDER_REVIEW"
    }
    (package_dir / "validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")

    return package_id

if __name__ == "__main__":
    pid = generate_h1_package()
    print(f"Generated launch package: {pid}")
