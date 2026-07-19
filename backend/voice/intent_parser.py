from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Mapping patterns to intents
_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"enable.*hold|place.*hold|turn on.*hold", re.IGNORECASE), "helm.operator_hold.enable"),
    (re.compile(r"disable.*hold|release.*hold|turn off.*hold", re.IGNORECASE), "helm.operator_hold.disable"),
    (re.compile(r"operator.*hold.*status|is.*hold.*active", re.IGNORECASE), "helm.operator_hold.status"),
    
    (re.compile(r"run.*conmon|run.*continuous.*monitoring|trigger.*conmon", re.IGNORECASE), "helm.conmon.run"),
    (re.compile(r"start.*assessment|run.*assessment|trigger.*assessment", re.IGNORECASE), "helm.assessment.start"),
    
    (re.compile(r"mark.*in.*progress", re.IGNORECASE), "helm.finding.mark_in_progress"),
    (re.compile(r"mark.*ready.*retest|mark.*for.*retest", re.IGNORECASE), "helm.finding.mark_ready_for_retest"),
    
    (re.compile(r"open.*findings|findings|poam", re.IGNORECASE), "helm.audit.open_findings"),
    (re.compile(r"control.*status|check.*control", re.IGNORECASE), "helm.audit.control_status"),
    (re.compile(r"latest.*assessment|last.*assessment|assessment.*stats", re.IGNORECASE), "helm.audit.latest_assessment"),
    (re.compile(r"audit.*posture|integrity.*posture|posture", re.IGNORECASE), "helm.audit.posture"),
    
    (re.compile(r"production.*authority", re.IGNORECASE), "helm.production_authority"),
    (re.compile(r"status.*summary|overall.*status|system.*status", re.IGNORECASE), "helm.status.summary"),
    (re.compile(r"runtime.*health|is.*healthy|leases|concurrency", re.IGNORECASE), "helm.runtime.health"),
    (re.compile(r"online.*agents|agents.*online|who is online", re.IGNORECASE), "helm.agents.online"),
    (re.compile(r"blockers|what is blocking", re.IGNORECASE), "helm.blockers.list"),
    (re.compile(r"mission.*progress|progress.*mission", re.IGNORECASE), "helm.mission.progress"),
    (re.compile(r"factory.*status|factories", re.IGNORECASE), "helm.factory.status"),
    
    (re.compile(r"help|commands|what.*say", re.IGNORECASE), "helm.help")
]

def parse_intent(utterance: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Parse free-text utterance, returning (intent_name, parameters)."""
    if not utterance:
        return None, {}
    
    utterance_clean = utterance.strip()
    
    # Try pattern matching
    for pattern, intent in _RULES:
        if pattern.search(utterance_clean):
            params = {}
            # Extract control_id if present (e.g. HAF-QUEUE-001)
            ctrl_match = re.search(r"\b(HAF-[A-Z]+-[0-9]+)\b", utterance_clean, re.IGNORECASE)
            if ctrl_match:
                params["control_id"] = ctrl_match.group(1).upper()
                
            # Extract finding_id if present (e.g. FND-HAF-20260719-8711)
            fnd_match = re.search(r"\b(FND-HAF-[0-9a-fA-F\-]+)\b", utterance_clean, re.IGNORECASE)
            if fnd_match:
                params["finding_id"] = fnd_match.group(1).upper()

            # Extract profile if present
            prof_match = re.search(r"profile\s+(\w+)", utterance_clean, re.IGNORECASE)
            if prof_match:
                params["profile"] = prof_match.group(1).lower()

            return intent, params

    return None, {}
