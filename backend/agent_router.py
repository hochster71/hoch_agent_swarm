import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

class AgentRouter:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        self.base_dir = base_dir
        self.manifest_path = self.base_dir / "data" / "prompt_registry" / "agents.manifest.json"
        self.report_path = self.base_dir / "data" / "prompt_registry" / "validation-report.json"
        self.aliases_path = self.base_dir / "data" / "prompt_registry" / "aliases.yaml"

    def get_registry_status(self) -> str:
        if not self.report_path.exists():
            return "FAIL_CLOSED"
        try:
            report_data = json.loads(self.report_path.read_text(encoding="utf-8"))
            return report_data.get("validation_status", "FAIL_CLOSED")
        except Exception:
            return "FAIL_CLOSED"

    def route(self, classified_task: Dict[str, Any]) -> Dict[str, Any]:
        status = self.get_registry_status()
        if status != "GO":
            raise ValueError(f"Registry status is not GO (was {status}). Routing blocked.")

        if not self.manifest_path.exists():
            raise FileNotFoundError("agents.manifest.json is missing.")

        manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        entries = manifest_data.get("entries", [])

        # Load deprecated aliases
        deprecated_ids = set()
        # Also try the prompt_library path as fallback
        library_aliases = Path("/Users/michaelhoch/hoch_agent_swarm_prompt_library/deprecated/aliases.yaml")
        aliases_to_check = [self.aliases_path, library_aliases]
        for path in aliases_to_check:
            if path.exists():
                try:
                    aliases_data = yaml.safe_load(path.read_text(encoding="utf-8"))
                    for a in aliases_data.get("aliases", []):
                        deprecated_ids.add(a.get("gapfill_id"))
                except Exception:
                    pass

        target_domain = classified_task.get("domain", "")
        target_industry = classified_task.get("industry", "")
        target_phase = classified_task.get("mission_phase", "")
        target_role = classified_task.get("runtime_role", "")
        target_risk = classified_task.get("risk_level", "LOW")

        scored_candidates = []
        for agent in entries:
            agent_id = agent.get("gene_id")
            
            # Exclude deprecated aliases
            if agent_id in deprecated_ids or agent.get("status") != "active":
                continue

            score = 0
            
            # Exact domain match
            if agent.get("domain") == target_domain:
                score += 10
                
            # Exact industry match
            if agent.get("industry") == target_industry:
                score += 5
            elif agent.get("industry") == "All Industries":
                score += 2
                
            # Mission phase match
            if agent.get("mission_phase") == target_phase:
                score += 3
                
            # Runtime role match
            if agent.get("runtime_role") == target_role:
                score += 3
                
            # Safety tier compatibility
            tier = agent.get("max_execution_tier", "T2_DRAFT_REMEDIATOR")
            if target_risk == "HIGH":
                if tier in ["T3_STAGED_WRITER", "T4_CONTROLLED_EXECUTOR", "T5_PRODUCTION_ACTOR"]:
                    score += 2
            else:
                score += 2
                
            # Local model ok
            if agent.get("local_model_ok"):
                score += 1
                
            # Evidence required
            if agent.get("evidence_required"):
                score += 1

            scored_candidates.append({
                "agent": agent,
                "score": score
            })

        # Sort: descending by score, ascending by gene_id for ties
        scored_candidates.sort(key=lambda x: (-x["score"], x["agent"]["gene_id"]))

        top_candidates = []
        for item in scored_candidates[:3]:
            top_candidates.append({
                "gene_id": item["agent"]["gene_id"],
                "title": item["agent"]["title"],
                "score": item["score"],
                "max_execution_tier": item["agent"]["max_execution_tier"],
                "requires_human_approval": item["agent"]["requires_human_approval"]
            })

        winner = scored_candidates[0]["agent"] if scored_candidates else None
        
        return {
            "winner": winner,
            "candidates": top_candidates,
            "registry_version": manifest_data.get("version", "1.0.0")
        }
