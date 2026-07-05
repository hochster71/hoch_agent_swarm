import json
import os
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

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
            self.base_dir / "data" / "prompt_registry" / "agents.manifest.json"
        ]

    def load_registry(self):
        manifest_path = self.base_dir / "data" / "prompt_registry" / "agents.manifest.json"
        report_path = self.base_dir / "data" / "prompt_registry" / "validation-report.json"
        
        self.prompts = []
        
        if not manifest_path.exists():
            self.status = "FAIL_CLOSED"
            print(f"[prompt_registry] FAIL_CLOSED: Missing manifest.")
            return

        try:
            val_status = "PASS"
            if report_path.exists():
                report_data = json.loads(report_path.read_text(encoding="utf-8"))
                val_status = report_data.get("validation_status")
                if val_status != "GO":
                    self.status = "FAIL_CLOSED"
                    print(f"[prompt_registry] FAIL_CLOSED: Validation status is not GO (was {val_status}).")
                    return
            else:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
                val_status = manifest_data.get("validation_status")
                if val_status not in ["PASS", "GO"]:
                    self.status = "FAIL_CLOSED"
                    print(f"[prompt_registry] FAIL_CLOSED: Manifest validation status is {val_status}.")
                    return
                
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = manifest_data.get("entries", [])
            
            # Map new schema to the legacy schema expected by the rest of the application:
            # - `id` -> `gene_id` (or fallback to `id`)
            # - `category` -> `task_class` (or fallback to `category`)
            mapped_prompts = []
            for entry in entries:
                p_copy = entry.copy()
                p_copy["id"] = entry.get("gene_id") or entry.get("id")
                p_copy["category"] = entry.get("task_class") or entry.get("category")
                mapped_prompts.append(p_copy)
                
            self.prompts = mapped_prompts
            self.status = "LIVE"
            print(f"[prompt_registry] Loaded {len(self.prompts)} active agents successfully. Registry status: {self.status}")
        except Exception as e:
            self.status = "FAIL_CLOSED"
            print(f"[prompt_registry] FAIL_CLOSED: Exception during registry load: {str(e)}")
            return

        self.load_promptops_store()

        security_critical_categories = {
            "SAST", "DAST", "DevSecOps", "Audit", "Governance", "Security Architecture",
            "Vulnerability Management", "Detection Engineering", "Supply Chain", "Privacy",
            "Data Security", "AI / ML Systems"
        }

        # Overlay promptops state and calculate severity onto prompts
        for p in self.prompts:
            pid = p.get("id")
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

        self.write_report(str(manifest_path))

    def load_promptops_store(self):
        store_path = self.base_dir / "data" / "prompt_registry" / "promptops_store.json"
        store_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.promptops_data = {}
        if store_path.exists():
            try:
                self.promptops_data = json.loads(store_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[prompt_registry] WARN: could not read promptops_store ({e}); continuing with empty store")
                
        updated = False
        for p in self.prompts:
            pid = p.get("id")
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

    def log_run_to_ledger(self, run_data: dict):
        ledger_path = self.base_dir / "data" / "prompt_registry" / "evidenceops_ledger.json"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        lock = threading.Lock()
        with lock:
            try:
                if ledger_path.exists():
                    data = json.loads(ledger_path.read_text(encoding="utf-8"))
                else:
                    data = []
            except Exception:
                data = []
                
            data.append(run_data)
            
            try:
                ledger_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[prompt_registry] WARN: could not write usage ledger ({e})")

    def get_manifest_health(self) -> Dict[str, Any]:
        manifest_path = self.base_dir / "data" / "prompt_registry" / "agents.manifest.json"
        report_path = self.base_dir / "data" / "prompt_registry" / "validation-report.json"
        
        def _fail_closed(reason: str) -> Dict[str, Any]:
            print(f"[prompt_registry] get_manifest_health FAIL_CLOSED: {reason}")
            return {
                "schema": "hasf-agent-capability-registry",
                "total_agents": 0,
                "active_agents": 0,
                "deprecated_agents": 0,
                "invalid_agents": 0,
                "gapfill_ids_remaining": 0,
                "duplicate_gene_ids": 0,
                "duplicate_content_hashes": 0,
                "missing_model_targets": 0,
                "validation_status": "FAIL_CLOSED",
                "fail_closed_reason": reason,
                "last_validation_timestamp": "",
                "manifest_path": str(manifest_path)
            }

        if not manifest_path.exists():
            return _fail_closed("MANIFEST_MISSING")

        try:
            report_data = {}
            if report_path.exists():
                report_data = json.loads(report_path.read_text(encoding="utf-8"))
            
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            val_status = report_data.get("validation_status") or manifest_data.get("validation_status")
            
            if val_status not in ["GO", "PASS"]:
                return _fail_closed(f"VALIDATION_STATUS_IS_{val_status}")

            total_agents = manifest_data.get("total_agents") or manifest_data.get("total_genes", 0)
            active_agents = manifest_data.get("active_agents", 0)
            deprecated_agents = manifest_data.get("deprecated_agents", 0)
            duplicate_count = manifest_data.get("duplicate_count") or manifest_data.get("duplicate_gene_ids", 0)
            broken_link_count = manifest_data.get("broken_link_count", 0)

            return {
                "schema": manifest_data.get("schema", "hasf-agent-capability-registry"),
                "name": manifest_data.get("name", "HOCH Agent Capability Registry"),
                "version": manifest_data.get("version", "4.0.0"),
                "created_for": manifest_data.get("created_for", "HOCH Agent Swarm"),
                "total_agents": total_agents,
                "active_agents": active_agents,
                "deprecated_agents": deprecated_agents,
                "duplicate_count": duplicate_count,
                "broken_link_count": broken_link_count,
                "total_genes": total_agents,
                "invalid_agents": manifest_data.get("invalid_agents", 0),
                "gapfill_ids_remaining": manifest_data.get("gapfill_ids_remaining", 0),
                "duplicate_gene_ids": duplicate_count,
                "duplicate_content_hashes": manifest_data.get("duplicate_content_hashes", 0),
                "missing_model_targets": manifest_data.get("missing_model_targets", 0),
                "validation_status": val_status,
                "last_validation_timestamp": report_data.get("timestamp") or manifest_data.get("last_validation_timestamp", ""),
                "manifest_path": str(manifest_path)
            }
        except Exception as e:
            return _fail_closed(f"LOAD_ERROR: {str(e)}")

    def write_report(self, source_used: Optional[str]):
        report_dir = self.base_dir / "artifacts" / "qa" / "prompt_registry"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "prompt_registry_report.json"

        categories = {}
        industries = {}
        
        security_critical_count = 0
        approval_gated_count = 0

        for p in self.prompts:
            cat = p.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
            
            ind = p.get("industry", "Unknown")
            industries[ind] = industries.get(ind, 0) + 1
            
            if p.get("severity") == "HIGH":
                security_critical_count += 1

            if p.get("requires_human_approval"):
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
