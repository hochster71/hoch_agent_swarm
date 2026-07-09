"""Regression tests for the BRAIN acceleration engine (gap analysis, gene expansion gate,
honest convergence, coverage-aware sweep). Pure/mechanical — no live model required; the
generate/judge paths are exercised with injected fakes so the GATES are tested, not the LLM."""
import os
import tempfile
import importlib


def test_gap_analysis_finds_thin_and_drift(tmp_path):
    import json
    from backend.brain_convergence import gap_analysis as G
    gp = tmp_path / "gp.json"; reg = tmp_path / "reg.json"; st = tmp_path / "st.json"
    gp.write_text(json.dumps({
        "class_sizes": {"Cyber": 40, "Privacy": 2, "Governance": 2, "Governance / Compliance": 30},
        "genes": {}}))
    reg.write_text(json.dumps({"generation": 3, "champions": {
        "Privacy": {"score": 45.0, "state": "X"}, "Cyber": {"score": 75.0, "state": "X"},
        "Governance": {"score": 40.0}}}))
    st.write_text(json.dumps({"mean_score": 55.0, "generation": 3, "state": "IMPROVING"}))
    r = G.analyze(str(gp), str(reg), str(st), min_pool=6, target=70.0)
    thin = {c["class"] for c in r["thin_classes"]}
    assert "Privacy" in thin and "Governance" in thin      # 2 < 6 => thin
    assert "Cyber" not in thin                              # 40 >= 6
    drift_pairs = {frozenset((d["a"], d["b"])) for d in r["taxonomy_drift"]}
    assert frozenset(("Governance / Compliance", "Governance")) in drift_pairs
    assert r["expansion_needed_genes"] == (6 - 2) + (6 - 2)  # Privacy + Governance deficits


def test_gene_expansion_dual_gate_rejects_dupes_and_keyword_stuffing():
    from backend.brain_convergence.gene_expansion import expand_class
    class_genes = [
        {"prompt": "Do the task."},
        {"prompt": "Scope files X. Require runtime verification evidence with timestamp. "
                   "Anti-fake-green: no PASS without proof. Rollback on failure. Structured report."},
    ]
    backend = {"kind": "fake", "model": "unit"}

    def gen(seed, cls, n=2, backend=None):
        return [
            {"text": "Do the task.", "source": "L"},                              # dup
            {"text": "scope evidence verification rollback gate report " * 3, "source": "L"},  # stuffed
            {"text": "tiny", "source": "L"},                                      # below median
            {"text": "Scope: module Y only. Require Docker/API runtime truth evidence at a "
                     "timestamped path. Gates: pytest+audit. Anti-fake-green. Rollback on "
                     "regression. Structured final report schema.", "source": "L"},           # genuine
        ]

    def judge(backend, a, b, cls):
        return {"winner": "A"} if b.startswith("scope evidence verification") else {"winner": "B"}

    out = expand_class("Privacy", class_genes, n_target=3, backend=backend,
                       generate_fn=gen, judge_fn=judge)
    assert len(out) == 1
    assert out[0]["prompt"].startswith("Scope: module Y")
    assert out[0]["state"] == "SYNTHETIC_ADMITTED"


def test_gene_expansion_no_backend_returns_empty(monkeypatch):
    from backend.brain_convergence import gene_expansion
    monkeypatch.setattr(gene_expansion, "detect_local_backend", lambda: None)
    assert gene_expansion.expand_class("Privacy", [{"prompt": "x"}], 3, backend=None) == []


def test_convergence_blind_flat_cannot_converge(tmp_path):
    from backend.brain_convergence import convergence as C
    sp = str(tmp_path / "s.json")
    s = None
    for g in range(1, 6):
        s = C.update(sp, g, 50.0, epsilon=0.5, patience=3, improver_online=False)
    assert s["converged"] is False and s["state"] == "STALLED_NO_IMPROVER"


def test_convergence_online_plateau_converges(tmp_path):
    from backend.brain_convergence import convergence as C
    sp = str(tmp_path / "s.json")
    # gen 1 is the baseline (gain=None); need `patience` real flat gains after it => 4 gens total.
    for g in range(1, 5):
        s = C.update(sp, g, 50.0, epsilon=0.5, patience=3, improver_online=True)
    assert s["converged"] is True and s["state"] == "CONVERGED"


def test_coverage_sweep_touches_all_and_prioritizes_weakest(tmp_path, monkeypatch):
    import backend.brain_convergence.improve_run as ir
    # redirect cursor into tmp so the test is hermetic
    champs = {f"C{i:02d}": {"score": float(i)} for i in range(20)}
    seen = set(); weak_hits = 0
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "prompt_brain").mkdir(parents=True, exist_ok=True)
    # patch the cursor path resolution by running from tmp cwd is not enough; call directly
    for _ in range(12):
        picked = ir._select_classes(champs, 6)
        keys = [k for k, _ in picked]
        seen.update(keys)
        if "C00" in keys:
            weak_hits += 1
    assert len(seen) >= 16          # broad rotation coverage over cycles
    assert weak_hits >= 10          # weakest near-always prioritized


def test_restricted_tournament_selection_niching():
    from backend.brain_convergence.gene_expansion import expand_class
    # 3 genes in the class
    class_genes = [
        {"gene_id": "g1", "prompt": "Identify code security vulnerabilities in docker containers", "task_class": "Cyber"},
        {"gene_id": "g2", "prompt": "Parse log files for authentication audit trail anomalies", "task_class": "Cyber"},
        {"gene_id": "g3", "prompt": "Setup telemetry pipelines using Tailscale status metrics", "task_class": "Cyber"},
    ]
    backend = {"kind": "fake", "model": "unit"}
    
    # Candidate 1: similar to g3, higher score
    # Candidate 2: similar to g1, lower score
    def gen(seed, cls, n=2, backend=None):
        return [
            {"text": "Setup telemetry pipelines using Tailscale metrics and relational database", "source": "L"},
            {"text": "Identify security issues in docker container systems", "source": "L"},
        ]
        
    def judge(backend, a, b, cls):
        return {"winner": "B"}
        
    def score_fake(text, rubric_path=None):
        if "relational database" in text:
            return {"overall": 80.0}
        elif "Identify security" in text:
            return {"overall": 40.0}
        elif "Identify code" in text:
            return {"overall": 50.0}
        elif "Parse log" in text:
            return {"overall": 60.0}
        elif "status metrics" in text:
            return {"overall": 70.0}
        return {"overall": 10.0}

    # Set max_pool = 3. Pool is already at 3, so full.
    admitted, replaced = expand_class(
        "Cyber", class_genes, n_target=2, backend=backend,
        generate_fn=gen, judge_fn=judge, score_fn=score_fake,
        max_pool=3, return_replaced=True
    )
    
    # Candidate 1 (Setup telemetry - score 80) is similar to g3 (score 70).
    # Since 80 > 70, Candidate 1 replaces g3.
    # Candidate 2 (Identify security - score 40) is similar to g1 (score 50).
    # Since 40 <= 50, Candidate 2 is discarded (not admitted).
    assert len(admitted) == 1
    assert admitted[0]["prompt"].startswith("Setup telemetry pipelines using Tailscale metrics")
    assert replaced == ["g3"]


def test_splits_guarantee_heldout():
    from backend.brain_convergence.splits import make_splits, assert_disjoint
    
    # Test for various n
    for n in range(1, 15):
        by_class = {"Cyber": [f"gene-{i}" for i in range(n)]}
        res = make_splits(by_class)
        assert_disjoint(res)
        
        counts = res["per_class"]["Cyber"]
        assert counts["train"] + counts["dev"] + counts["heldout"] == n
        assert counts["heldout"] >= 1


