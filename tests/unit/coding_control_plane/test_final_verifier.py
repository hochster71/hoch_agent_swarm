from backend.coding_control_plane.final_verifier import FinalVerifier

def test_final_verifier_blocks_forbidden_claims():
    verifier = FinalVerifier()
    
    # Report contains forbidden absolute wording ("production ready" and "no blockers")
    res = verifier.verify_final_report("The system is fully complete, production ready, and has no blockers.", active_gates_pass=False, remaining_blockers=["some_defect"])
    assert res["status"] == "BLOCKED"
    assert "production ready" in res["reason"]

def test_final_verifier_allows_clean_report():
    verifier = FinalVerifier()
    
    # Report has no forbidden words
    res = verifier.verify_final_report("The patch is successfully applied and active gates pass.", active_gates_pass=True, remaining_blockers=[])
    assert res["status"] == "VERIFIED"
    assert res["confidence_cap"] == 100.0
