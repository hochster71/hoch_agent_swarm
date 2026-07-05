import pytest
from backend.staging_manager import run_staging_validation
from backend.main import api_get_staging_dry_run

def test_run_staging_validation():
    res = run_staging_validation()
    
    assert res["status"] in ["PASS", "FAIL", "WARN"]
    assert res["staging_tag"] == "v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY-staging"
    assert "checkpoints" in res
    assert len(res["checkpoints"]) > 0
    
    # Verify presence of key checkpoints
    names = [cp["name"] for cp in res["checkpoints"]]
    assert "Health Endpoints Probe" in names
    assert "Preflight Gate Check" in names
    assert "Immutable Ledger Verification" in names
    assert "Rollback Path Readiness" in names
    
    # Verify safety language
    assert res["compliance"]["statement"] == "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW"
    assert "The system has ATO-supporting evidence prepared for review" in res["compliance"]["notice"]
    assert "Actual ATO has not been granted" in res["compliance"]["notice"]
    assert "No authorization claim is being made" in res["compliance"]["notice"]

def test_staging_api_endpoint():
    res = api_get_staging_dry_run()
    assert res["staging_tag"] == "v0.1.6-ERROR-BUDGET-AWARE-AUTONOMY-staging"
    assert res["compliance"]["statement"] == "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW"

def test_production_readiness_derive_only():
    from backend.main import production_readiness
    from unittest.mock import patch
    
    # 1. Blocked system -> NO-GO
    with patch("backend.final_verifier.final_verdict.FinalVerdict.get_final_verdict") as mock_fv:
        mock_fv.return_value = {
            "status": "BLOCKED",
            "readiness_score": 90.0,
            "readiness_caps": ["git working tree is dirty"]
        }
        res = production_readiness()
        assert res["go_no_go"] == "NO-GO"

    # 2. Verified system but not authorized -> PENDING_VERIFICATION
    with patch("backend.final_verifier.final_verdict.FinalVerdict.get_final_verdict") as mock_fv, \
         patch("backend.main.os.path.exists", return_value=False):
        mock_fv.return_value = {
            "status": "VERIFIED",
            "readiness_score": 100.0,
            "readiness_caps": []
        }
        res = production_readiness()
        assert res["go_no_go"] == "PENDING_VERIFICATION"

