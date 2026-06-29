import os
import pytest
from backend.final_verifier.evidence_validator import EvidenceValidator

def test_evidence_validator_scans_docs():
    # Write a temporary evidence file containing absolute claims
    os.makedirs("docs/evidence/test", exist_ok=True)
    temp_path = "docs/evidence/test/temp_evidence_absolute.md"
    with open(temp_path, "w") as f:
        f.write("# Verification Report\nWe are 100% complete and fully secure.")

    validator = EvidenceValidator(evidence_dir="docs/evidence/test")
    res = validator.validate_recent_evidence()
    assert res["is_valid"] is False
    assert any("100%" in v or "fully secure" in v for v in res.get("violations", []))

    # Clean up
    if os.path.exists(temp_path):
        os.remove(temp_path)
