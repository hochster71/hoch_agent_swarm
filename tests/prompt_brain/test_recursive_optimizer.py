from unittest import mock
from backend.brain_convergence import recursive_optimizer as ro

BACKEND = {"kind": "ollama", "base": "http://x", "model": "llama3"}
CHAMP = {"gene_id": "c1", "prompt": "scope: edit x. evidence required with timestamp. rollback on failure."}


def test_no_backend_returns_none():
    with mock.patch.object(ro, "detect_local_backend", return_value=None):
        assert ro.recursive_improve_champion(CHAMP, "Cyber") is None


def test_recursive_improvement_success():
    better = ("ROLE + SCOPE: edit only x.py (non-goals listed). METHOD: verify runtime truth via API. "
              "EVIDENCE: artifact path + timestamp + hash. ANTI-FAKE-GREEN: seeded-fault negative test. "
              "OUTPUT: STATUS json. ROLLBACK: revert on red gate. INTEGRATION: regression checks.")
    
    with mock.patch.object(ro, "_ollama_generate", return_value=better):
        with mock.patch.object(ro, "llm_judge", return_value={"winner": "B", "raw": "B is more disciplined"}):
            out = ro.recursive_improve_champion(CHAMP, "Cyber", k=2, backend=BACKEND)
            assert out is not None
            assert out["state"] == "RECURSIVELY_IMPROVED"
            assert out["mech_score"] > 0
