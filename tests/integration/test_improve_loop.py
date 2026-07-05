from unittest import mock
from backend.brain_convergence import improve_loop as il

BACKEND = {"kind": "ollama", "base": "http://x", "model": "llama3"}
CHAMP = {"gene_id": "c1", "prompt": "scope: edit x. evidence required with timestamp. rollback on failure."}


def test_no_backend_returns_none():
    with mock.patch.object(il, "detect_local_backend", return_value=None):
        assert il.improve_champion(CHAMP, "Cyber") is None


def test_mechanical_regression_is_rejected():
    # candidate is empty-ish -> low mech score -> gate (b) blocks before judge even runs
    with mock.patch.object(il, "generate_candidates", return_value=[{"text": "do stuff", "source": "LOCAL:ollama:llama3"}]):
        with mock.patch.object(il, "llm_judge") as judge:
            out = il.improve_champion(CHAMP, "Cyber", backend=BACKEND)
    assert out is None
    judge.assert_not_called()  # never reached the judge — mechanical gate stopped it


def test_judge_rejects_keyword_stuffed_candidate():
    # candidate passes mechanical (has the keywords) but the JUDGE prefers champion (A) -> not promoted
    stuffed = "scope evidence timestamp rollback verify gate audit fake-green non-goal integration regression"
    with mock.patch.object(il, "generate_candidates", return_value=[{"text": stuffed, "source": "LOCAL:ollama:llama3"}]):
        with mock.patch.object(il, "llm_judge", return_value={"winner": "A", "raw": "A is clearer"}):
            out = il.improve_champion(CHAMP, "Cyber", backend=BACKEND)
    assert out is None  # Goodhart defense: mech liked it, judge rejected it -> blocked


def test_genuine_improvement_is_promoted():
    better = ("ROLE + SCOPE: edit only x.py (non-goals listed). METHOD: verify runtime truth via API. "
              "EVIDENCE: artifact path + timestamp + hash. ANTI-FAKE-GREEN: seeded-fault negative test. "
              "OUTPUT: STATUS json. ROLLBACK: revert on red gate. INTEGRATION: regression checks.")
    with mock.patch.object(il, "generate_candidates", return_value=[{"text": better, "source": "LOCAL:ollama:llama3"}]):
        with mock.patch.object(il, "llm_judge", return_value={"winner": "B", "raw": "B is more disciplined"}):
            out = il.improve_champion(CHAMP, "Cyber", backend=BACKEND)
    assert out is not None
    assert out["state"] == "GENERATED_AND_JUDGED" and out["judge"] == "LOCAL_LLM_JUDGE"
    assert out["beats_mech"] >= 0
