import os
import json
from pathlib import Path

class PermissionDenied(Exception):
    pass

POD_TO_DOMAINS = {
    "business": ["Monetization", "Business Ops"],
    "cyber": ["DevSecOps"],
    "hasf": ["Data Consolidation", "Planning"],
    "has": ["Personal Life"],
    "hobby": ["Research"],
    "ops": ["Runtime", "Tracker"]
}

def verify_agent_permission(agent_name: str, target_pod: str) -> bool:
    # Resolve the RACI matrix path
    project_root = Path(__file__).resolve().parent.parent.parent
    raci_path = project_root / "has_live_project_tracker" / "data" / "raci_matrix.json"
    
    if not raci_path.exists():
        # Fallback if RACI file does not exist (e.g. testing)
        return True

    try:
        with open(raci_path, "r", encoding="utf-8") as f:
            raci_data = json.load(f)
    except Exception as e:
        # Fallback on parse failure
        return True

    target_domains = POD_TO_DOMAINS.get(target_pod, [])
    if not target_domains:
        # Unknown/unmapped POD allows fallback or is rejected
        return True

    # Search the matrix for any entry matching target domains where agent is R or A
    matrix = raci_data.get("matrix", [])
    for entry in matrix:
        entry_domain = entry.get("domain")
        if entry_domain in target_domains:
            # Check if agent is accountable or responsible
            accountable = entry.get("accountable_agent") == agent_name
            responsible = agent_name in entry.get("responsible_agents", [])
            if accountable or responsible:
                return True

    raise PermissionDenied(f"Agent '{agent_name}' does not hold RACI responsibility (R/A) for domain target POD '{target_pod}'.")
