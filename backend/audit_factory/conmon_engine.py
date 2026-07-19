from __future__ import annotations
import json
import os
from datetime import datetime, timezone
import jsonschema
from backend.audit_factory.models import ConMonSignal

class ConMonEngine:
    # Narrow dependency mapping from mutated files to control IDs
    FILE_DEPENDENCY_MAP = {
        "backend/council/founder_gate.py": ["HAF-GOV-001", "HAF-GOV-002", "HAF-GOV-003", "HAF-GOV-004", "HAF-GOV-005", "HAF-GOV-006"],
        "backend/hochster_runtime_audit.py": ["HAF-TRUTH-001", "HAF-TRUTH-002", "HAF-TRUTH-003", "HAF-TRUTH-004", "HAF-TRUTH-005", "HAF-TRUTH-006"],
        "scripts/helm_autoloop.sh": ["HAF-TRUTH-001", "HAF-TRUTH-005"],
        "scripts/helm_restart_api.sh": ["HAF-REC-001", "HAF-REC-002"],
        "coordination/audit_factory/catalogs/control_catalog.yaml": ["HAF-CONMON-001"],
        "pyproject.toml": ["HAF-SEC-003"],
        "poetry.lock": ["HAF-SEC-003"],
        "package-lock.json": ["HAF-SEC-003"]
    }

    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/schemas/conmon_signal.schema.json")
        )
        self.schema = None
        if os.path.exists(self.schema_path):
            with open(self.schema_path, "r") as f:
                self.schema = json.load(f)

    def evaluate_file_change(self, relative_file_path: str) -> list[ConMonSignal]:
        """Creates a ConMon signal if a mutated file maps to specific controls."""
        impacted = self.FILE_DEPENDENCY_MAP.get(relative_file_path, [])
        if not impacted:
            # Fallback: if not mapped specifically, do not trigger signal
            return []

        signal_id = f"SIG-HAF-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{os.urandom(2).hex()}"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        signal = ConMonSignal(
            signal_id=signal_id,
            signal_type="FILE_CHANGE",
            target=relative_file_path,
            observed_at=now_str,
            previous_state="STABLE",
            new_state="MUTATED",
            impacted_controls=impacted,
            severity="HIGH"
        )

        if self.schema:
            jsonschema.validate(instance=signal.model_dump(), schema=self.schema)

        return [signal]
