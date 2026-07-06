"""HOCH multi-factory tests: the Factory contract, the music scorer, and proof the domain-agnostic
BRAIN engine runs on the music (HMF) domain exactly as it does on software (HASF)."""
from pathlib import Path


def test_registry_has_both_factories_with_resolvable_scorers():
    from backend.factory.registry import get_factory, list_factories
    codes = {f.code for f in list_factories()}
    assert {"HASF", "HMF", "HRF"} <= codes
    sw, mu = get_factory("software"), get_factory("music")
    # software keeps the historical FLAT layout; music is subfoldered (backward compat)
    assert sw.gene_pool.parent.name == "prompt_brain"
    assert mu.gene_pool.parent.name == "music"
    # both scorers import and are callable
    assert callable(sw.scorer()) and callable(mu.scorer())
    # publishing is always operator-gated
    assert sw.publish_tier == "T3" and mu.publish_tier == "T3"
    assert "originality_check" in mu.gates  # HMF-specific governance


def test_music_scorer_rewards_spec_and_labels_proxy():
    from backend.brain_convergence.music_scorer import score_prompt
    rubric = "config/music_score_rubric.yaml"
    good = ("Genre: deep house. Structure: intro/verse/chorus/bridge/outro. Hook: plucked synth "
            "motif. Originality: original, no clone, cleared samples. Instrumentation: sub bass, "
            "pads, synth, congas. Tempo/key: 122 BPM, A minor, 4/4. Mix/master: -8 LUFS stereo "
            "compression reference. Arc: build tension release. Metadata: title mood duration. "
            "QC: A/B reference check before render.")
    lazy = "make a banger"
    r = score_prompt(good, rubric)
    assert r["method"] == "MECHANICAL_PROXY" and r["rung"] == 1
    assert r["overall"] > score_prompt(lazy, rubric)["overall"]
    assert score_prompt(lazy, rubric)["overall"] == 0.0


def test_hrf_registered_with_citation_gate():
    from backend.factory.registry import get_factory
    hrf = get_factory("research")
    assert hrf is not None and hrf.code == "HRF"
    assert hrf.gene_pool.parent.name == "research"
    assert callable(hrf.scorer())
    # the anti-hallucination gate must be declared
    assert "citation_verification" in hrf.gates
    assert hrf.publish_tier == "T3"


def test_research_scorer_rewards_rigor_and_labels_proxy():
    from backend.brain_convergence.research_scorer import score_prompt
    rubric = "config/research_score_rubric.yaml"
    rigorous = ("Moonshot longevity grand challenge. Testable hypothesis: senolytic reduces frailty "
                "vs placebo. Evidence standard: preregistered endpoint, effect size, confidence, "
                "confirm/refute thresholds. Method: randomized controls, sample size, reproducible "
                "open data. Literature: cite PubMed DOIs, verifiable primary sources only. Kill "
                "criteria: reject if no dose-response. Ethics: IRB consent dual-use. Impact: "
                "healthspan for patients.")
    vague = "look into aging"
    r = score_prompt(rigorous, rubric)
    assert r["method"] == "MECHANICAL_PROXY"
    assert r["overall"] > score_prompt(vague, rubric)["overall"]
    assert score_prompt(vague, rubric)["overall"] == 0.0


def test_citation_verifier_malformed_is_not_found_offline():
    # malformed IDs are rejected WITHOUT any network call (fail-closed on garbage)
    from backend.brain_convergence import citation_verifier as CV
    assert CV.verify_citation("not-a-real-id")["status"] == "NOT_FOUND"
    assert CV.verify_citation("10.bad")["status"] == "NOT_FOUND"
    assert CV.verify_arxiv("not-an-arxiv-id")["status"] == "NOT_FOUND"


def test_citation_verifier_routes_by_id_type(monkeypatch):
    # a dotted arXiv id routes to the arXiv resolver; a bare number to PMID; a 10.x to DOI
    from backend.brain_convergence import citation_verifier as CV
    monkeypatch.setattr(CV, "verify_arxiv", lambda x: {"status": "VERIFIED", "id": x})
    monkeypatch.setattr(CV, "verify_pmid", lambda x: {"status": "VERIFIED", "id": x})
    monkeypatch.setattr(CV, "verify_doi", lambda x: {"status": "VERIFIED", "id": x})
    assert CV.verify_citation("2312.00752")["kind"] == "arxiv"
    assert CV.verify_citation("31542391")["kind"] == "pmid"
    assert CV.verify_citation("10.1016/j.ebiom.2019.08.069")["kind"] == "doi"


def test_citation_gate_fail_closed(monkeypatch):
    # gate PASSES only if EVERY citation VERIFIED; one NOT_FOUND blocks the batch
    from backend.brain_convergence import citation_verifier as CV

    def fake_verify(c):
        return {"status": "VERIFIED" if c.startswith("10.1016") else "NOT_FOUND", "id": c}
    monkeypatch.setattr(CV, "verify_citation", fake_verify)
    assert CV.gate(["10.1016/real", "10.1016/also-real"])["decision"] == "PASS"
    assert CV.gate(["10.1016/real", "10.9999/hallucinated"])["decision"] == "BLOCK"
    assert CV.gate([])["decision"] == "BLOCK"          # no citations => cannot pass


def test_gene_expansion_accepts_domain_scorer():
    # the gate can be driven by a Factory's OWN scorer (research), not just the software one
    from backend.brain_convergence.gene_expansion import expand_class
    from backend.brain_convergence.research_scorer import score_prompt as research_score
    genes = [{"prompt": "Hypothesis: X. Evidence standard: endpoint. Method: controls. Cite DOIs."},
             {"prompt": "study stuff"}]

    def gen(seed, cls, n=2, backend=None):
        return [{"text": "Testable hypothesis: Y reduces Z vs control. Evidence standard: "
                         "preregistered endpoint, effect size, confidence. Method: randomized "
                         "controls, reproducible open data. Cite PubMed DOIs, verifiable. Kill "
                         "criteria: reject if null. Ethics IRB. Impact: patients.", "source": "L"}]

    out = expand_class("Longevity", genes, n_target=1, backend={"kind": "fake"},
                       generate_fn=gen, judge_fn=lambda b, a, x, c: {"winner": "B"},
                       score_fn=research_score)
    assert len(out) == 1 and out[0]["state"] == "SYNTHETIC_ADMITTED"


def test_engine_runs_on_music_domain(tmp_path):
    # the SAME gap_analysis used for software must work on music paths unchanged
    import json
    from backend.brain_convergence import gap_analysis as G
    gp = tmp_path / "gp.json"
    gp.write_text(json.dumps({
        "domain": "music",
        "class_sizes": {"House": 1, "Ambient": 2, "Trap": 1},
        "genes": {}}))
    r = G.analyze(str(gp), str(tmp_path / "none_reg.json"), str(tmp_path / "none_st.json"),
                  min_pool=3, target=70.0)
    thin = {c["class"] for c in r["thin_classes"]}
    assert {"House", "Ambient", "Trap"} <= thin           # all below min_pool=3
    assert r["expansion_needed_genes"] == (3 - 1) + (3 - 2) + (3 - 1)
