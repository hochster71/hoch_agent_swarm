from unittest import mock
from backend.brain_convergence import local_model_bridge as lmb


def test_no_backend_returns_empty_and_never_crashes():
    with mock.patch.object(lmb, "detect_local_backend", return_value=None):
        out = lmb.generate_candidates("base prompt", "Cyber", n=3)
    assert out == []  # honest: mechanical-only, no fabrication


def test_status_reports_unavailable_gracefully():
    with mock.patch.object(lmb, "detect_local_backend", return_value=None):
        s = lmb.status()
    assert s["live_brain_available"] is False and "mechanical-only" in s["note"]


def test_generate_labels_source_when_backend_up():
    backend = {"kind": "ollama", "base": "http://localhost:11434", "model": "llama3"}
    with mock.patch.object(lmb, "_ollama_generate", return_value="IMPROVED PROMPT with evidence + rollback"):
        out = lmb.generate_candidates("base", "Cyber", n=2, backend=backend)
    assert len(out) == 2
    assert all(c["source"] == "LOCAL:ollama:llama3" for c in out)
    assert all(c["text"] for c in out)


def test_generate_survives_model_error():
    backend = {"kind": "ollama", "base": "http://localhost:11434", "model": "llama3"}
    with mock.patch.object(lmb, "_ollama_generate", side_effect=RuntimeError("model busy")):
        out = lmb.generate_candidates("base", "Cyber", n=2, backend=backend)
    assert out == []  # errors filtered, no crash, no fabrication
