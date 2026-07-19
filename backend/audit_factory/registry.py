from __future__ import annotations
import json
import os
import tempfile

class HAFRegistryManager:
    def __init__(self, registries_dir: str = None):
        self.registries_dir = registries_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/registries")
        )
        os.makedirs(self.registries_dir, exist_ok=True)
        self.assessment_registry_path = os.path.join(self.registries_dir, "assessment_registry.json")
        self.certification_registry_path = os.path.join(self.registries_dir, "certification_registry.json")
        self.evidence_index_path = os.path.join(self.registries_dir, "evidence_index.json")

    def _atomic_write(self, filepath: str, data: dict):
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_path, filepath)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def load_registry(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_assessment_run(self, run_id: str, run_summary: dict):
        registry = self.load_registry(self.assessment_registry_path)
        if "runs" not in registry:
            registry["runs"] = {}
        registry["runs"][run_id] = run_summary
        self._atomic_write(self.assessment_registry_path, registry)

    def save_certification_decision(self, decision: dict):
        registry = self.load_registry(self.certification_registry_path)
        if "decisions" not in registry:
            registry["decisions"] = []
        # Remove older decision with same scope/level
        registry["decisions"] = [
            d for d in registry["decisions"]
            if not (d.get("scope") == decision.get("scope") and d.get("level") == decision.get("level"))
        ]
        registry["decisions"].append(decision)
        self._atomic_write(self.certification_registry_path, registry)

    def index_evidence(self, evidence: dict):
        registry = self.load_registry(self.evidence_index_path)
        if "evidence" not in registry:
            registry["evidence"] = {}
        registry["evidence"][evidence["evidence_id"]] = evidence
        self._atomic_write(self.evidence_index_path, registry)
