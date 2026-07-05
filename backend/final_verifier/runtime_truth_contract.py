"""Runtime Truth Contract loader and enforcement helpers.

Additive, non-breaking companion to the other final_verifier validators. Loads
config/runtime_truth_contract.json (the machine-readable form of
docs/doctrine/HAS_EVIDENCE_DISCIPLINE_BASELINE.md) and exposes pure helper
functions so gates, the readiness engine, and UI status rendering can enforce
the source-of-truth hierarchy and label-state machine without embedding the
rules in model prompts.

Nothing here mutates state or calls out; every function is deterministic and
returns a dict, matching the style of evidence_validator / ui_truth_validator.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional

DEFAULT_CONTRACT_PATH = os.path.join("config", "runtime_truth_contract.json")


class RuntimeTruthContract:
    def __init__(self, contract_path: str = DEFAULT_CONTRACT_PATH):
        self.contract_path = contract_path
        self._contract: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        if self._contract is None:
            with open(self.contract_path, "r") as f:
                self._contract = json.load(f)
        return self._contract

    # --- source-of-truth hierarchy ------------------------------------------

    def source_rank(self, source: str) -> int:
        """Lower rank number = higher authority. Unknown sources rank last."""
        for entry in self.load().get("source_of_truth_hierarchy", []):
            if entry["source"] == source:
                return entry["rank"]
        return 10_000

    def resolve_conflict(self, source_a: str, source_b: str) -> str:
        """Return the authoritative source when two disagree."""
        return source_a if self.source_rank(source_a) <= self.source_rank(source_b) else source_b

    # --- label-state machine ------------------------------------------------

    def state_renders_green(self, state: str) -> bool:
        return bool(self.load().get("label_states", {}).get(state, {}).get("green", False))

    def validate_label(self, state: str, present_evidence_keys: List[str]) -> Dict[str, Any]:
        """Check a label state against the evidence actually supplied."""
        states = self.load().get("label_states", {})
        if state not in states:
            return {"is_valid": False, "reason": f"Unknown label state '{state}'", "missing": []}
        required = states[state].get("requires", [])
        missing = [r for r in required if r not in present_evidence_keys]
        return {
            "is_valid": len(missing) == 0,
            "renders_green": states[state].get("green", False),
            "missing": missing,
            "reason": "ok" if not missing else f"{state} missing evidence: {', '.join(missing)}",
        }

    # --- freshness ----------------------------------------------------------

    def is_fresh(self, evidence_kind: str, produced_at_epoch: float, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        budget = self.load().get("freshness_budgets_seconds", {}).get(evidence_kind)
        if budget is None:
            return False  # unknown kind -> treat as not fresh (fail closed)
        return (now - produced_at_epoch) <= budget

    # --- proportionality tiers ---------------------------------------------

    def tier_requirements(self, tier_key: str) -> Dict[str, Any]:
        return self.load().get("proportionality_tiers", {}).get(tier_key, {})

    def tier_gate(self, tier_key: str, present_evidence_keys: List[str]) -> Dict[str, Any]:
        """Does the supplied evidence satisfy the tier's minimum? Non-blocking
        tiers (T0) always pass."""
        tier = self.tier_requirements(tier_key)
        if not tier:
            return {"is_valid": False, "reason": f"Unknown tier '{tier_key}'", "missing": []}
        if not tier.get("blocking", True):
            return {"is_valid": True, "reason": f"{tier_key} is non-blocking", "missing": []}
        required = tier.get("min_evidence", [])
        missing = [r for r in required if r not in present_evidence_keys]
        return {
            "is_valid": len(missing) == 0,
            "missing": missing,
            "reason": "ok" if not missing else f"{tier_key} missing: {', '.join(missing)}",
        }

    def release_blockers(self) -> List[str]:
        return list(self.load().get("release_blockers", []))


class RuntimeTruthVerdictGuard:
    """Fail-open guard that enforces the label-state machine on a FinalVerdict.

    The only rule it enforces is the contract's core invariant: a verdict may
    render green (status VERIFIED) only when readiness is genuinely not-ready-
    capped. It can only ADD a blocker, never clear one, and it returns
    is_valid=True whenever the inputs are missing or ambiguous, so wiring it in
    cannot spuriously block a currently-passing verdict.
    """

    def __init__(self, contract: Optional[RuntimeTruthContract] = None,
                 not_ready_cap: Optional[float] = None,
                 cap_policy_path: str = os.path.join("config", "readiness_cap_policy.yaml")):
        self.contract = contract or RuntimeTruthContract()
        # Single source of truth: read the not-ready cap from the same policy the
        # ReadinessCapEngine uses, so the two can never drift. Explicit override
        # wins; fall back to 50.0 only if the policy is unreadable.
        if not_ready_cap is not None:
            self.not_ready_cap = not_ready_cap
        else:
            self.not_ready_cap = self._load_not_ready_cap(cap_policy_path, default=50.0)

    @staticmethod
    def _load_not_ready_cap(cap_policy_path: str, default: float) -> float:
        try:
            import yaml
            with open(cap_policy_path, "r") as f:
                policy = yaml.safe_load(f) or {}
            return float(policy["readiness_cap_policy"]["caps"]["not_ready"])
        except Exception:
            return default

    def validate_verdict(self, status: str, readiness_score: Any) -> Dict[str, Any]:
        # Only VERIFIED renders green; every other state is already non-green.
        try:
            renders_green = self.contract.state_renders_green(status)
        except Exception:
            return {"is_valid": True, "reason": "contract unavailable; guard fails open",
                    "violations": []}

        if not renders_green:
            return {"is_valid": True, "reason": f"{status} does not render green",
                    "violations": []}

        try:
            score = float(readiness_score)
        except (TypeError, ValueError):
            return {"is_valid": True, "reason": "readiness score unavailable; guard fails open",
                    "violations": []}

        if score <= self.not_ready_cap:
            v = (f"fake_green: status {status} claims green while readiness "
                 f"{score:.1f} is at/below not-ready cap {self.not_ready_cap:.1f}")
            return {"is_valid": False, "reason": v, "violations": [v]}

        return {"is_valid": True, "reason": "green verdict is contract-legal",
                "violations": []}
