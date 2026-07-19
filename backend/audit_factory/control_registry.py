from __future__ import annotations
import json
import os
from typing import Dict, List, Optional
import yaml
import jsonschema
from backend.audit_factory.models import Control

class ControlRegistry:
    def __init__(self, catalog_path: str = None, schema_path: str = None):
        self.catalog_path = catalog_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/catalogs/control_catalog.yaml")
        )
        self.schema_path = schema_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/schemas/control.schema.json")
        )
        self.controls: Dict[str, Control] = {}
        self.load_and_validate()

    def load_and_validate(self):
        if not os.path.exists(self.catalog_path):
            raise FileNotFoundError(f"Control catalog not found at {self.catalog_path}")
        if not os.path.exists(self.schema_path):
            raise FileNotFoundError(f"Control schema not found at {self.schema_path}")

        with open(self.schema_path, "r") as f:
            schema = json.load(f)

        with open(self.catalog_path, "r") as f:
            data = yaml.safe_load(f)

        controls_list = data.get("controls", [])
        for ctrl_dict in controls_list:
            # Enforce string types for validation where required by schema
            ctrl_dict["control_id"] = str(ctrl_dict.get("control_id", ""))
            ctrl_dict["version"] = str(ctrl_dict.get("version", ""))
            ctrl_dict["level"] = str(ctrl_dict.get("level", ""))
            ctrl_dict["domain"] = str(ctrl_dict.get("domain", ""))
            ctrl_dict["family"] = str(ctrl_dict.get("family", ""))
            ctrl_dict["title"] = str(ctrl_dict.get("title", ""))
            ctrl_dict["requirement"] = str(ctrl_dict.get("requirement", ""))
            ctrl_dict["severity"] = str(ctrl_dict.get("severity", ""))
            ctrl_dict["failure_effect"] = str(ctrl_dict.get("failure_effect", ""))
            ctrl_dict["status"] = str(ctrl_dict.get("status", "NOT_ASSESSED"))
            
            # Validate against schema
            jsonschema.validate(instance=ctrl_dict, schema=schema)
            
            # Parse to Pydantic
            ctrl = Control(**ctrl_dict)
            self.controls[ctrl.control_id] = ctrl

    def get_control(self, control_id: str) -> Optional[Control]:
        return self.controls.get(control_id)

    def list_controls(self) -> List[Control]:
        return list(self.controls.values())
