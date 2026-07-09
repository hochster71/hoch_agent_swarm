"""HRF research scorer — MECHANICAL PROXY for a research agenda's rigor + moonshot ambition.

Drop-in twin of scorer.py (same score_prompt signature) so the domain-agnostic BRAIN engine scores
the research gene pool unchanged.

HONESTY BOUNDARY: this scores whether a research *agenda/protocol* is well-formed (testable
hypothesis, evidence standard, method, kill criteria, ...). It does NOT establish that any finding
is TRUE — that requires executing the study and verifying every citation against real sources
(PubMed / bioRxiv / ClinicalTrials / ChEMBL). Output is labeled MECHANICAL_PROXY, rung=1. A high
score means 'rigorously specified', never 'result is real'. citation_verifiability is weighted high
because fabricated citations/results are research's deadly failure — HRF's anti-hallucination gate.
"""
from pathlib import Path
from typing import Dict, Any, Optional

_DEFAULT_WEIGHTS = {
    "testable_hypothesis": 0.15, "evidence_standard": 0.13, "citation_verifiability": 0.12,
    "method_rigor": 0.12, "literature_grounding": 0.12, "moonshot_ambition": 0.12,
    "reproducibility": 0.08, "falsifiability_kill_criteria": 0.06, "ethics_safety": 0.05,
    "impact_alignment": 0.05,
}

# Signal keywords per dimension (lowercased substring match). Threshold = hits for full marks.
_SIGNALS = {
    "testable_hypothesis": (["hypothesis", "we predict", "falsifiable", "null hypothesis", "if ", "then ", "testable"], 2),
    "evidence_standard": (["endpoint", "measure", "confirm", "refute", "success criteria", "metric", "effect size", "p-value", "confidence"], 2),
    "citation_verifiability": (["cite", "citation", "doi", "pubmed", "biorxiv", "verifiable", "primary source", "reference", "peer-review"], 2),
    "method_rigor": (["method", "control", "sample size", "randomiz", "protocol", "procedure", "design", "cohort", "assay"], 2),
    "literature_grounding": (["prior work", "literature", "baseline", "state of the art", "known", "replicat", "meta-analysis", "review"], 1),
    "moonshot_ambition": (["10x", "grand challenge", "moonshot", "abundance", "longevity", "fusion", "breakthrough", "transform", "orders of magnitude"], 1),
    "reproducibility": (["reproducib", "open data", "code available", "materials", "preregist", "share", "replicable"], 1),
    "falsifiability_kill_criteria": (["kill criteria", "stop condition", "fail if", "reject if", "abort", "go/no-go", "decision gate"], 1),
    "ethics_safety": (["ethic", "safety", "irb", "dual-use", "consent", "biosafety", "responsible"], 1),
    "impact_alignment": (["impact", "benefit", "who benefits", "outcome", "humanity", "patients", "society", "grand-challenge"], 1),
}


def _load_weights(rubric_path: Optional[str]) -> Dict[str, float]:
    if not rubric_path or not Path(rubric_path).exists():
        return dict(_DEFAULT_WEIGHTS)
    try:
        import yaml
        d = yaml.safe_load(Path(rubric_path).read_text())["dimensions"]
        return {k: float(v["weight"]) for k, v in d.items()}
    except Exception:
        return dict(_DEFAULT_WEIGHTS)


def score_prompt(text: str, rubric_path: Optional[str] = None) -> Dict[str, Any]:
    """MECHANICAL_PROXY score of a research agenda's rigor. Same shape as scorer.py."""
    t = (text or "").lower()
    weights = _load_weights(rubric_path)
    dims: Dict[str, float] = {}
    for dim, (kws, thresh) in _SIGNALS.items():
        hits = sum(1 for k in kws if k in t)
        dims[dim] = min(1.0, hits / thresh) if thresh else 0.0
    overall = round(100.0 * sum(dims[d] * weights.get(d, 0.0) for d in dims), 2)
    return {"overall": overall, "dimensions": dims,
            "method": "MECHANICAL_PROXY", "rung": 1,
            "note": "agenda rigor only; a finding is real only after execution + citation verification"}


def compare(candidate_text: str, incumbent_text: str, rubric_path: Optional[str] = None) -> Dict[str, Any]:
    c = score_prompt(candidate_text, rubric_path)["overall"]
    i = score_prompt(incumbent_text, rubric_path)["overall"]
    return {"candidate": c, "incumbent": i, "delta": round(c - i, 2), "candidate_wins": c > i}


# Wire in live-outcomes blended scoring (2026-07-07)
from backend.brain_convergence.scorer import blended_score

