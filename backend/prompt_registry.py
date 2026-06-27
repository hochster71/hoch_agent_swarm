import json
from pathlib import Path
from typing import Dict, Any, List, Optional

class PromptRegistry:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        self.base_dir = base_dir
        self.prompts: List[Dict[str, Any]] = []
        self.status = "FAIL_CLOSED"
        self.load_registry()

    def get_source_paths(self) -> List[Path]:
        return [
            self.base_dir / "backend" / "prompt_library.json",
            Path("/Users/michaelhoch/hoch_agent_swarm_prompt_library/hoch_agent_swarm_prompt_library.json"),
            self.base_dir / "hoch_agent_swarm_prompt_library.json"
        ]

    def load_registry(self):
        loaded_data = None
        source_used = None
        
        for path in self.get_source_paths():
            if path.exists():
                try:
                    loaded_data = json.loads(path.read_text(encoding="utf-8"))
                    source_used = str(path)
                    break
                except Exception:
                    continue

        if not loaded_data or not isinstance(loaded_data, list):
            self.status = "FAIL_CLOSED"
            self.prompts = []
            self.write_report(None)
            return

        valid_prompts = []
        required_fields = ["id", "category", "industry", "title", "mission", "outputs", "prompt"]
        
        for p in loaded_data:
            if all(p.get(field) for field in required_fields):
                valid_prompts.append(p)

        self.prompts = valid_prompts
        count = len(self.prompts)
        
        if count >= 100:
            self.status = "LIVE"
        elif count > 0:
            self.status = "DEGRADED"
        else:
            self.status = "FAIL_CLOSED"

        self.write_report(source_used)

    def write_report(self, source_used: Optional[str]):
        report_dir = self.base_dir / "artifacts" / "qa" / "prompt_registry"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "prompt_registry_report.json"

        categories = {}
        industries = {}
        security_critical_categories = {
            "SAST", "DAST", "DevSecOps", "Audit", "Governance", "Security Architecture",
            "Vulnerability Management", "Detection Engineering", "Supply Chain", "Privacy",
            "Data Security", "AI / ML Systems"
        }
        
        security_critical_count = 0
        approval_gated_count = 0

        for p in self.prompts:
            cat = p["category"]
            categories[cat] = categories.get(cat, 0) + 1
            
            ind = p["industry"]
            industries[ind] = industries.get(ind, 0) + 1
            
            if cat in security_critical_categories:
                security_critical_count += 1

            # Determine if prompt is approval gated based on category or content
            prompt_text = p["prompt"].lower()
            if cat in ["Governance", "DevSecOps", "Operations", "Incident Response"] or any(
                kw in prompt_text for kw in ["delete", "deploy", "publish", "credentials", "firewall", "quarantine", "waiver", "override"]
            ):
                approval_gated_count += 1

        report = {
            "status": self.status,
            "total_prompts": len(self.prompts),
            "source_used": source_used,
            "categories": categories,
            "industries": industries,
            "security_critical_count": security_critical_count,
            "approval_gated_count": approval_gated_count
        }

        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

# Global singleton
_registry_instance = None

def get_registry() -> PromptRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = PromptRegistry()
    return _registry_instance
