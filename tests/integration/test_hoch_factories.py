"""HOCH multi-factory tests: the Factory contract, the music scorer, and proof the domain-agnostic
BRAIN engine runs on the music (HMF) domain exactly as it does on software (HASF)."""
from pathlib import Path


def test_registry_has_both_factories_with_resolvable_scorers():
    from backend.factory.registry import get_factory, list_factories
    codes = {f.code for f in list_factories()}
    assert {"HASF", "HMF"} <= codes
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
