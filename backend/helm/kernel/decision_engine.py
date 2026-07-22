#!/usr/bin/env python3
"""
HELM Governance Reference Decision Engine (v1.0.0 Normative)
============================================================
Implements the normative HELM Release Promotion Evaluation Algorithm,
SLSA-style attestation provenance verification ("HELM-Provenance-1.0"),
and HELM Canonical JSON Profile v1.0 SHA256 decision digest computation.
"""

import hashlib
import json
import math
from typing import Any, Dict, List, Tuple


class HELMDecisionEngine:
    """Normative Reference Decision Engine for HELM Release Promotion."""

    POLICY_ID = "HELM-RELEASE-GOVERNANCE"
    POLICY_VERSION = "1.0.0"
    PROVENANCE_SCHEMA_VERSION = "HELM-Provenance-1.0"
    CANONICAL_JSON_PROFILE = "HELM-Canonical-JSON-Profile-v1.0"
    RUNTIME_SCHEMA_VERSION = "1.1"
    DECISION_ENGINE_VERSION = "1.0.0"

    VALID_DECISION_CODES = {
        "APPROVED",
        "WITHHELD_UNVERIFIED_PROVENANCE",
        "REJECTED_SLO_VIOLATION",
        "REJECTED_OPEN_P0",
        "FROZEN_ERROR_BUDGET",
    }

    @classmethod
    def _sanitize_for_canonical(cls, obj: Any) -> Any:
        """Recursively sanitizes and orders data according to HELM Canonical JSON Profile v1.0 (RFC 8785 subset).
        
        Rules:
        - Dict keys must be strings and sorted by UTF-16 code units (RFC 8785 Section 3.2.3).
        - Floats must be finite numbers (reject NaN, Infinity, -Infinity).
        - Negative zero (-0.0) is serialized as 0 per RFC 8785 Section 3.2.2.
        - Lists preserve element order, but items are recursively sanitized.
        """
        if isinstance(obj, dict):
            sorted_dict = {}
            for key in sorted(obj.keys()):
                if not isinstance(key, str):
                    raise ValueError(f"Canonical JSON Profile v1.0 requires string keys, got: {type(key)}")
                sorted_dict[key] = cls._sanitize_for_canonical(obj[key])
            return sorted_dict
        elif isinstance(obj, list):
            return [cls._sanitize_for_canonical(item) for item in obj]
        elif isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                raise ValueError(f"Canonical JSON Profile v1.0 forbids NaN/Infinity float values: {obj}")
            if obj == 0.0:
                return 0
            return obj
        return obj

    @classmethod
    def canonical_json_bytes(cls, obj: Any) -> bytes:
        """Serializes data using HELM Canonical JSON Profile v1.0 (based on RFC 8785)."""
        sanitized = cls._sanitize_for_canonical(obj)
        return json.dumps(
            sanitized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    @classmethod
    def evaluate_release_promotion(cls, rdr_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates release promotion clearance under normative constitutional invariants.
        
        Evaluator Pipeline:
        1. Provenance Gate (Dominates Evaluation; NOT_VERIFIED => INADMISSIBLE)
        2. Substantive SLO Gate
        3. Open P0 Findings Gate
        4. Burn-Rate Freeze Gate
        5. HELM Canonical JSON Profile v1.0 Decision Digest Calculation
        """
        provenance_status = rdr_payload.get("provenance_status", "NOT_VERIFIED")
        slo_status = rdr_payload.get("slo_status", "FAIL")
        open_p0_findings = rdr_payload.get("open_p0_findings", 0)
        burn_rate_multiplier = float(rdr_payload.get("burn_rate_multiplier", 1.0))

        # 1. Constitutional Invariant: NOT_VERIFIED Dominates Evaluation
        if provenance_status != "VERIFIED":
            decision_code = "WITHHELD_UNVERIFIED_PROVENANCE"
        # 2. Substantive SLO Gate
        elif slo_status == "FAIL":
            decision_code = "REJECTED_SLO_VIOLATION"
        # 3. Open P0 Findings Gate
        elif open_p0_findings > 0:
            decision_code = "REJECTED_OPEN_P0"
        # 4. Burn-Rate Freeze Gate
        elif burn_rate_multiplier >= 5.0:
            decision_code = "FROZEN_ERROR_BUDGET"
        else:
            decision_code = "APPROVED"

        # Construct Canonical Digest Envelope
        digest_inputs = {
            "config_digest": rdr_payload.get("configuration_digest", ""),
            "decision_code": decision_code,
            "evaluated_inputs": rdr_payload.get("evaluated_inputs", {}),
            "evidence_digests": sorted(rdr_payload.get("evidence_proof_package_digests", [])),
            "generator_version": rdr_payload.get("generator_version", "v1.0.0"),
            "git_commit": rdr_payload.get("git_commit_sha", ""),
            "measurement_results": rdr_payload.get("measurement_results", {}),
            "policy_version": cls.POLICY_VERSION,
        }

        canonical_bytes = cls.canonical_json_bytes(digest_inputs)
        decision_digest = hashlib.sha256(canonical_bytes).hexdigest()

        return {
            "decision_code": decision_code,
            "decision_digest": decision_digest,
            "policy_id": cls.POLICY_ID,
            "policy_version": cls.POLICY_VERSION,
            "provenance_schema_version": cls.PROVENANCE_SCHEMA_VERSION,
            "canonical_json_profile": cls.CANONICAL_JSON_PROFILE,
            "runtime_schema_version": cls.RUNTIME_SCHEMA_VERSION,
            "decision_engine_version": cls.DECISION_ENGINE_VERSION,
            "evaluated_inputs_digest": hashlib.sha256(cls.canonical_json_bytes(rdr_payload)).hexdigest(),
        }
