"""Chat-with-the-BRAIN retrieval invariants — grounded, cited, never hallucinating offline."""


def test_retrieval_is_grounded_and_cited():
    from backend.orchestrator.brain_query import ask
    r = ask("senolytic longevity research")
    # offline (no model) must be retrieval_only and can never fabricate an answer
    assert r["mode"] in ("retrieval_only", "synthesized")
    assert r["grounded"] is True
    assert r["hits"], "a real question should retrieve real genes"
    # every returned source is a real gene_id that appears in the hits
    hit_ids = {h["gene_id"] for h in r["hits"]}
    assert set(r["sources"]) <= hit_ids
    # the top hit for a longevity query should be a research/longevity gene, not noise
    assert any("senolytic" in (h["title"] or "").lower() or h["code"] == "HRF" for h in r["hits"][:3])


def test_empty_question_returns_no_hits():
    from backend.orchestrator.brain_query import retrieve
    assert retrieve("") == []
    assert retrieve("the a of to") == []   # all stopwords -> nothing to match


def test_meta_question_routes_to_orchestrator_plan():
    # "what should HRF work on next" — the answer lives in the orchestrator plan, not gene text
    from backend.orchestrator import founder_orchestrator as FO
    from backend.orchestrator.brain_query import ask, _factory_in
    FO.decide()  # ensure a fresh brief exists
    assert _factory_in("what should HRF work on next") == "research"
    r = ask("what should HRF work on next")
    hrf = r["state"]["orchestrator"]["by_domain"].get("research")
    assert hrf and hrf["action"], "HRF's next action must be present in the answer context"
    # factory-scoped question surfaces that factory's own genes first
    assert r["hits"] and r["hits"][0]["code"] == "HRF"
