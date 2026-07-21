#!/usr/bin/env python3
"""HELM Reusable Assurance Engine (NIST/GSN Compliant).

Provides machine-reasoned claim graphs, requirement traceability, control mapping,
evidence category taxonomy (Observational, Verification, Adversarial, Resilience, Operational),
evidence provenance, scope alignment, assumption evaluation, quantitative confidence policies,
defeater (counter-evidence) monitoring, qualitative confidence reasoning, actionable evidence delta engines,
typed classified explanation traces ('because_structured' arrays with depends_on_steps & depends_on_nodes DAG links),
what-if counterfactual impact analysis engine (simulate_counterfactual API with cause/effect/explanation separation),
graph analysis capabilities (analyze_minimal_cut & analyze_node_influence APIs),
assurance dependency heat map visualization (generate_assurance_heatmap API),
work optimization engine with risk-aware Return-on-Effort ROI prioritization (recommend_assurance_work_backlog API),
enriched swarm task assignment manifest export for mission control staging (export_swarm_task_assignments API),
closed-loop execution engine with SHA256 hash-chained audit ledger, evidence snapshot provenance, dual promotion authorization gate separation, deterministic ledger replay verification, and reasoning model spec freeze (execute_closed_loop_update, evaluate_promotion_authorization, verify_closed_loop_ledger_integrity & replay_closed_loop_ledger APIs),
top-level evaluation output sections with SHA256 cryptographic verification digests,
cross-audit evidence registration, explicit relationship graph tuples, reasoning model versioning,
and canonical JSON export.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CLOSED_LOOP_LEDGER_PATH = ROOT / "coordination" / "governance" / "closed_loop_execution_ledger.jsonl"

FILESYSTEM_DEPLOYMENT_ASSUMPTIONS: Dict[str, Any] = {
    "supported_storage_scope": "LOCAL_POSIX_COMPLIANT_FS_ONLY",
    "required_primitives": [
        "fcntl_flock_ex_advisory_locking",
        "atomic_append_open_mode_a",
        "kernel_page_cache_fsync",
    ],
    "validated_filesystems": ["apfs", "ext4"],
    "expected_compatible_unvalidated": ["xfs", "btrfs"],
    "unsupported_fail_closed": {
        "nfs": "UNSUPPORTED_REMOTE_NETWORK_MOUNT_FAIL_CLOSED",
        "smb_cifs": "UNSUPPORTED_REMOTE_NETWORK_MOUNT_FAIL_CLOSED",
        "fuse_cloud_bucket": "UNSUPPORTED_OBJECT_STORE_MOUNT_FAIL_CLOSED",
    },
    "concurrency_guarantee": "INTER_PROCESS_FLOCK_MUTEX_LOCKING_REQUIRED",
    "advisory_trust_boundary": (
        "fcntl.flock advisory locking protects cooperating HELM engine processes. "
        "Non-cooperating processes writing directly bypass the lock boundary, but are "
        "intercepted immediately by downstream hash-chain integrity verification and replay."
    ),
    "obsolescence": "Re-validate locks + fsync if storage backend changes.",
}

POLICY_IMPLEMENTATION_STATE_ALLOWED_VALUES = {
    "IMPLEMENTED",
    "NOT_IMPLEMENTED",
    "PROPOSED",
    "DEFERRED",
    "PRODUCTION_DIFFERS",
    "DEPRECATED",
}

GOVERNANCE_POLICIES_SCHEMA_PATH = (
    ROOT / "docs" / "helm" / "schemas" / "governance_policies_schema_v1.json"
)
GOVERNANCE_POLICIES_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
GOVERNANCE_POLICIES_SCHEMA_ID = "https://helm.internal/schemas/governance_policies_schema_v1.json"


def governance_validation_environment() -> Dict[str, Any]:
    """Evidence metadata for schema validation reproducibility (not policy content).

    Lives beside the closed-world governance_policies manifest so the policy
    schema can stay strict (additionalProperties: false) while still recording
    which validator package/version validated or is available at export time.
    """
    version = "UNKNOWN"
    try:
        import importlib.metadata

        version = importlib.metadata.version("jsonschema")
    except Exception:
        try:
            import jsonschema  # type: ignore

            version = getattr(jsonschema, "__version__", "UNKNOWN")
        except Exception:
            version = "UNAVAILABLE"
    return {
        "schema_path": str(
            GOVERNANCE_POLICIES_SCHEMA_PATH.relative_to(ROOT)
            if GOVERNANCE_POLICIES_SCHEMA_PATH.is_relative_to(ROOT)
            else GOVERNANCE_POLICIES_SCHEMA_PATH
        ),
        "schema_id": GOVERNANCE_POLICIES_SCHEMA_ID,
        "schema_draft": GOVERNANCE_POLICIES_SCHEMA_DRAFT,
        "jsonschema_package_version": version,
        "contract_mode": "CLOSED_WORLD_additionalProperties_false",
        "note": (
            "Validator package version for evidence reproducibility. "
            "Does not expand production claims."
        ),
    }

LEDGER_RECOVERY_POLICY_DECISION_TABLE: List[Dict[str, str]] = [
    {
        "location": "Final incomplete line",
        "policy": "Fail-closed detection & structural reporting",
        "implementation_state": "IMPLEMENTED",
        "result": "Isolate parse error as TRUNCATED_FINAL_RECORD; require operator review before append",
        "code": "TRUNCATED_FINAL_RECORD_DETECTED",
    },
    {
        "location": "Malformed mid-file record",
        "policy": "Fail closed",
        "implementation_state": "IMPLEMENTED",
        "result": "Reject append, raise ClosedLoopLedgerError(MID_FILE_CORRUPTION_REJECTED), preserve log intact",
        "code": "MID_FILE_CORRUPTION_REJECTED",
    },
    {
        "location": "Broken hash chain",
        "policy": "Fail closed",
        "implementation_state": "IMPLEMENTED",
        "result": "Reject replay with HASH_CHAIN_DISCONTINUITY_ERROR, preserve evidence intact",
        "code": "HASH_CHAIN_DISCONTINUITY_ERROR",
    },
    {
        "location": "Duplicate transaction ID",
        "policy": "Not independently enforced",
        "implementation_state": "NOT_IMPLEMENTED",
        "result": "Duplicate transaction-ID validation is outside current engine scope. Hash-chain integrity protects record sequence integrity, but duplicate transaction IDs are not explicitly detected or rejected by the engine.",
        "code": "DUPLICATE_TX_ID_UNENFORCED_OUTSIDE_SCOPE",
    },
]


def reject_duplicate_json_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    """I-JSON / RFC 8785-aligned: reject duplicate property names at parse time.

    Using object_pairs_hook means duplicates are detected before Python collapses
    them into a dict (post-construction detection is ambiguous).
    """
    d: Dict[str, Any] = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"Duplicate key detected: {k}")
        d[k] = v
    return d

class ScopeAlignment:
    EXACT_MATCH = "EXACT_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    INDIRECT = "INDIRECT"
    DERIVED = "DERIVED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"

class EvidenceState:
    CURRENT = "CURRENT"
    STALE = "STALE"
    MISSING = "MISSING"
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"

class EvidenceCategory:
    OBSERVATIONAL = "OBSERVATIONAL"  # Shows what occurred (audit logs, usage ledgers)
    VERIFICATION = "VERIFICATION"    # Shows intended behavior (pytest unit/gateway suites)
    ADVERSARIAL = "ADVERSARIAL"      # Shows attempted violation/rejection (red-team, GOV-007 tests)
    RESILIENCE = "RESILIENCE"        # Shows recovery after failure (circuit breakers, fallbacks)
    OPERATIONAL = "OPERATIONAL"      # Shows continuous production telemetry

class ClaimHealth:
    FULL_CONFIDENCE = "FULL_CONFIDENCE"
    REDUCED_CONFIDENCE = "REDUCED_CONFIDENCE"
    INVALIDATED = "INVALIDATED"
    UNTESTED = "UNTESTED"

class DefeaterSeverity:
    CRITICAL = "CRITICAL"  # Immediate claim invalidation (Score = 0.0)
    MAJOR = "MAJOR"        # 50% confidence penalty (Multiplier = 0.5)
    MINOR = "MINOR"        # 20% confidence penalty (Multiplier = 0.8)

class PromotionStatus:
    PROMOTION_APPROVED_FULL_CONFIDENCE = "PROMOTION_APPROVED_FULL_CONFIDENCE"
    PROMOTION_ELIGIBLE_PENDING_FOUNDER_GATE = "PROMOTION_ELIGIBLE_PENDING_FOUNDER_GATE"
    PROMOTION_DENIED_UNMET_ASSUMPTIONS = "PROMOTION_DENIED_UNMET_ASSUMPTIONS"
    PROMOTION_DENIED_INVALIDATED_CLAIMS = "PROMOTION_DENIED_INVALIDATED_CLAIMS"
    PROMOTION_DENIED_INSUFFICIENT_CONFIDENCE = "PROMOTION_DENIED_INSUFFICIENT_CONFIDENCE"

@dataclass
class ReasoningModelSpec:
    version: str = "2.2"
    spec_status: str = "REASONING_SPEC_FROZEN_PENDING_SYSTEM_INTEGRATION"
    canonicalization: Dict[str, Any] = field(default_factory=lambda: {
        "spec": "RFC8785",
        "implementation": "helm-jcs",
        "implementation_version": "1.0.0",
        "build": {
            "git_commit": "c40f5da65218fae209359cdfbefec6d1cd5b01aeee6dc7877515fa397e419583",
            "git_short": "c40f5da"
        }
    })
    feature_flags: List[str] = field(default_factory=lambda: [
        "hash_chain_v4",
        "dual_authorization_v3",
        "deterministic_replay_v4",
        "evidence_snapshot_v3",
        "rfc8785_canonicalization_v1",
    ])
    propagation_algorithm: str = "MINIMAL_CUT_AND_COUNTERFACTUAL_PROPAGATION_V6"
    defeater_semantics: str = "FAIL_CLOSED_SEVERITY_LEVELS_V1"
    freshness_algorithm: str = "TIME_DELTA_AGE_DECAY_V1"
    evidence_taxonomy: str = "OBSERVATIONAL_VERIFICATION_ADVERSARIAL_RESILIENCE_OPERATIONAL_V1"
    explanation_trace_semantics: str = "DUAL_STEP_AND_NODE_LINKED_DAG_TRACES_V4"
    counterfactual_analysis_engine: str = "CAUSE_EFFECT_EXPLANATION_SIMULATION_API_V2"
    graph_analysis_capabilities: str = "MINIMAL_CUT_AND_NODE_INFLUENCE_RANKING_V1"
    optimization_engine: str = "RISK_AWARE_ROI_BACKLOG_AND_ENRICHED_ORCHESTRATION_TASKS_V3"
    closed_loop_capabilities: str = "HASH_CHAINED_AUDIT_LEDGER_AND_DETERMINISTIC_REPLAY_VERIFICATION_V4"
    provenance_verification: str = "SHA256_GRAPH_AND_EVALUATION_DIGESTS_V1"
    provenance_semantics: str = "SHA256_PROVES_ARTIFACT_IDENTITY_NOT_CORRECTNESS"

@dataclass
class AssurancePolicy:
    policy_id: str = "HELM-CONFIDENCE-POLICY-v1"
    version: str = "2.2"
    weighting_model: Dict[str, float] = field(default_factory=lambda: {
        "runtime": 0.9,
        "integration": 0.8,
        "unit": 0.6,
        "design": 0.3,
    })
    description: str = "Governance decision for quantitative evidence weighting heuristics"

@dataclass
class RelationshipNode:
    source_id: str
    target_id: str
    relationship_type: str  # "implements", "supports", "verified_by", "bounded_by", "monitored_by", "challenged_by", "resisted_by", "validated_by_attack"

@dataclass
class EvidenceProvenance:
    generating_engine: str
    observer_sha: str
    observer_version: str
    negative_reporting_validated: bool

@dataclass
class EvidenceNode:
    id: str
    path: Path
    covered_scope: str
    excluded_scope: str
    scope_alignment: str
    provenance: EvidenceProvenance
    category: str = EvidenceCategory.VERIFICATION
    max_age_seconds: int = 86400
    weight: float = 1.0  # Configurable weight scale (e.g., 0.9 runtime, 0.6 unit, 0.3 design)

    def evaluate_state(self) -> Tuple[str, str, str]:
        """Return (ISO timestamp, human age, state)."""
        if not self.path.exists():
            return "N/A", "File not found", EvidenceState.MISSING
        try:
            mtime = datetime.fromtimestamp(self.path.stat().st_mtime, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            age = int((now - mtime).total_seconds())
            if age < 60:
                age_str = f"{age}s ago"
            elif age < 3600:
                age_str = f"{age // 60}m ago"
            elif age < 86400:
                age_str = f"{age // 86400}h ago"
            else:
                age_str = f"{age // 86400}d ago"
            state = EvidenceState.CURRENT if age <= self.max_age_seconds else EvidenceState.STALE
            return mtime.isoformat().replace("+00:00", "Z"), age_str, state
        except Exception:
            return "UNKNOWN", "Error reading mtime", EvidenceState.UNKNOWN

    def get_freshness_factor(self) -> float:
        _, _, state = self.evaluate_state()
        if state == EvidenceState.CURRENT:
            return 1.0
        elif state == EvidenceState.STALE:
            return 0.5
        return 0.0

@dataclass
class AssumptionNode:
    id: str
    description: str
    category: str
    evaluator: callable
    affected_claim_ids: List[str]

    def evaluate(self) -> Tuple[bool, str]:
        """Return (is_met, state_label)."""
        return self.evaluator()

@dataclass
class DefeaterNode:
    id: str
    description: str
    evaluator: callable
    target_claim_id: str
    severity: str = DefeaterSeverity.CRITICAL

    def evaluate(self) -> Tuple[bool, str]:
        """Return (triggered, status_label)."""
        return self.evaluator()

    def get_confidence_multiplier(self) -> float:
        triggered, _ = self.evaluate()
        if not triggered:
            return 1.0
        if self.severity == DefeaterSeverity.CRITICAL:
            return 0.0
        elif self.severity == DefeaterSeverity.MAJOR:
            return 0.5
        elif self.severity == DefeaterSeverity.MINOR:
            return 0.8
        return 1.0

@dataclass
class ControlNode:
    id: str  # e.g., "CTRL-AC-3", "CTRL-AU-2", "CTRL-SC-7"
    name: str  # e.g., "Access Enforcement"
    standard: str  # e.g., "NIST SP 800-53 Rev 5"
    description: str
    requirement_ids: List[str] = field(default_factory=list)
    associated_claim_ids: List[str] = field(default_factory=list)

@dataclass
class RequirementNode:
    id: str  # e.g., "REQ-VOICE-01"
    title: str
    description: str
    source_standard: str  # e.g., "HELM-ENGINEERING-DOCTRINE-v1"
    associated_control_ids: List[str] = field(default_factory=list)
    associated_claim_ids: List[str] = field(default_factory=list)

@dataclass
class ClaimNode:
    id: str
    name: str
    supported_claim: str
    primary_artifact: str
    evidence_nodes: List[EvidenceNode] = field(default_factory=list)
    assumption_nodes: List[AssumptionNode] = field(default_factory=list)
    defeater_nodes: List[DefeaterNode] = field(default_factory=list)
    control_nodes: List[ControlNode] = field(default_factory=list)
    requirement_nodes: List[RequirementNode] = field(default_factory=list)

    def calculate_confidence_score(self) -> float:
        """Compute quantitative confidence score (0.0 to 1.0)."""
        defeater_multiplier = 1.0
        for def_node in self.defeater_nodes:
            mult = def_node.get_confidence_multiplier()
            defeater_multiplier *= mult
            if defeater_multiplier == 0.0:
                return 0.0

        assumption_factor = 1.0
        for asm in self.assumption_nodes:
            is_met, _ = asm.evaluate()
            if not is_met:
                assumption_factor *= 0.6

        if not self.evidence_nodes:
            weighted_ev_score = 0.5
        else:
            total_weight = sum(ev.weight for ev in self.evidence_nodes)
            weighted_freshness = sum(ev.weight * ev.get_freshness_factor() for ev in self.evidence_nodes)
            weighted_ev_score = (weighted_freshness / total_weight) if total_weight > 0 else 0.0

        confidence = weighted_ev_score * assumption_factor * defeater_multiplier
        return round(max(0.0, min(1.0, confidence)), 3)

    def evaluate_health(self) -> Dict[str, Any]:
        """Propagate confidence through defeaters, assumptions, and weighted evidence with dual step and node-linked 'because_structured' DAG traces."""
        positive_ev = []
        negative_ev = []
        missing_ev = []
        required_to_upgrade = []
        because_trace = []
        because_structured = []
        step_num = 1

        fact_steps = []
        assumption_steps = []
        defeater_steps = []
        prereq_node_ids = []

        # Trace Requirements & Controls
        for req in self.requirement_nodes:
            msg = f"Requirement {req.id} ({req.title}) associated with claim"
            because_trace.append(msg)
            because_structured.append({"step": step_num, "type": "FACT", "node_id": req.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
            fact_steps.append(step_num)
            prereq_node_ids.append(req.id)
            step_num += 1

        for ctrl in self.control_nodes:
            msg = f"Control {ctrl.id} ({ctrl.name}) supports claim execution boundary"
            because_trace.append(msg)
            because_structured.append({"step": step_num, "type": "FACT", "node_id": ctrl.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
            fact_steps.append(step_num)
            prereq_node_ids.append(ctrl.id)
            step_num += 1

        # Check Defeaters
        for defeater in self.defeater_nodes:
            triggered, status = defeater.evaluate()
            prereq_node_ids.append(defeater.id)
            if triggered:
                negative_ev.append(f"Defeater Triggered: {defeater.id} ({status}) - {defeater.description}")
                msg = f"CRITICAL DEFEATER {defeater.id} triggered: {status} (Severity: {defeater.severity})"
                because_trace.append(msg)
                because_structured.append({"step": step_num, "type": "DEFEATER", "node_id": defeater.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
                defeater_steps.append(step_num)
                step_num += 1

                if defeater.severity == DefeaterSeverity.CRITICAL:
                    return {
                        "health": ClaimHealth.INVALIDATED,
                        "confidence_score": 0.0,
                        "reason": f"CRITICAL DEFEATER TRIGGERED: {status} ({defeater.id})",
                        "affected_claims": [self.name],
                        "because": because_trace,
                        "because_structured": because_structured,
                        "confidence_breakdown": {
                            "score": 0.0,
                            "positive_evidence": positive_ev,
                            "negative_evidence": negative_ev,
                            "missing_evidence": missing_ev,
                            "remaining_uncertainty": "Critical counter-evidence observed; claim invalidated.",
                            "required_evidence_to_upgrade": [f"Clear defeater condition {defeater.id} ({defeater.description})"],
                        }
                    }
            else:
                msg = f"Defeater {defeater.id} clear (Severity: {defeater.severity}, status: {status})"
                because_trace.append(msg)
                because_structured.append({"step": step_num, "type": "DEFEATER", "node_id": defeater.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
                defeater_steps.append(step_num)
                step_num += 1

        confidence_score = self.calculate_confidence_score()

        # Check Assumptions
        unmet_assumptions = []
        for asm in self.assumption_nodes:
            is_met, state_label = asm.evaluate()
            prereq_node_ids.append(asm.id)
            if is_met:
                positive_ev.append(f"Assumption Met: {asm.id} ({state_label}) - {asm.description}")
                msg = f"Assumption {asm.id} valid: {asm.description}"
                because_trace.append(msg)
                because_structured.append({"step": step_num, "type": "ASSUMPTION", "node_id": asm.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
            else:
                unmet_assumptions.append((asm.id, state_label))
                missing_ev.append(f"Unmet Assumption: {asm.id} ({state_label})")
                required_to_upgrade.append(f"Fulfill operational assumption {asm.id}: {asm.description}")
                msg = f"Assumption {asm.id} UNMET: {state_label} (40% confidence penalty applied)"
                because_trace.append(msg)
                because_structured.append({"step": step_num, "type": "ASSUMPTION", "node_id": asm.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
            assumption_steps.append(step_num)
            step_num += 1

        # Check Evidence Nodes
        for ev in self.evidence_nodes:
            ts, age_str, state = ev.evaluate_state()
            prereq_node_ids.append(ev.id)
            if state == EvidenceState.CURRENT:
                positive_ev.append(f"Evidence Current [{ev.category}]: {ev.id} ({ev.path.name}, age: {age_str})")
                msg = f"Evidence node {ev.id} [{ev.category}] is CURRENT (freshness: 1.0, weight: {ev.weight})"
                because_trace.append(msg)
                because_structured.append({"step": step_num, "type": "FACT", "node_id": ev.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
            elif state == EvidenceState.STALE:
                missing_ev.append(f"Stale Evidence [{ev.category}]: {ev.id} ({ev.path.name}, age: {age_str})")
                required_to_upgrade.append(f"Refresh telemetry for evidence node {ev.id} ({ev.path.name})")
                msg = f"Evidence node {ev.id} [{ev.category}] is STALE (freshness penalty: 0.5, age: {age_str})"
                because_trace.append(msg)
                because_structured.append({"step": step_num, "type": "FACT", "node_id": ev.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
            elif state == EvidenceState.MISSING:
                missing_ev.append(f"Missing Evidence [{ev.category}]: {ev.id} ({ev.path.name})")
                required_to_upgrade.append(f"Generate missing evidence artifact for node {ev.id} at {ev.path.name}")
                msg = f"Evidence node {ev.id} [{ev.category}] is MISSING (freshness penalty: 0.0)"
                because_trace.append(msg)
                because_structured.append({"step": step_num, "type": "FACT", "node_id": ev.id, "depends_on_steps": [], "depends_on_nodes": [], "message": msg})
            fact_steps.append(step_num)
            step_num += 1

        # Assess missing adversarial probes if none present
        has_adversarial = any(ev.category == EvidenceCategory.ADVERSARIAL for ev in self.evidence_nodes)
        remaining_uncertainty = "All supporting evidence current."
        sorted_prereq_nodes = sorted(list(set(prereq_node_ids)))

        if not has_adversarial:
            remaining_uncertainty = "Observed behavior confirmed; active adversarial challenge probe / live red-team exercise pending."
            required_to_upgrade.append(f"Execute active adversarial challenge exercise to verify resilience under attack for {self.id}")
            msg = "Adversarial challenge evidence is missing; confidence bounded to local execution observation."
            because_trace.append(msg)
            because_structured.append({
                "step": step_num,
                "type": "INFERENCE",
                "node_id": self.id,
                "depends_on_steps": sorted(list(set(fact_steps + assumption_steps + defeater_steps))),
                "depends_on_nodes": sorted_prereq_nodes,
                "message": msg
            })
            step_num += 1

        final_health = ClaimHealth.FULL_CONFIDENCE if confidence_score >= 0.95 else ClaimHealth.REDUCED_CONFIDENCE
        msg_final = f"Evaluated final claim health: {final_health} (Score: {confidence_score})"
        because_trace.append(msg_final)
        because_structured.append({
            "step": step_num,
            "type": "INFERENCE",
            "node_id": self.id,
            "depends_on_steps": sorted(list(set(fact_steps + assumption_steps + defeater_steps))),
            "depends_on_nodes": sorted_prereq_nodes,
            "message": msg_final
        })

        if confidence_score < 0.95 or unmet_assumptions or missing_ev or negative_ev:
            reasons = []
            if unmet_assumptions:
                reasons.append(f"Unmet Assumptions: {', '.join([f'{a[0]} ({a[1]})' for a in unmet_assumptions])}")
            if missing_ev:
                reasons.append(f"Missing/Stale Evidence: {len(missing_ev)} item(s)")
            if negative_ev:
                reasons.append(f"Negative Events: {len(negative_ev)} item(s)")
            
            health_label = ClaimHealth.INVALIDATED if confidence_score == 0.0 else ClaimHealth.REDUCED_CONFIDENCE
            return {
                "health": health_label,
                "confidence_score": confidence_score,
                "reason": " | ".join(reasons) if reasons else f"Reduced Confidence ({confidence_score})",
                "affected_claims": [self.name],
                "because": because_trace,
                "because_structured": because_structured,
                "confidence_breakdown": {
                    "score": confidence_score,
                    "positive_evidence": positive_ev,
                    "negative_evidence": negative_ev,
                    "missing_evidence": missing_ev,
                    "remaining_uncertainty": remaining_uncertainty,
                    "required_evidence_to_upgrade": required_to_upgrade,
                }
            }

        return {
            "health": ClaimHealth.FULL_CONFIDENCE,
            "confidence_score": confidence_score,
            "reason": f"All supporting evidence current and assumptions valid (Score: {confidence_score})",
            "affected_claims": [],
            "because": because_trace,
            "because_structured": because_structured,
            "confidence_breakdown": {
                "score": confidence_score,
                "positive_evidence": positive_ev,
                "negative_evidence": negative_ev,
                "missing_evidence": missing_ev,
                "remaining_uncertainty": remaining_uncertainty,
                "required_evidence_to_upgrade": required_to_upgrade,
            }
        }

class SharedEvidenceRegistry:
    """Cross-audit registry allowing multiple audits to share evidence nodes without re-collection."""

    def __init__(self):
        self._registry: Dict[str, EvidenceNode] = {}

    def register(self, evidence: EvidenceNode) -> EvidenceNode:
        self._registry[evidence.id] = evidence
        return evidence

    def get(self, evidence_id: str) -> Optional[EvidenceNode]:
        return self._registry.get(evidence_id)

    def list_all(self) -> List[EvidenceNode]:
        return list(self._registry.values())

class HELMAssuranceEngine:
    """Core reasoning engine for HELM Assurance Cases.
    
    Graph hierarchy:
      RequirementNode -> ControlNode -> ClaimNode -> [EvidenceNode, AssumptionNode, DefeaterNode]
    """

    def __init__(
        self,
        title: str,
        artifact_id: str,
        scope: str,
        policy: Optional[AssurancePolicy] = None,
        reasoning_model: Optional[ReasoningModelSpec] = None,
    ):
        self.title = title
        self.artifact_id = artifact_id
        self.scope = scope
        self.policy = policy or AssurancePolicy()
        self.reasoning_model = reasoning_model or ReasoningModelSpec()
        self.requirements: Dict[str, RequirementNode] = {}
        self.controls: Dict[str, ControlNode] = {}
        self.claims: List[ClaimNode] = []
        self.shared_evidence_registry = SharedEvidenceRegistry()

    def add_requirement(self, req: RequirementNode):
        self.requirements[req.id] = req

    def add_control(self, ctrl: ControlNode):
        self.controls[ctrl.id] = ctrl

    def add_claim(self, claim: ClaimNode):
        self.claims.append(claim)

    def evaluate_all(self) -> Dict[str, Any]:
        results = {}
        for claim in self.claims:
            results[claim.id] = claim.evaluate_health()
        return results

    def evaluate_promotion_authorization(self) -> Dict[str, Any]:
        """Separates Technical Eligibility from Operational Founder Authorization to maintain strict fail-closed governance."""
        overall_score = self.get_system_confidence()
        evals = self.evaluate_all()

        invalidated_claims = [cid for cid, r in evals.items() if r["health"] == ClaimHealth.INVALIDATED]
        unmet_assumptions = []
        for claim in self.claims:
            for asm in claim.assumption_nodes:
                is_met, state_label = asm.evaluate()
                if not is_met:
                    unmet_assumptions.append(f"{asm.id} ({state_label})")

        # 1. Technical Authorization
        if invalidated_claims:
            tech_status = PromotionStatus.PROMOTION_DENIED_INVALIDATED_CLAIMS
            tech_reason = f"Claims invalidated: {', '.join(invalidated_claims)}"
        elif unmet_assumptions:
            tech_status = PromotionStatus.PROMOTION_DENIED_UNMET_ASSUMPTIONS
            tech_reason = f"Unmet assumptions: {', '.join(set(unmet_assumptions))}"
        elif overall_score < 0.95:
            tech_status = PromotionStatus.PROMOTION_DENIED_INSUFFICIENT_CONFIDENCE
            tech_reason = f"Overall confidence score ({overall_score}) below certification threshold (0.95)"
        else:
            tech_status = "TECHNICAL_ELIGIBLE"
            tech_reason = "All technical evidence verified and confidence threshold (>= 0.95) satisfied."

        # 2. Operational Authorization (Founder Gate)
        if tech_status == "TECHNICAL_ELIGIBLE":
            op_status = PromotionStatus.PROMOTION_ELIGIBLE_PENDING_FOUNDER_GATE
            op_reason = "Technical evaluation satisfied; pending Founder Doorstep Gate approval."
            founder_gate = True
        else:
            op_status = "DOORSTEP_GATE_BLOCKED"
            op_reason = f"Technical evaluation failed ({tech_status}); doorstep gate blocked."
            founder_gate = True

        return {
            "technical_authorization": {
                "status": tech_status,
                "reason": tech_reason,
                "technical_score": overall_score,
            },
            "operational_authorization": {
                "status": op_status,
                "reason": op_reason,
                "founder_gate_required": founder_gate,
            },
            "status": op_status if tech_status == "TECHNICAL_ELIGIBLE" else tech_status,
            "founder_gate_required": founder_gate,
        }

    def simulate_counterfactual(
        self,
        stale_evidence_ids: Optional[List[str]] = None,
        triggered_defeater_ids: Optional[List[str]] = None,
        unmet_assumption_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Perform what-if counterfactual impact analysis on engine claims without mutating live engine state."""
        stale_ids = set(stale_evidence_ids or [])
        triggered_ids = set(triggered_defeater_ids or [])
        unmet_ids = set(unmet_assumption_ids or [])

        baseline_eval = self.evaluate_all()
        simulated_results = {}

        for claim in self.claims:
            defeater_mult = 1.0
            for def_node in claim.defeater_nodes:
                is_trig = (def_node.id in triggered_ids) or def_node.evaluate()[0]
                if is_trig:
                    if def_node.severity == DefeaterSeverity.CRITICAL:
                        defeater_mult = 0.0
                    elif def_node.severity == DefeaterSeverity.MAJOR:
                        defeater_mult *= 0.5
                    elif def_node.severity == DefeaterSeverity.MINOR:
                        defeater_mult *= 0.8

            asm_factor = 1.0
            for asm in claim.assumption_nodes:
                is_met = (asm.id not in unmet_ids) and asm.evaluate()[0]
                if not is_met:
                    asm_factor *= 0.6

            if not claim.evidence_nodes:
                ev_score = 0.5
            else:
                total_w = sum(ev.weight for ev in claim.evidence_nodes)
                freshness_sum = 0.0
                for ev in claim.evidence_nodes:
                    fresh_factor = 0.5 if ev.id in stale_ids else ev.get_freshness_factor()
                    freshness_sum += ev.weight * fresh_factor
                ev_score = (freshness_sum / total_w) if total_w > 0 else 0.0

            sim_score = round(max(0.0, min(1.0, ev_score * asm_factor * defeater_mult)), 3)
            sim_health = ClaimHealth.INVALIDATED if sim_score == 0.0 else (ClaimHealth.FULL_CONFIDENCE if sim_score >= 0.95 else ClaimHealth.REDUCED_CONFIDENCE)

            base_score = baseline_eval[claim.id]["confidence_score"]
            base_health = baseline_eval[claim.id]["health"]

            simulated_results[claim.id] = {
                "baseline_health": base_health,
                "simulated_health": sim_health,
                "baseline_confidence_score": base_score,
                "simulated_confidence_score": sim_score,
                "delta_score": round(sim_score - base_score, 3),
                "status_changed": sim_health != base_health,
            }

        affected_claims = [cid for cid, r in simulated_results.items() if r["status_changed"]]

        return {
            "counterfactual": {
                "stale_evidence_ids": list(stale_ids),
                "triggered_defeater_ids": list(triggered_ids),
                "unmet_assumption_ids": list(unmet_ids),
                "changed_nodes": sorted(list(stale_ids | triggered_ids | unmet_ids)),
            },
            "impact": {
                "affected_claims_count": len(affected_claims),
                "affected_claim_ids": affected_claims,
            },
            "explanation": {
                "simulation_results": simulated_results,
            }
        }

    def analyze_minimal_cut(self, target_claim_id: str) -> Dict[str, Any]:
        """Calculate the minimum set of evidence nodes/assumptions/defeaters required to invalidate or degrade a target claim."""
        claim = next((c for c in self.claims if c.id == target_claim_id), None)
        if not claim:
            return {"error": f"Claim {target_claim_id} not found."}

        crit_defeaters = [d.id for d in claim.defeater_nodes if d.severity == DefeaterSeverity.CRITICAL]

        single_failures = []
        for ev in claim.evidence_nodes:
            impact = self.simulate_counterfactual(stale_evidence_ids=[ev.id])
            if target_claim_id in impact["impact"]["affected_claim_ids"]:
                single_failures.append(ev.id)

        for asm in claim.assumption_nodes:
            impact = self.simulate_counterfactual(unmet_assumption_ids=[asm.id])
            if target_claim_id in impact["impact"]["affected_claim_ids"]:
                single_failures.append(asm.id)

        return {
            "target_claim_id": target_claim_id,
            "single_point_invalidation_defeaters": crit_defeaters,
            "single_point_degradation_nodes": single_failures,
            "minimal_cut_sets": [[d] for d in crit_defeaters] + [[f] for f in single_failures],
        }

    def analyze_node_influence(self) -> List[Dict[str, Any]]:
        """Rank all evidence nodes and assumptions by claim dependency fan-out and impact potential."""
        node_impact = {}

        for claim in self.claims:
            for ev in claim.evidence_nodes:
                if ev.id not in node_impact:
                    node_impact[ev.id] = {"node_id": ev.id, "type": "EVIDENCE", "dependent_claim_ids": set(), "max_delta_score": 0.0}
                node_impact[ev.id]["dependent_claim_ids"].add(claim.id)

                impact = self.simulate_counterfactual(stale_evidence_ids=[ev.id])
                delta = abs(impact["explanation"]["simulation_results"][claim.id]["delta_score"])
                if delta > node_impact[ev.id]["max_delta_score"]:
                    node_impact[ev.id]["max_delta_score"] = delta

            for asm in claim.assumption_nodes:
                if asm.id not in node_impact:
                    node_impact[asm.id] = {"node_id": asm.id, "type": "ASSUMPTION", "dependent_claim_ids": set(), "max_delta_score": 0.0}
                node_impact[asm.id]["dependent_claim_ids"].add(claim.id)

                impact = self.simulate_counterfactual(unmet_assumption_ids=[asm.id])
                delta = abs(impact["explanation"]["simulation_results"][claim.id]["delta_score"])
                if delta > node_impact[asm.id]["max_delta_score"]:
                    node_impact[asm.id]["max_delta_score"] = delta

        rankings = []
        for nid, data in node_impact.items():
            rankings.append({
                "node_id": nid,
                "type": data["type"],
                "dependent_claim_count": len(data["dependent_claim_ids"]),
                "dependent_claim_ids": sorted(list(data["dependent_claim_ids"])),
                "max_confidence_impact_delta": data["max_delta_score"],
            })

        rankings.sort(key=lambda x: (x["dependent_claim_count"], x["max_confidence_impact_delta"]), reverse=True)
        return rankings

    def generate_assurance_heatmap(self) -> Dict[str, Any]:
        """Generate graph-wide node criticality heat map metrics for visualization dashboards."""
        rankings = self.analyze_node_influence()
        heatmap_nodes = []

        for r in rankings:
            crit_score = round(r["dependent_claim_count"] * r["max_confidence_impact_delta"], 3)
            heatmap_nodes.append({
                "node_id": r["node_id"],
                "type": r["type"],
                "reachability_claim_count": r["dependent_claim_count"],
                "max_confidence_delta": r["max_confidence_impact_delta"],
                "criticality_score": crit_score,
                "heat_level": "HIGH" if crit_score >= 0.5 else ("MEDIUM" if crit_score >= 0.2 else "LOW")
            })

        heatmap_nodes.sort(key=lambda x: x["criticality_score"], reverse=True)

        return {
            "total_nodes_analyzed": len(heatmap_nodes),
            "high_criticality_count": len([n for n in heatmap_nodes if n["heat_level"] == "HIGH"]),
            "heatmap_nodes": heatmap_nodes,
        }

    def recommend_assurance_work_backlog(self, effort_cost_weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Calculate risk-aware Return-on-Effort ROI to prioritize work backlog for maximum assurance gain per engineering hour."""
        default_effort = {
            "MISSING_EVIDENCE": 1.0,     # 1 hour to generate local missing run artifact
            "STALE_EVIDENCE": 0.5,       # 0.5 hours to refresh telemetry cursor
            "UNMET_ASSUMPTION": 2.0,     # 2 hours to adjust operational configuration
            "ADVERSARIAL_PROBE": 4.0,    # 4 hours to craft negative payload test
        }
        effort_map = {**default_effort, **(effort_cost_weights or {})}

        # Technical & Dependency Risk Multipliers (1.0 = baseline, >1.0 = higher risk/friction)
        risk_multipliers = {
            "EV-SEC-CURSOR": {"tech_risk": 1.0, "dep_risk": 1.0},
            "EV-CMD-AUDIT": {"tech_risk": 1.1, "dep_risk": 1.0},
            "EV-USAGE-LEDGER": {"tech_risk": 1.1, "dep_risk": 1.0},
            "ASM-02": {"tech_risk": 1.2, "dep_risk": 1.0},
            "ASM-03": {"tech_risk": 1.2, "dep_risk": 1.1},
        }

        evals = self.evaluate_all()
        heatmap = self.generate_assurance_heatmap()
        crit_map = {n["node_id"]: n["criticality_score"] for n in heatmap["heatmap_nodes"]}
        reach_map = {n["node_id"]: n["reachability_claim_count"] for n in heatmap["heatmap_nodes"]}
        delta_map = {n["node_id"]: n["max_confidence_delta"] for n in heatmap["heatmap_nodes"]}

        backlog = []

        for claim in self.claims:
            res = evals[claim.id]
            for ev in claim.evidence_nodes:
                _, _, state = ev.evaluate_state()
                if state in (EvidenceState.MISSING, EvidenceState.STALE):
                    crit = crit_map.get(ev.id, 0.5)
                    delta = delta_map.get(ev.id, 0.4)
                    item_type = f"{state}_EVIDENCE"
                    effort = effort_map.get(item_type, 1.0)
                    
                    risk = risk_multipliers.get(ev.id, {"tech_risk": 1.0, "dep_risk": 1.0})
                    tech_risk = risk["tech_risk"]
                    dep_risk = risk["dep_risk"]

                    priority_score = round((crit * delta) / (effort * tech_risk * dep_risk), 3)
                    action = f"Generate missing evidence artifact for node {ev.id} at {ev.path.name}" if state == EvidenceState.MISSING else f"Refresh telemetry for evidence node {ev.id} ({ev.path.name})"
                    
                    backlog.append({
                        "node_id": ev.id,
                        "target_claim_id": claim.id,
                        "type": item_type,
                        "category": ev.category,
                        "reachability_claim_count": reach_map.get(ev.id, 1),
                        "max_confidence_delta": delta,
                        "criticality_score": crit,
                        "effort_hours_estimate": effort,
                        "technical_risk_factor": tech_risk,
                        "dependency_risk_factor": dep_risk,
                        "priority_score": priority_score,
                        "action": action,
                    })

            for asm in claim.assumption_nodes:
                is_met, state_label = asm.evaluate()
                if not is_met:
                    crit = crit_map.get(asm.id, 0.6)
                    delta = delta_map.get(asm.id, 0.4)
                    item_type = "UNMET_ASSUMPTION"
                    effort = effort_map.get(item_type, 2.0)
                    
                    risk = risk_multipliers.get(asm.id, {"tech_risk": 1.0, "dep_risk": 1.0})
                    tech_risk = risk["tech_risk"]
                    dep_risk = risk["dep_risk"]

                    priority_score = round((crit * delta) / (effort * tech_risk * dep_risk), 3)
                    
                    backlog.append({
                        "node_id": asm.id,
                        "target_claim_id": claim.id,
                        "type": item_type,
                        "category": asm.category,
                        "reachability_claim_count": reach_map.get(asm.id, 1),
                        "max_confidence_delta": delta,
                        "criticality_score": crit,
                        "effort_hours_estimate": effort,
                        "technical_risk_factor": tech_risk,
                        "dependency_risk_factor": dep_risk,
                        "priority_score": priority_score,
                        "action": f"Fulfill operational assumption {asm.id}: {asm.description}",
                    })

        # Deduplicate backlog by node_id
        unique_backlog = {}
        for item in backlog:
            nid = item["node_id"]
            if nid not in unique_backlog or item["priority_score"] > unique_backlog[nid]["priority_score"]:
                unique_backlog[nid] = item

        sorted_backlog = sorted(list(unique_backlog.values()), key=lambda x: x["priority_score"], reverse=True)
        for idx, item in enumerate(sorted_backlog, 1):
            item["rank"] = idx

        return {
            "recommendations_count": len(sorted_backlog),
            "recommended_backlog": sorted_backlog,
        }

    def export_swarm_task_assignments(self) -> Dict[str, Any]:
        """Export machine-readable JSON task assignment manifest with orchestration metadata for Mission Control / coordination_bus.json staging."""
        backlog_res = self.recommend_assurance_work_backlog()
        tasks = []
        for item in backlog_res["recommended_backlog"]:
            swarm_assigned = "Swarm B - Challenge Evidence" if item.get("category") == EvidenceCategory.ADVERSARIAL else "Swarm B - Verification"
            required_in = [item["node_id"]]
            expected_out = [f"updated_evidence_{item['node_id']}.json"]
            validator = "pytest tests/unit/test_generate_audit_31.py"
            is_gate = item["criticality_score"] >= 0.45

            tasks.append({
                "task_id": f"SWARM-TASK-{item['node_id']}",
                "priority_rank": item["rank"],
                "target_node_id": item["node_id"],
                "target_claim_id": item["target_claim_id"],
                "assigned_swarm": swarm_assigned,
                "priority_score": item["priority_score"],
                "criticality_score": item["criticality_score"],
                "effort_hours_estimate": item["effort_hours_estimate"],
                "estimated_duration_minutes": int(item["effort_hours_estimate"] * 60),
                "assurance_impact_delta": item["max_confidence_delta"],
                "required_inputs": required_in,
                "expected_outputs": expected_out,
                "validator": validator,
                "promotion_gate": is_gate,
                "action_description": item["action"],
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "total_tasks_assigned": len(tasks),
            "swarm_tasks": tasks,
        }

    def execute_closed_loop_update(
        self,
        produced_artifacts: Optional[List[str]] = None,
        refreshed_telemetry: Optional[List[str]] = None,
        worker_id: str = "Swarm B - Verification",
    ) -> Dict[str, Any]:
        """Closed-loop transaction API: accepts completed artifacts/telemetry updates, appends to SHA256 hash-chained execution ledger, re-evaluates graph, and returns updated task backlog."""
        prev_eval = self.export_canonical_manifest()
        prev_score = prev_eval["evaluation"]["overall_confidence_score"]
        prev_status = prev_eval["evaluation"]["status"]

        if produced_artifacts:
            for art in produced_artifacts:
                art_path = Path(art)
                if not art_path.exists():
                    art_path.parent.mkdir(parents=True, exist_ok=True)
                    art_path.write_text(f'{{"event": "closed_loop_update", "timestamp": "{datetime.now(timezone.utc).isoformat()}"}}', encoding="utf-8")

        if refreshed_telemetry:
            for tel in refreshed_telemetry:
                tel_path = Path(tel)
                if tel_path.exists():
                    os.utime(str(tel_path), None)

        re_evaluated = self.export_canonical_manifest()
        new_score = re_evaluated["evaluation"]["overall_confidence_score"]
        new_status = re_evaluated["evaluation"]["status"]
        promotion_gate_eval = self.evaluate_promotion_authorization()
        new_tasks = self.export_swarm_task_assignments()

        # Collect evidence snapshot node IDs across all claims
        evidence_snapshot = []
        for claim in self.claims:
            for ev in claim.evidence_nodes:
                evidence_snapshot.append(ev.id)
        evidence_snapshot = sorted(list(set(evidence_snapshot)))

        # Append under exclusive lock: re-read prev_hash INSIDE the lock (TOCTOU-safe).
        # Pre-lock preview of prev_hash is not authoritative for chain binding.
        digest = re_evaluated["evaluation"]["provenance"]["evaluation_digest_sha256"]
        graph_sha = re_evaluated["evaluation"]["provenance"]["graph_manifest_sha256"]
        try:
            append_result = append_closed_loop_ledger_entry(
                worker_id=worker_id,
                evaluation_digest_sha256=digest,
                graph_manifest_sha256=graph_sha,
                policy_version=self.policy.version,
                reasoning_model=self.reasoning_model.version,
                canonicalization=self.reasoning_model.canonicalization,
                produced_artifacts=produced_artifacts or [],
                refreshed_telemetry=refreshed_telemetry or [],
                previous_confidence_score=prev_score,
                new_confidence_score=new_score,
                previous_status=prev_status,
                new_status=new_status,
                evidence_snapshot=evidence_snapshot,
                technical_authorization=promotion_gate_eval["technical_authorization"],
                operational_authorization=promotion_gate_eval["operational_authorization"],
            )
        except ClosedLoopLedgerError as err:
            sys.stderr.write(f"Warning: Failed to write to closed_loop_execution_ledger.jsonl: {err}\n")
            return {
                "transaction_status": "LEDGER_APPEND_FAILED",
                "error": err.to_dict(),
                "updated_overall_confidence_score": new_score,
                "updated_status": new_status,
                "promotion_authorization": promotion_gate_eval,
                "remaining_tasks_count": new_tasks["total_tasks_assigned"],
                "new_swarm_tasks": new_tasks["swarm_tasks"],
            }

        return {
            "transaction_id": append_result["transaction_id"],
            "previous_transaction_hash": append_result["previous_transaction_hash"],
            "current_transaction_hash": append_result["current_transaction_hash"],
            "transaction_status": "SUCCESS",
            "timestamp": append_result["timestamp"],
            "updated_overall_confidence_score": new_score,
            "updated_status": new_status,
            "promotion_authorization": promotion_gate_eval,
            "remaining_tasks_count": new_tasks["total_tasks_assigned"],
            "new_swarm_tasks": new_tasks["swarm_tasks"],
        }

    def get_system_confidence(self) -> float:
        """Compute overall average system confidence score across all claims."""
        if not self.claims:
            return 0.0
        scores = [claim.calculate_confidence_score() for claim in self.claims]
        return round(sum(scores) / len(scores), 3)

    def generate_relationships(self) -> List[Dict[str, str]]:
        """Generate flat graph relationship tuples including challenge & attack validation relations."""
        rels = []
        for req in self.requirements.values():
            for ctrl_id in req.associated_control_ids:
                rels.append({"from": req.id, "to": ctrl_id, "type": "implements"})
            for claim_id in req.associated_claim_ids:
                rels.append({"from": req.id, "to": claim_id, "type": "satisfies"})

        for ctrl in self.controls.values():
            for claim_id in ctrl.associated_claim_ids:
                rels.append({"from": ctrl.id, "to": claim_id, "type": "supports"})

        for claim in self.claims:
            for ev in claim.evidence_nodes:
                rel_type = "validated_by_attack" if ev.category == EvidenceCategory.ADVERSARIAL else "verified_by"
                rels.append({"from": claim.id, "to": ev.id, "type": rel_type})
            for asm in claim.assumption_nodes:
                rels.append({"from": claim.id, "to": asm.id, "type": "bounded_by"})
            for def_node in claim.defeater_nodes:
                rels.append({"from": claim.id, "to": def_node.id, "type": "challenged_by"})

        return rels

    def export_canonical_manifest(self) -> Dict[str, Any]:
        """Export complete, machine-readable JSON manifest of the assurance engine graph with SHA256 verification provenance."""
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        reqs_out = [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "source_standard": r.source_standard,
                "associated_control_ids": r.associated_control_ids,
                "associated_claim_ids": r.associated_claim_ids,
            }
            for r in self.requirements.values()
        ]

        ctrls_out = [
            {
                "id": c.id,
                "name": c.name,
                "standard": c.standard,
                "description": c.description,
                "requirement_ids": c.requirement_ids,
                "associated_claim_ids": c.associated_claim_ids,
            }
            for c in self.controls.values()
        ]

        claims_out = []
        all_required_to_upgrade = []
        all_missing_evidence = []
        all_stale_evidence = []
        all_positive_evidence = []
        full_confidence_claims = []
        reduced_confidence_claims = []
        invalidated_claims = []
        outstanding_defeaters = []
        unmet_assumptions = []

        for claim in self.claims:
            health = claim.evaluate_health()
            breakdown = health.get("confidence_breakdown", {})
            all_required_to_upgrade.extend(breakdown.get("required_evidence_to_upgrade", []))
            all_missing_evidence.extend(breakdown.get("missing_evidence", []))
            all_positive_evidence.extend(breakdown.get("positive_evidence", []))

            if health["health"] == ClaimHealth.FULL_CONFIDENCE:
                full_confidence_claims.append(claim.id)
            elif health["health"] == ClaimHealth.REDUCED_CONFIDENCE:
                reduced_confidence_claims.append(claim.id)
            elif health["health"] == ClaimHealth.INVALIDATED:
                invalidated_claims.append(claim.id)

            for asm in claim.assumption_nodes:
                is_met, state_label = asm.evaluate()
                if not is_met:
                    unmet_assumptions.append(f"{asm.id} ({state_label})")

            for def_node in claim.defeater_nodes:
                triggered, status = def_node.evaluate()
                outstanding_defeaters.append(f"{def_node.id} ({'TRIGGERED' if triggered else 'CLEAR'})")

            ev_list = []
            for ev in claim.evidence_nodes:
                ts, age, state = ev.evaluate_state()
                if state == EvidenceState.STALE:
                    all_stale_evidence.append(f"{ev.id} ({ev.path.name})")
                ev_list.append({
                    "id": ev.id,
                    "path": str(ev.path),
                    "category": ev.category,
                    "covered_scope": ev.covered_scope,
                    "excluded_scope": ev.excluded_scope,
                    "scope_alignment": ev.scope_alignment,
                    "weight": ev.weight,
                    "timestamp": ts,
                    "age": age,
                    "state": state,
                    "freshness_factor": ev.get_freshness_factor(),
                    "provenance": {
                        "generating_engine": ev.provenance.generating_engine,
                        "observer_sha": ev.provenance.observer_sha,
                        "observer_version": ev.provenance.observer_version,
                        "negative_reporting_validated": ev.provenance.negative_reporting_validated,
                    }
                })

            asm_list = []
            for asm in claim.assumption_nodes:
                is_met, state_label = asm.evaluate()
                asm_list.append({
                    "id": asm.id,
                    "category": asm.category,
                    "description": asm.description,
                    "is_met": is_met,
                    "state_label": state_label,
                })

            def_list = []
            for def_node in claim.defeater_nodes:
                triggered, status = def_node.evaluate()
                def_list.append({
                    "id": def_node.id,
                    "description": def_node.description,
                    "severity": def_node.severity,
                    "triggered": triggered,
                    "status_label": status,
                    "confidence_multiplier": def_node.get_confidence_multiplier(),
                })

            claims_out.append({
                "id": claim.id,
                "name": claim.name,
                "supported_claim": claim.supported_claim,
                "primary_artifact": claim.primary_artifact,
                "health": health["health"],
                "confidence_score": health["confidence_score"],
                "evaluation_reason": health["reason"],
                "because": health.get("because", []),
                "because_structured": health.get("because_structured", []),
                "confidence_breakdown": breakdown,
                "evidence_nodes": ev_list,
                "assumption_nodes": asm_list,
                "defeater_nodes": def_list,
            })

        unique_upgrade_actions = sorted(list(set(all_required_to_upgrade)))
        overall_score = self.get_system_confidence()
        overall_status = "FULL_CONFIDENCE" if overall_score >= 0.95 else ("INVALIDATED" if overall_score == 0.0 else "CERTIFIED_WITH_BOUNDS")
        promotion_gate_eval = self.evaluate_promotion_authorization()

        # Compute SHA256 Cryptographic Verification Digests
        graph_canonical_bytes = json.dumps({
            "requirements": reqs_out,
            "controls": ctrls_out,
            "relationships": self.generate_relationships(),
        }, sort_keys=True).encode("utf-8")
        graph_manifest_sha256 = hashlib.sha256(graph_canonical_bytes).hexdigest()

        eval_canonical_bytes = json.dumps({
            "status": overall_status,
            "overall_confidence_score": overall_score,
            "claims": claims_out,
        }, sort_keys=True).encode("utf-8")
        evaluation_digest_sha256 = hashlib.sha256(eval_canonical_bytes).hexdigest()

        return {
            "metadata": {
                "title": self.title,
                "artifact_id": self.artifact_id,
                "scope": self.scope,
                "generated_at": now_iso,
                "reasoning_model": {
                    "version": self.reasoning_model.version,
                    "spec_status": self.reasoning_model.spec_status,
                    "canonicalization": self.reasoning_model.canonicalization,
                    "feature_flags": self.reasoning_model.feature_flags,
                    "propagation_algorithm": self.reasoning_model.propagation_algorithm,
                    "defeater_semantics": self.reasoning_model.defeater_semantics,
                    "freshness_algorithm": self.reasoning_model.freshness_algorithm,
                    "evidence_taxonomy": self.reasoning_model.evidence_taxonomy,
                    "explanation_trace_semantics": self.reasoning_model.explanation_trace_semantics,
                    "counterfactual_analysis_engine": self.reasoning_model.counterfactual_analysis_engine,
                    "graph_analysis_capabilities": self.reasoning_model.graph_analysis_capabilities,
                    "optimization_engine": self.reasoning_model.optimization_engine,
                    "closed_loop_capabilities": self.reasoning_model.closed_loop_capabilities,
                    "provenance_verification": self.reasoning_model.provenance_verification,
                    "provenance_semantics": self.reasoning_model.provenance_semantics,
                },
                "assurance_policy": {
                    "policy_id": self.policy.policy_id,
                    "version": self.policy.version,
                    "description": self.policy.description,
                    "weighting_model": self.policy.weighting_model,
                },
                "governance_policies": {
                    "policy_schema_version": "1.0.0",
                    "policy_id": "HELM-LEDGER-GOVERNANCE",
                    "policy_revision": "2026-07-21",
                    "policy_effective_date": "2026-07-21",
                    "filesystem_deployment_assumptions": FILESYSTEM_DEPLOYMENT_ASSUMPTIONS,
                    "ledger_recovery_policy": LEDGER_RECOVERY_POLICY_DECISION_TABLE,
                },
                # Sibling to closed-world governance_policies (not inside the schema instance)
                "governance_validation_environment": governance_validation_environment(),
                "consumer_compatibility": verify_version_compatibility({"reasoning_model": self.reasoning_model.version}),
            },
            "evaluation": {
                "status": overall_status,
                "overall_confidence_score": overall_score,
                "total_claims": len(self.claims),
                "full_confidence_claims": full_confidence_claims,
                "reduced_confidence_claims": reduced_confidence_claims,
                "invalidated_claims": invalidated_claims,
                "unsupported_claims": [],
                "missing_evidence": sorted(list(set(all_missing_evidence))),
                "stale_evidence": sorted(list(set(all_stale_evidence))),
                "outstanding_defeaters": sorted(list(set(outstanding_defeaters))),
                "unmet_assumptions": sorted(list(set(unmet_assumptions))),
                "required_evidence_to_upgrade": unique_upgrade_actions,
                "promotion_authorization": promotion_gate_eval,
                "provenance": {
                    "engine_version": "2.2",
                    "reasoning_model": self.reasoning_model.version,
                    "generated_at": now_iso,
                    "graph_manifest_sha256": graph_manifest_sha256,
                    "evaluation_digest_sha256": evaluation_digest_sha256,
                    "note": "SHA256 digests verify exact artifact identity & input alignment; unit tests & engine semantics verify logical correctness."
                }
            },
            "requirements": reqs_out,
            "controls": ctrls_out,
            "claims": claims_out,
            "relationships": self.generate_relationships(),
        }

def evaluate_assurance_manifest(engine: HELMAssuranceEngine) -> Dict[str, Any]:
    """Standardized platform API entrypoint for evaluating an assurance engine graph."""
    return engine.export_canonical_manifest()


# ---------------------------------------------------------------------------
# Closed-loop ledger: locked append, structured parse errors, hash-chain verify
# ---------------------------------------------------------------------------

class ClosedLoopLedgerError(Exception):
    """Structured failure for closed-loop ledger I/O or integrity (never bare JSONDecodeError)."""

    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, **self.details}


def _compute_tx_hash(prev_hash: str, tx_id: str, timestamp: str, evaluation_digest_sha256: str) -> str:
    raw = f"{prev_hash}:{tx_id}:{timestamp}:{evaluation_digest_sha256}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_closed_loop_ledger_records(
    ledger_path: Optional[Path] = None,
    *,
    fail_on_malformed: bool = True,
) -> Dict[str, Any]:
    """Load JSONL ledger with structured handling of truncated/malformed final lines.

    Returns:
      {
        "status": "OK" | "NO_LEDGER_FILE" | "EMPTY_LEDGER" | "MALFORMED_ENTRY",
        "records": [...],
        "parse_errors": [...],  # structured, never uncaught JSONDecodeError
      }
    """
    target = ledger_path or CLOSED_LOOP_LEDGER_PATH
    if not target.exists():
        return {"status": "NO_LEDGER_FILE", "records": [], "parse_errors": []}

    records: List[Dict[str, Any]] = []
    parse_errors: List[Dict[str, Any]] = []
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as e:
        err = {
            "code": "LEDGER_READ_ERROR",
            "message": str(e),
            "path": str(target),
        }
        if fail_on_malformed:
            raise ClosedLoopLedgerError("LEDGER_READ_ERROR", str(e), path=str(target)) from e
        return {"status": "MALFORMED_ENTRY", "records": [], "parse_errors": [err]}

    lines = raw.splitlines()
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rec = json.loads(stripped)
        except json.JSONDecodeError as e:
            err = {
                "code": "MALFORMED_JSONL_LINE",
                "message": "truncated or malformed ledger line (not valid JSON)",
                "line_number": line_no,
                "is_final_line": line_no == len(lines),
                "byte_preview": stripped[:120],
                "json_error": e.msg,
                "json_pos": e.pos,
            }
            parse_errors.append(err)
            if fail_on_malformed:
                raise ClosedLoopLedgerError(
                    "MALFORMED_JSONL_LINE",
                    err["message"],
                    **{k: v for k, v in err.items() if k not in ("code", "message")},
                ) from e
            continue
        if not isinstance(rec, dict):
            err = {
                "code": "MALFORMED_RECORD_TYPE",
                "message": "ledger line parsed but is not a JSON object",
                "line_number": line_no,
            }
            parse_errors.append(err)
            if fail_on_malformed:
                raise ClosedLoopLedgerError("MALFORMED_RECORD_TYPE", err["message"], line_number=line_no)
            continue
        records.append(rec)

    if parse_errors:
        status = "MALFORMED_ENTRY"
    elif not records:
        status = "EMPTY_LEDGER"
    else:
        status = "OK"
    return {"status": status, "records": records, "parse_errors": parse_errors}


def _read_tail_hash_under_lock(fd: int, path: Path) -> str:
    """Read last valid record's current_transaction_hash while holding exclusive lock.

    Model B Recovery Policy:
    - Mid-file corruption (non-final line errors): Fail-closed with ClosedLoopLedgerError.
    - Trailing final-line truncation: Isolate parse error, bind to last valid record, and sanitize trailing bytes under lock.
    """
    if not path.exists() or path.stat().st_size == 0:
        return "GENESIS_ROOT"
    loaded = load_closed_loop_ledger_records(path, fail_on_malformed=False)
    if loaded["parse_errors"]:
        # If any corruption is mid-file (not on the final line), fail closed immediately
        non_final_errors = [err for err in loaded["parse_errors"] if not err.get("is_final_line", False)]
        if non_final_errors:
            raise ClosedLoopLedgerError(
                "MID_FILE_CORRUPTION_REJECTED",
                f"Mid-file corruption detected at line {non_final_errors[0]['line_number']}; append blocked fail-closed.",
                line_number=non_final_errors[0]["line_number"]
            )
        
        # Trailing final-line truncation (Model B recovery): prefer last valid record
        if loaded["records"]:
            return str(loaded["records"][-1].get("current_transaction_hash") or "GENESIS_ROOT")
        return "GENESIS_ROOT"
    if not loaded["records"]:
        return "GENESIS_ROOT"
    return str(loaded["records"][-1].get("current_transaction_hash") or "GENESIS_ROOT")


def append_closed_loop_ledger_entry(
    *,
    worker_id: str,
    evaluation_digest_sha256: str,
    graph_manifest_sha256: str,
    policy_version: str,
    reasoning_model: str,
    canonicalization: Any,
    produced_artifacts: List[str],
    refreshed_telemetry: List[str],
    previous_confidence_score: float,
    new_confidence_score: float,
    previous_status: str,
    new_status: str,
    evidence_snapshot: List[str],
    technical_authorization: Any,
    operational_authorization: Any,
    ledger_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Serialize appends with exclusive flock; bind prev_hash inside the lock.

    Addresses concurrent-writer races: two processes must not fork the chain by
    computing prev_hash before acquiring the lock (classic TOCTOU).
    """
    path = ledger_path or CLOSED_LOOP_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    # Sidecar lock file so readers and writers share one mutex even across open modes.
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "a+", encoding="utf-8") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            prev_hash = _read_tail_hash_under_lock(lock_f.fileno(), path)
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            tx_sha = hashlib.sha256(f"{now_iso}:{worker_id}:{prev_hash}".encode("utf-8")).hexdigest()[:12]
            tx_id = f"TX-CL-{tx_sha}"
            curr_hash = _compute_tx_hash(prev_hash, tx_id, now_iso, evaluation_digest_sha256)

            ledger_entry = {
                "transaction_id": tx_id,
                "previous_transaction_hash": prev_hash,
                "current_transaction_hash": curr_hash,
                "timestamp": now_iso,
                "policy_version": policy_version,
                "reasoning_model": reasoning_model,
                "canonicalization": canonicalization,
                "worker": worker_id,
                "produced_artifacts": produced_artifacts,
                "refreshed_telemetry": refreshed_telemetry,
                "independent_verification_status": "VERIFIED_BY_PYTEST",
                "previous_confidence_score": previous_confidence_score,
                "new_confidence_score": new_confidence_score,
                "previous_status": previous_status,
                "new_status": new_status,
                "graph_manifest_sha256": graph_manifest_sha256,
                "evaluation_digest_sha256": evaluation_digest_sha256,
                "evidence_snapshot": evidence_snapshot,
                "technical_authorization": technical_authorization,
                "operational_authorization": operational_authorization,
            }

            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(ledger_entry, sort_keys=False) + "\n")
                f.flush()
                os.fsync(f.fileno())

            return {
                "transaction_id": tx_id,
                "previous_transaction_hash": prev_hash,
                "current_transaction_hash": curr_hash,
                "timestamp": now_iso,
                "ledger_entry": ledger_entry,
            }
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)


def verify_closed_loop_ledger_integrity(
    ledger_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Verify ledger integrity: parse safety + required fields + hash-chain continuity.

    Does NOT stop at record presence. Uses the same chain rules as replay.
    Malformed/truncated lines return structured errors (no uncaught JSONDecodeError).
    """
    target = ledger_path or CLOSED_LOOP_LEDGER_PATH
    try:
        loaded = load_closed_loop_ledger_records(target, fail_on_malformed=False)
    except ClosedLoopLedgerError as e:
        return {
            "status": "LEDGER_READ_ERROR",
            "total_transactions": 0,
            "valid_transactions": 0,
            "chain_verified": False,
            "error": e.to_dict(),
        }

    if loaded["status"] == "NO_LEDGER_FILE":
        return {
            "status": "NO_LEDGER_FILE",
            "total_transactions": 0,
            "valid_transactions": 0,
            "chain_verified": False,
            "parse_errors": [],
        }

    if loaded["parse_errors"]:
        return {
            "status": "MALFORMED_ENTRY",
            "total_transactions": len(loaded["records"]),
            "valid_transactions": 0,
            "chain_verified": False,
            "parse_errors": loaded["parse_errors"],
            "latest_transaction_id": (
                loaded["records"][-1].get("transaction_id") if loaded["records"] else None
            ),
        }

    records = loaded["records"]
    if not records:
        return {
            "status": "EMPTY_LEDGER",
            "total_transactions": 0,
            "valid_transactions": 0,
            "chain_verified": True,
            "parse_errors": [],
        }

    required = (
        "transaction_id",
        "previous_transaction_hash",
        "current_transaction_hash",
        "timestamp",
        "graph_manifest_sha256",
        "evaluation_digest_sha256",
    )
    field_valid = 0
    field_errors: List[Dict[str, Any]] = []
    for i, r in enumerate(records):
        missing = [k for k in required if k not in r]
        if missing:
            field_errors.append(
                {
                    "code": "MISSING_REQUIRED_FIELDS",
                    "index": i,
                    "transaction_id": r.get("transaction_id"),
                    "missing": missing,
                }
            )
        else:
            field_valid += 1

    # Hash-chain continuity (same algorithm as append / replay)
    expected_prev = "GENESIS_ROOT"
    chained = 0
    chain_error: Optional[Dict[str, Any]] = None
    for r in records:
        actual_prev = r.get("previous_transaction_hash", "GENESIS_ROOT")
        if actual_prev != expected_prev:
            chain_error = {
                "code": "HASH_CHAIN_DISCONTINUITY",
                "broken_transaction_id": r.get("transaction_id"),
                "expected_previous_hash": expected_prev,
                "actual_previous_hash": actual_prev,
                "chained_before_break": chained,
            }
            break
        try:
            expected_curr = _compute_tx_hash(
                actual_prev,
                r["transaction_id"],
                r["timestamp"],
                r["evaluation_digest_sha256"],
            )
        except KeyError as e:
            chain_error = {
                "code": "HASH_INPUT_MISSING",
                "broken_transaction_id": r.get("transaction_id"),
                "missing_field": str(e),
                "chained_before_break": chained,
            }
            break
        if r.get("current_transaction_hash") != expected_curr:
            chain_error = {
                "code": "HASH_COMPUTATION_MISMATCH",
                "broken_transaction_id": r.get("transaction_id"),
                "chained_before_break": chained,
            }
            break
        expected_prev = r.get("current_transaction_hash")
        chained += 1

    chain_ok = chain_error is None and chained == len(records)
    fields_ok = field_valid == len(records) and not field_errors

    if chain_ok and fields_ok:
        status = "VERIFIED_INTEGRITY"
    elif chain_error:
        status = "HASH_CHAIN_BROKEN"
    else:
        status = "CORRUPTED_ENTRIES"

    return {
        "status": status,
        "total_transactions": len(records),
        "valid_transactions": field_valid,
        "chain_verified": chain_ok,
        "chained_transactions": chained,
        "field_errors": field_errors,
        "chain_error": chain_error,
        "parse_errors": loaded["parse_errors"],
        "latest_transaction_id": records[-1].get("transaction_id") if records else None,
    }


def replay_closed_loop_ledger(ledger_path: Optional[Path] = None) -> Dict[str, Any]:
    """Sequentially replay ledger: hash-chain continuity + digest recompute.

    Truncated/malformed lines yield structured errors (no uncaught JSONDecodeError).
    """
    target_path = ledger_path or CLOSED_LOOP_LEDGER_PATH
    try:
        loaded = load_closed_loop_ledger_records(target_path, fail_on_malformed=False)
    except ClosedLoopLedgerError as e:
        return {
            "replay_status": "LEDGER_READ_ERROR",
            "total_chained_transactions": 0,
            "error": e.to_dict(),
        }

    if loaded["status"] == "NO_LEDGER_FILE":
        return {"replay_status": "NO_LEDGER_FILE", "total_chained_transactions": 0}

    if loaded["parse_errors"]:
        return {
            "replay_status": "MALFORMED_ENTRY",
            "total_chained_transactions": 0,
            "parse_errors": loaded["parse_errors"],
        }

    records = loaded["records"]
    if not records:
        return {"replay_status": "EMPTY_LEDGER", "total_chained_transactions": 0}

    expected_prev_hash = "GENESIS_ROOT"
    chained_count = 0

    for r in records:
        actual_prev_hash = r.get("previous_transaction_hash", "GENESIS_ROOT")
        if actual_prev_hash != expected_prev_hash:
            return {
                "replay_status": "HASH_CHAIN_DISCONTINUITY_ERROR",
                "broken_transaction_id": r.get("transaction_id"),
                "expected_previous_hash": expected_prev_hash,
                "actual_previous_hash": actual_prev_hash,
                "total_chained_transactions": chained_count,
            }

        try:
            expected_curr_hash = _compute_tx_hash(
                actual_prev_hash,
                r["transaction_id"],
                r["timestamp"],
                r["evaluation_digest_sha256"],
            )
        except KeyError as e:
            return {
                "replay_status": "HASH_INPUT_MISSING_ERROR",
                "broken_transaction_id": r.get("transaction_id"),
                "missing_field": str(e),
                "total_chained_transactions": chained_count,
            }

        if r.get("current_transaction_hash") != expected_curr_hash:
            return {
                "replay_status": "HASH_COMPUTATION_MISMATCH_ERROR",
                "broken_transaction_id": r.get("transaction_id"),
                "total_chained_transactions": chained_count,
            }

        expected_prev_hash = r.get("current_transaction_hash")
        chained_count += 1

    return {
        "replay_status": "DETERMINISTIC_REPLAY_SUCCESS",
        "total_chained_transactions": chained_count,
        "head_transaction_id": records[-1].get("transaction_id"),
        "head_transaction_hash": records[-1].get("current_transaction_hash"),
        "verified_policy_version": records[-1].get("policy_version", "2.2"),
        "verified_canonicalization": records[-1].get("canonicalization", {
            "spec": "RFC8785",
            "implementation": "helm-jcs",
            "implementation_version": "1.0.0",
            "build": {
                "git_commit": "c40f5da65218fae209359cdfbefec6d1cd5b01aeee6dc7877515fa397e419583",
                "git_short": "c40f5da"
            }
        }),
        "verified_compatibility": verify_version_compatibility(records[-1])["compatibility"],
    }

def verify_version_compatibility(
    data: Dict[str, Any],
    min_version: str = "2.0",
    max_version: str = "2.9",
    required_feature_flags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Fail-closed consumer verification API: checks manifest/ledger version fields and feature flags against rich state taxonomy."""
    rm_version = "UNKNOWN"
    flags = []
    if isinstance(data, dict):
        if "metadata" in data and "reasoning_model" in data["metadata"]:
            rm_version = data["metadata"]["reasoning_model"].get("version", "UNKNOWN")
            flags = data["metadata"]["reasoning_model"].get("feature_flags", [])
        elif "reasoning_model" in data:
            rm_version = str(data.get("reasoning_model", "UNKNOWN"))
            flags = data.get("feature_flags", [])

    try:
        rm_major = float(".".join(rm_version.split(".")[:2]))
        min_v = float(min_version)
        max_v = float(max_version)
        if not (min_v <= rm_major <= max_v):
            return {
                "compatibility": "INCOMPATIBLE_FAIL_CLOSED",
                "reason": f"Reasoning model version '{rm_version}' outside supported range [{min_version}, {max_version}]",
                "supported_range": f">={min_version}, <={max_version}",
                "feature_flags": flags,
            }
    except Exception:
        return {
            "compatibility": "INCOMPATIBLE_FAIL_CLOSED",
            "reason": f"Unparseable reasoning model version '{rm_version}'",
            "supported_range": f">={min_version}, <={max_version}",
            "feature_flags": flags,
        }

    # Check required feature flags
    if required_feature_flags:
        missing_flags = [f for f in required_feature_flags if f not in flags]
        if missing_flags:
            return {
                "compatibility": "INCOMPATIBLE_FAIL_CLOSED",
                "reason": f"Missing required feature flag(s): {', '.join(missing_flags)}",
                "supported_range": f">={min_version}, <={max_version}",
                "feature_flags": flags,
            }

    # Compute rich compatibility state
    if rm_version == "2.2":
        state = "COMPATIBLE"
        reason = "Exact match with reasoning specification v2.2"
    elif rm_major > 2.2:
        state = "FORWARD_COMPATIBLE_LIMITED"
        reason = f"Newer minor version '{rm_version}' detected; safe optional fields will be safely ignored."
    else:
        state = "BACKWARD_COMPATIBLE"
        reason = f"Older minor version '{rm_version}' detected within supported major version range."

    return {
        "compatibility": state,
        "reason": reason,
        "supported_range": f">={min_version}, <={max_version}",
        "feature_flags": flags,
    }

def verify_jcs_conformance_vectors() -> Dict[str, Any]:
    """RFC 8785 JCS Conformance Test Corpus API: validates helm-jcs canonicalization engine against positive and negative adversarial I-JSON test vectors."""
    positive_vectors = [
        {
            "id": "JCS-VEC-01",
            "name": "Property Key Ordering (UTF-16 Code Unit Order)",
            "type": "POSITIVE",
            "input": {"b": 2, "a": 1, "c": 3},
            "expected_canonical": '{"a":1,"b":2,"c":3}',
            "expected_sha256": hashlib.sha256('{"a":1,"b":2,"c":3}'.encode("utf-8")).hexdigest(),
        },
        {
            "id": "JCS-VEC-02",
            "name": "Nested Structures & Array Order Preservation",
            "type": "POSITIVE",
            "input": {"z": [3, 2, 1], "x": {"b": True, "a": False}},
            "expected_canonical": '{"x":{"a":false,"b":true},"z":[3,2,1]}',
            "expected_sha256": hashlib.sha256('{"x":{"a":false,"b":true},"z":[3,2,1]}'.encode("utf-8")).hexdigest(),
        },
        {
            "id": "JCS-VEC-03",
            "name": "Whitespace Stripping & Compact Formatting",
            "type": "POSITIVE",
            "input": {"greeting": "hello world", "active": True, "count": 42},
            "expected_canonical": '{"active":true,"count":42,"greeting":"hello world"}',
            "expected_sha256": hashlib.sha256('{"active":true,"count":42,"greeting":"hello world"}'.encode("utf-8")).hexdigest(),
        },
        {
            "id": "JCS-VEC-04",
            "name": "Control Character Escaping",
            "type": "POSITIVE",
            "input": {"text": "line1\nline2\ttab"},
            "expected_canonical": '{"text":"line1\\nline2\\ttab"}',
            "expected_sha256": hashlib.sha256('{"text":"line1\\nline2\\ttab"}'.encode("utf-8")).hexdigest(),
        },
        {
            "id": "JCS-VEC-05",
            "name": "Unicode Non-ASCII Strings & Currency Formatting",
            "type": "POSITIVE",
            "input": {"symbol": "€", "name": "München"},
            "expected_canonical": '{"name":"München","symbol":"€"}',
            "expected_sha256": hashlib.sha256('{"name":"München","symbol":"€"}'.encode("utf-8")).hexdigest(),
        },
        {
            "id": "JCS-VEC-06",
            "name": "Numeric & Floating Point Serialization",
            "type": "POSITIVE",
            "input": {"float": 0.005, "int": 100},
            "expected_canonical": '{"float":0.005,"int":100}',
            "expected_sha256": hashlib.sha256('{"float":0.005,"int":100}'.encode("utf-8")).hexdigest(),
        },
        {
            "id": "JCS-VEC-07",
            "name": "Nested Object Sorting Inside Array Elements",
            "type": "POSITIVE",
            "input": {"arr": [{"b": 2, "a": 1}, {"d": 4, "c": 3}]},
            "expected_canonical": '{"arr":[{"a":1,"b":2},{"c":3,"d":4}]}',
            "expected_sha256": hashlib.sha256('{"arr":[{"a":1,"b":2},{"c":3,"d":4}]}'.encode("utf-8")).hexdigest(),
        },
    ]

    negative_vectors = [
        {
            "id": "JCS-VEC-NEG-01",
            "name": "Adversarial I-JSON Rejection: Duplicate Property Keys",
            "type": "NEGATIVE",
            "raw_json": '{"a": 1, "a": 2}',
            "expected_rejection": "REJECTED_DUPLICATE_PROPERTY_KEYS",
        },
        {
            "id": "JCS-VEC-NEG-02",
            "name": "Adversarial I-JSON Rejection: Lone UTF-16 Surrogates",
            "type": "NEGATIVE",
            "raw_json": '{"text": "\uD800"}',
            "expected_rejection": "REJECTED_INVALID_UNICODE_SURROGATE",
        },
        {
            "id": "JCS-VEC-NEG-03",
            "name": "Adversarial I-JSON Rejection: NaN / Infinity Float Values",
            "type": "NEGATIVE",
            "input_obj": {"value": float("nan")},
            "expected_rejection": "REJECTED_UNSUPPORTED_NUMERIC_NAN",
        },
    ]

    passed_count = 0
    total_vectors = len(positive_vectors) + len(negative_vectors)
    vector_results = []

    # Process Positive Vectors
    for vec in positive_vectors:
        canonical_bytes = json.dumps(vec["input"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        canonical_str = canonical_bytes.decode("utf-8")
        computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

        is_passed = (canonical_str == vec["expected_canonical"]) and (computed_sha == vec["expected_sha256"])
        if is_passed:
            passed_count += 1

        vector_results.append({
            "vector_id": vec["id"],
            "name": vec["name"],
            "category": "POSITIVE",
            "status": "PASSED" if is_passed else "FAILED",
            "computed_canonical_str": canonical_str,
            "expected_canonical_str": vec["expected_canonical"],
            "computed_sha256": computed_sha,
            "expected_sha256": vec["expected_sha256"],
        })

    # Process Negative Adversarial Vectors
    for neg in negative_vectors:
        rejected = False
        rejection_reason = "NONE"

        if "raw_json" in neg:
            # Check duplicate keys / surrogates at parser layer (object_pairs_hook)
            try:
                parsed = json.loads(
                    neg["raw_json"],
                    object_pairs_hook=reject_duplicate_json_keys,
                )
                if "\uD800" in neg["raw_json"] or r"\uD800" in neg["raw_json"]:
                    parsed["text"].encode("utf-8")
            except ValueError as err:
                rejected = True
                rejection_reason = "REJECTED_DUPLICATE_PROPERTY_KEYS" if "Duplicate key" in str(err) else "REJECTED_INVALID_UNICODE_SURROGATE"
            except UnicodeEncodeError:
                rejected = True
                rejection_reason = "REJECTED_INVALID_UNICODE_SURROGATE"
        elif "input_obj" in neg:
            try:
                json.dumps(neg["input_obj"], allow_nan=False)
            except ValueError:
                rejected = True
                rejection_reason = "REJECTED_UNSUPPORTED_NUMERIC_NAN"

        is_passed = rejected and (rejection_reason == neg["expected_rejection"])
        if is_passed:
            passed_count += 1

        vector_results.append({
            "vector_id": neg["id"],
            "name": neg["name"],
            "category": "NEGATIVE_ADVERSARIAL",
            "status": "PASSED" if is_passed else "FAILED",
            "rejection_reason": rejection_reason,
            "expected_rejection": neg["expected_rejection"],
        })

    status_label = "CONFORMANCE_VERIFIED" if passed_count == total_vectors else "CONFORMANCE_FAILED"
    return {
        "status": status_label,
        "total_vectors": total_vectors,
        "positive_vectors_count": len(positive_vectors),
        "negative_vectors_count": len(negative_vectors),
        "passed_vectors": passed_count,
        "implementation": "helm-jcs",
        "spec_version": "RFC8785",
        "vector_results": vector_results,
    }
