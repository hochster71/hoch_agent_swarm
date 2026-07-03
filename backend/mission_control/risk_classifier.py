"""Capability-based risk classification (H2 remediation).

The audit flagged that approval_gate.py classified risk by matching substrings
in the task DESCRIPTION ("deploy", "spend", "production"). Behavioral/text
defenses are adversarially manipulable: an agent that rephrases a task as
"promote build to customer environment" evades the keyword set entirely.

The security literature is consistent on the fix: classify by the CAPABILITIES
a task actually requests, not by what it says. Structural gating (withholding
or escalating on a capability) removes the means of evasion, whereas keyword
matching only reduces its probability. We adopt the widely-used five ascending
risk tiers (read_only < write < execute < network < destructive), consistent
with least-privilege tool-tiering in recent agent-security frameworks and the
classic Saltzer & Schroeder (1975) least-privilege principle.

Risk is the MAX tier over all requested capabilities. Text keywords are kept
only as a NON-DOWNGRADABLE secondary signal: they can raise the tier (defence
in depth) but can never lower the capability-derived floor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Set

# Ordered tiers; index == severity.
TIERS = ["READ_ONLY", "WRITE", "EXECUTE", "NETWORK", "DESTRUCTIVE"]
TIER_INDEX = {t: i for i, t in enumerate(TIERS)}

# Map each capability to its intrinsic tier. Unknown capabilities default to
# EXECUTE (fail-safe: assume more dangerous than write, less than network).
CAPABILITY_TIERS = {
    # read
    "read": "READ_ONLY", "summarization": "READ_ONLY", "document_review": "READ_ONLY",
    "research": "READ_ONLY", "qa": "READ_ONLY", "local_reasoning": "READ_ONLY",
    "code_review": "READ_ONLY", "multimodal_review": "READ_ONLY",
    "display": "READ_ONLY", "mobile_dashboard": "READ_ONLY", "heartbeat": "READ_ONLY",
    # write
    "build": "WRITE", "write": "WRITE", "artifact_write": "WRITE",
    "evidence_write": "WRITE", "automation": "WRITE",
    # execute
    "compute": "EXECUTE", "execute": "EXECUTE", "spatial": "EXECUTE",
    "control_plane": "EXECUTE",
    # network
    "network": "NETWORK", "relay": "NETWORK", "api": "NETWORK",
    "external_fetch": "NETWORK", "publish": "NETWORK",
    # destructive / high-authority
    "deploy": "DESTRUCTIVE", "delete": "DESTRUCTIVE", "payment": "DESTRUCTIVE",
    "spend": "DESTRUCTIVE", "secrets": "DESTRUCTIVE", "credentials": "DESTRUCTIVE",
    "prod_deployment": "DESTRUCTIVE", "package_publish": "DESTRUCTIVE",
    "git_tag_mutation": "DESTRUCTIVE", "artifact_signing": "DESTRUCTIVE",
    "approval_terminal": "DESTRUCTIVE",  # can authorize others -> highest
    "family_data": "DESTRUCTIVE", "private_data": "DESTRUCTIVE",
}

# Text signals that can only ESCALATE (never downgrade). Kept as defence in
# depth for tasks whose capability set under-declares their true intent.
_ESCALATION_KEYWORDS = {
    "DESTRUCTIVE": ["deploy", "publish", "delete", "spend", "app store", "app-store",
                    "firewall", "router", "secrets", "credentials", "family",
                    "private data", "production", "prod ", "wire transfer",
                    "payment", "charge card", "model deletion", "bypass approval",
                    "ignore security", "override gate"],
    "NETWORK": ["external", "internet", "fetch url", "outbound", "webhook"],
}

# Tier -> control decision. Everything at EXECUTE and above needs a human;
# DESTRUCTIVE additionally requires a founder signature (see approval_gate).
_TIER_DECISION = {
    "READ_ONLY": ("ALLOW", False, "LOW"),
    "WRITE": ("ALLOW", False, "LOW"),
    "EXECUTE": ("APPROVAL_REQUIRED", True, "MEDIUM"),
    "NETWORK": ("APPROVAL_REQUIRED", True, "HIGH"),
    "DESTRUCTIVE": ("APPROVAL_REQUIRED", True, "CRITICAL"),
}


@dataclass
class RiskAssessment:
    tier: str
    decision: str
    human_approval_required: bool
    risk_level: str
    reasons: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "decision": self.decision,
            "human_approval_required": self.human_approval_required,
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "capabilities": self.capabilities,
        }


def _tier_of_capability(cap: str) -> str:
    return CAPABILITY_TIERS.get(cap.lower().strip(), "EXECUTE")  # unknown -> EXECUTE (fail-safe)


def _max_tier(a: str, b: str) -> str:
    return a if TIER_INDEX[a] >= TIER_INDEX[b] else b


def classify(capabilities: Iterable[str], task_description: str = "") -> RiskAssessment:
    """Classify risk as the MAX capability tier, escalated (never lowered) by
    text signals. Fail-safe: empty capability set is treated as EXECUTE."""
    caps = [c for c in (capabilities or []) if c]
    reasons: List[str] = []

    if not caps:
        tier = "EXECUTE"
        reasons.append("No capabilities declared — defaulting to EXECUTE (fail-safe).")
    else:
        tier = "READ_ONLY"
        for c in caps:
            ct = _tier_of_capability(c)
            if ct == "EXECUTE" and c.lower() not in CAPABILITY_TIERS:
                reasons.append(f"Unknown capability '{c}' → EXECUTE (fail-safe).")
            tier = _max_tier(tier, ct)
        reasons.append(f"Capability floor: {tier} (from {caps}).")

    # Escalation-only keyword pass.
    tl = (task_description or "").lower()
    for esc_tier, words in _ESCALATION_KEYWORDS.items():
        hit = next((w for w in words if w in tl), None)
        if hit and TIER_INDEX[esc_tier] > TIER_INDEX[tier]:
            reasons.append(f"Text signal '{hit}' escalates {tier} → {esc_tier}.")
            tier = esc_tier

    decision, approval, level = _TIER_DECISION[tier]
    return RiskAssessment(
        tier=tier, decision=decision, human_approval_required=approval,
        risk_level=level, reasons=reasons, capabilities=caps,
    )
