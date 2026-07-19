from __future__ import annotations
import hashlib
import json
import os
from datetime import datetime, timezone
import jsonschema
from backend.audit_factory.models import Evidence

class EvidenceValidator:
    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/schemas/evidence.schema.json")
        )
        self.schema = None
        if os.path.exists(self.schema_path):
            with open(self.schema_path, "r") as f:
                self.schema = json.load(f)

    def validate_evidence(self, evidence: Evidence, root_dir: str = None) -> bool:
        """Validates evidence structure, recomputes artifact hash, and checks freshness."""
        if self.schema:
            try:
                jsonschema.validate(instance=evidence.model_dump(), schema=self.schema)
            except Exception as e:
                evidence.status = "INVALID"
                evidence.metadata["validation_error"] = f"Schema validation failed: {e}"
                return False

        # Recompute SHA-256 from local file
        target_path = evidence.source_path
        if root_dir:
            # If path is relative to repo root, resolve against it
            if not os.path.isabs(target_path):
                target_path = os.path.join(root_dir, target_path)

        if not os.path.exists(target_path):
            evidence.status = "INVALID"
            evidence.metadata["validation_error"] = f"Artifact missing at {target_path}"
            return False

        try:
            sha256_hash = hashlib.sha256()
            with open(target_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            computed_hash = sha256_hash.hexdigest()
        except Exception as e:
            evidence.status = "INVALID"
            evidence.metadata["validation_error"] = f"Read failed: {e}"
            return False

        if computed_hash != evidence.sha256:
            evidence.status = "INVALID"
            evidence.metadata["validation_error"] = (
                f"Cryptographic hash mismatch. Expected: {evidence.sha256}, Got: {computed_hash}"
            )
            return False

        # Freshness evaluation
        try:
            # Handle possible trailing Z in ISO formats
            fresh_str = evidence.fresh_until.replace("Z", "+00:00")
            fresh_dt = datetime.fromisoformat(fresh_str)
            now_dt = datetime.now(timezone.utc)
            if now_dt > fresh_dt:
                evidence.status = "STALE"
                evidence.metadata["validation_error"] = f"Evidence expired at {evidence.fresh_until}"
                return False
        except Exception as e:
            evidence.status = "INVALID"
            evidence.metadata["validation_error"] = f"Invalid freshness timestamp: {e}"
            return False

        evidence.status = "VALID"
        return True
