from __future__ import annotations
from backend.audit_factory.models import Evidence

class ProvenanceValidator:
    def validate_provenance(self, evidence: Evidence) -> bool:
        """Verifies producer, validator, and version references are properly registered."""
        if not evidence.producer or evidence.producer == "UNKNOWN":
            evidence.metadata["provenance_error"] = "Missing or untrusted evidence producer."
            return False

        if not evidence.validator or evidence.validator == "UNKNOWN":
            evidence.metadata["provenance_error"] = "Missing independent validator identifier."
            return False

        # If it's a file-based target under Git, ensure commit_sha is captured
        if evidence.source_type == "FILE" and not evidence.commit_sha:
            evidence.metadata["provenance_warning"] = "Missing version control tracking reference (commit_sha)."
            
        return True
