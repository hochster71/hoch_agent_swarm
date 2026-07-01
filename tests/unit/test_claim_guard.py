from backend.runtime_truth.claim_guard import ClaimGuard

def test_claim_guard_verify():
    guard = ClaimGuard()
    assert guard.verify_claim("Release version is ready", ["evidence-1"]) is True
    assert guard.verify_claim("", []) is False
