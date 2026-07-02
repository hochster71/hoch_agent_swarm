import pytest
from backend.michael_ai.prompt_builder import build_next_prompt
from backend.michael_ai.training_corpus import export_training_corpus

def test_next_prompt_generation_preserves_release_constraints():
    res = build_next_prompt()
    assert res["status"] == "success"
    assert "NO_ACTIVE_RELEASE_GO" in res["prompt"]
    assert "Stop all" in res["prompt"]
    assert "Final Verifier" in res["prompt"]

def test_training_corpus_exports_examples():
    res = export_training_corpus()
    assert res["status"] == "success"
    assert res["count"] > 0
    assert len(res["corpus"]) > 0
    
    first_example = res["corpus"][0]
    assert "request" in first_example
    assert "desired_output_pattern" in first_example
    assert "avoid_output_pattern" in first_example
    assert "operating_doctrine" in first_example
