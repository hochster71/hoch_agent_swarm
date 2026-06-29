from backend.promptops.prompt_rewriter import PromptRewriter

def test_prompt_rewriter():
    rewriter = PromptRewriter()
    
    res = rewriter.rewrite("Build HAS e2e production ready no errors", "DOCKER_RUNTIME")
    assert res["mission_id"].startswith("MSN-")
    assert "Objective" in res["rewritten_text"]
    assert "Non-Goals" in res["rewritten_text"]
