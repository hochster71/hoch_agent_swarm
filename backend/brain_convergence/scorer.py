"""M0 BRAIN Convergence — Scorer (mechanical proxy).

Deterministic, no-LLM proxy scorer aligned to config/prompt_score_rubric.yaml (10 weighted
dimensions). At M0 each dimension is scored by detecting rubric-relevant signals in the prompt
text — a transparent heuristic, explicitly labeled MECHANICAL_PROXY, NOT a model judgment.
At Rung 2 this is replaced/augmented by live LLM judges on the held-out split.

Honesty: this proxy measures whether a prompt *contains the disciplines the rubric asks for*
(scope, evidence, anti-fake-green, rollback, ...). It does not judge semantic quality — that is
what the Rung-2 judges add. Kept deterministic so the loop is reproducible and auditable.
"""
import re
from pathlib import Path
from typing import Dict, Any, Optional

_DEFAULT_WEIGHTS = {
    "scope_clarity": 0.15, "non_goals_defined": 0.10, "runtime_truth_required": 0.15,
    "gate_requirements_defined": 0.10, "evidence_required": 0.15,
    "final_report_schema_defined": 0.05, "anti_fake_claim_controls": 0.10,
    "human_loop_reduction": 0.10, "rollback_or_stop_condition": 0.05, "integration_safety": 0.05,
}

# Signal keywords per rubric dimension (lowercased substring match). Threshold = hits for full marks.
_SIGNALS = {
    "scope_clarity": (["scope", "files", "method", "inputs", "steps", "deliverable", "task:"], 2),
    "non_goals_defined": (["non-goal", "do not", "don't", "not to touch", "out of scope", "must not", "never"], 1),
    "runtime_truth_required": (["verify", "runtime", "docker", "api", "ui", "telemetry", "healthcheck", "curl", "test output", "live"], 2),
    "gate_requirements_defined": (["gate", "pytest", "npm", "lint", "validate", "check script", "verification", "ci"], 1),
    "evidence_required": (["evidence", "artifact", "path", "timestamp", "hash", "log", "ledger"], 2),
    "final_report_schema_defined": (["output:", "report", "schema", "status=", "format", "return", "json"], 1),
    "anti_fake_claim_controls": (["fake-green", "fake green", "no fake", "unverified", "claimed", "seeded", "adversarial", "verified only"], 1),
    "human_loop_reduction": (["fallback", "auto", "without approval", "escalate only", "default", "self-"], 1),
    "rollback_or_stop_condition": (["rollback", "stop condition", "abort", "revert", "stop ", "blocked", "halt"], 1),
    "integration_safety": (["regression", "integrity", "existing", "don't break", "backward", "compat", "non-destructive"], 1),
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
    t = (text or "").lower()
    weights = _load_weights(rubric_path)
    dims: Dict[str, float] = {}
    for dim, (kws, thresh) in _SIGNALS.items():
        hits = sum(1 for k in kws if k in t)
        dims[dim] = min(1.0, hits / thresh) if thresh else 0.0
    overall = round(100.0 * sum(dims[d] * weights.get(d, 0.0) for d in dims), 2)
    return {"overall": overall, "dimensions": dims, "method": "MECHANICAL_PROXY", "rung": 1}


def compare(candidate_text: str, incumbent_text: str, rubric_path: Optional[str] = None) -> Dict[str, Any]:
    """Head-to-head. Deterministic. Positive delta = candidate scored higher."""
    c = score_prompt(candidate_text, rubric_path)["overall"]
    i = score_prompt(incumbent_text, rubric_path)["overall"]
    return {"candidate": c, "incumbent": i, "delta": round(c - i, 2), "candidate_wins": c > i}
