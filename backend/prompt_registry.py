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
            self.base_dir / "data" / "prompt_registry" / "hoch_agent_swarm_prompt_library_v3_enhanced.json",
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

        if not loaded_data:
            self.status = "FAIL_CLOSED"
            self.prompts = []
            self.write_report(None)
            return

        # Extract prompts list if wrapped in a dict
        prompts_list = []
        if isinstance(loaded_data, dict) and "prompts" in loaded_data:
            prompts_list = loaded_data["prompts"]
        elif isinstance(loaded_data, list):
            prompts_list = loaded_data
        else:
            self.status = "FAIL_CLOSED"
            self.prompts = []
            self.write_report(source_used)
            return

        valid_prompts = []
        required_fields = ["id", "category", "industry", "title", "mission", "outputs"]
        
        for p in prompts_list:
            if "prompt_text" in p and "prompt" not in p:
                p["prompt"] = p["prompt_text"]
            if all(p.get(field) for field in required_fields) and p.get("prompt"):
                valid_prompts.append(p)

        self.prompts = valid_prompts
        count = len(self.prompts)
        
        if count >= 100:
            self.status = "LIVE"
        elif count > 0:
            self.status = "DEGRADED"
        else:
            self.status = "FAIL_CLOSED"

        self.load_promptops_store()

        security_critical_categories = {
            "SAST", "DAST", "DevSecOps", "Audit", "Governance", "Security Architecture",
            "Vulnerability Management", "Detection Engineering", "Supply Chain", "Privacy",
            "Data Security", "AI / ML Systems"
        }

        # Overlay promptops state and calculate severity onto prompts
        for p in self.prompts:
            pid = p["id"]
            cat = p.get("category", "Unknown")
            prompt_text = p.get("prompt", "").lower()
            
            if cat in security_critical_categories or any(kw in prompt_text for kw in ["delete", "deploy", "publish", "credentials", "firewall", "quarantine", "waiver", "override"]):
                sev = "HIGH"
            elif cat in ["Privacy", "Data Security"] or any(kw in prompt_text for kw in ["private data", "home", "privacy"]):
                sev = "MEDIUM"
            else:
                sev = "LOW"
            p["severity"] = sev
            p["calculated_risk"] = sev

            if hasattr(self, "promptops_data") and pid in self.promptops_data:
                entry = self.promptops_data[pid]
                p["lifecycle_state"] = entry.get("lifecycle_state", "active")
                p["usage_count"] = entry.get("usage_count", 0)
                p["failure_count"] = entry.get("failure_count", 0)
                p["last_run_timestamp"] = entry.get("last_run_timestamp")
                p["approval_metadata"] = entry.get("approval_metadata")
                p["last_known_hash"] = entry.get("last_known_hash")
            else:
                p["lifecycle_state"] = "active"
                p["usage_count"] = 0
                p["failure_count"] = 0
                p["last_run_timestamp"] = None
                p["approval_metadata"] = None

        self.write_report(source_used)

    def load_promptops_store(self):
        import hashlib
        store_path = self.base_dir / "data" / "prompt_registry" / "promptops_store.json"
        store_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.promptops_data = {}
        if store_path.exists():
            try:
                self.promptops_data = json.loads(store_path.read_text(encoding="utf-8"))
            except Exception:
                pass
                
        updated = False
        for p in self.prompts:
            pid = p["id"]
            p_text = p.get("prompt", "")
            current_hash = hashlib.sha256(p_text.encode("utf-8")).hexdigest()
            original_hash = p.get("hash") or current_hash
            
            if pid not in self.promptops_data:
                self.promptops_data[pid] = {
                    "prompt_id": pid,
                    "lifecycle_state": "active",
                    "usage_count": 0,
                    "failure_count": 0,
                    "last_run_timestamp": None,
                    "last_known_hash": current_hash,
                    "original_hash": original_hash,
                    "approval_metadata": None
                }
                updated = True
            else:
                entry = self.promptops_data[pid]
                if entry.get("last_known_hash") != current_hash:
                    app_meta = entry.get("approval_metadata")
                    if not app_meta or app_meta.get("approved_hash") != current_hash:
                        entry["lifecycle_state"] = "review_required"
                    entry["last_known_hash"] = current_hash
                    updated = True
                    
        if updated or not store_path.exists():
            store_path.write_text(json.dumps(self.promptops_data, indent=2), encoding="utf-8")

    def save_promptops_store(self):
        store_path = self.base_dir / "data" / "prompt_registry" / "promptops_store.json"
        store_path.write_text(json.dumps(self.promptops_data, indent=2), encoding="utf-8")

    def increment_usage(self, prompt_id: str, success: bool):
        if hasattr(self, "promptops_data") and prompt_id in self.promptops_data:
            from datetime import datetime, timezone
            entry = self.promptops_data[prompt_id]
            entry["usage_count"] = entry.get("usage_count", 0) + 1
            if not success:
                entry["failure_count"] = entry.get("failure_count", 0) + 1
            entry["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()
            self.save_promptops_store()
            
            # Keep prompts list in sync
            for p in self.prompts:
                if p["id"] == prompt_id:
                    p["usage_count"] = entry["usage_count"]
                    p["failure_count"] = entry["failure_count"]
                    p["last_run_timestamp"] = entry["last_run_timestamp"]
            
    def update_prompt_state(self, prompt_id: str, state: str, approval_metadata: Optional[Dict[str, Any]] = None):
        if hasattr(self, "promptops_data") and prompt_id in self.promptops_data:
            entry = self.promptops_data[prompt_id]
            entry["lifecycle_state"] = state
            if approval_metadata:
                entry["approval_metadata"] = approval_metadata
            self.save_promptops_store()
            
            # Keep prompts list in sync
            for p in self.prompts:
                if p["id"] == prompt_id:
                    p["lifecycle_state"] = state
                    if approval_metadata:
                        p["approval_metadata"] = approval_metadata

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
