from __future__ import annotations
import os
from typing import Dict, List, Set
import yaml
from backend.audit_factory.control_registry import ControlRegistry
from backend.audit_factory.profile_loader import ProfileLoader
from backend.audit_factory.models import Control

class AssessmentPlanner:
    def __init__(self, control_registry: ControlRegistry, profile_loader: ProfileLoader, procedures_path: str = None):
        self.control_registry = control_registry
        self.profile_loader = profile_loader
        self.procedures_path = procedures_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/procedures/assessment_procedures.yaml")
        )
        self.procedures: Dict[str, dict] = {}
        self.load_procedures()

    def load_procedures(self):
        if os.path.exists(self.procedures_path):
            with open(self.procedures_path, "r") as f:
                data = yaml.safe_load(f)
            for proc in data.get("procedures", []):
                self.procedures[proc["id"]] = proc

    def plan_assessment(self, profile_name: str) -> List[Control]:
        active_control_ids = self.profile_loader.resolve_profile(profile_name)
        planned_controls = []
        for cid in active_control_ids:
            ctrl = self.control_registry.get_control(cid)
            if ctrl:
                planned_controls.append(ctrl)
        
        # Sort logically: dependencies / levels first (L0 -> L1 -> L2 -> L3 -> L4)
        planned_controls.sort(key=lambda x: x.level)
        return planned_controls
