from __future__ import annotations
import json
import os
from datetime import datetime, timezone
import jsonschema
from backend.audit_factory.models import Finding

class FindingsEngine:
    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/schemas/finding.schema.json")
        )
        self.schema = None
        if os.path.exists(self.schema_path):
            with open(self.schema_path, "r") as f:
                self.schema = json.load(f)

    def create_finding(
        self,
        control_id: str,
        run_id: str,
        title: str,
        description: str,
        severity: str,
        technical_result: str = "FAIL"
    ) -> Finding:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        finding_id = f"FND-HAF-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{os.urandom(2).hex()}"
        
        finding = Finding(
            finding_id=finding_id,
            control_id=control_id,
            assessment_run_id=run_id,
            title=title,
            description=description,
            severity=severity,
            status="OPEN",
            technical_result=technical_result,
            created_at=now_str
        )

        if self.schema:
            try:
                jsonschema.validate(instance=finding.model_dump(), schema=self.schema)
            except Exception as e:
                # Fallback addition of validation metadata
                finding.description += f" (Schema validation warning: {e})"
                
        return finding
