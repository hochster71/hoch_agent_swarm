"""M0 BRAIN Convergence — Scorer (mechanical proxy).

Deterministic, no-LLM proxy scorer aligned to config/prompt_score_rubric.yaml (10 weighted
dimensions). At M0 each dimension is scored by detecting rubric-relevant signals in the prompt
text — a transparent heuristic, explicitly labeled MECHANICAL_PROXY, NOT a model judgment.
At Rung 2 this is replaced/augmented by live LLM judges on the held-out split.

Honesty: this proxy measures whether a prompt *contains the disciplines the rubric asks for*
(scope, evidence, anti-fake-green, rollback, ...). It does not judge semantic quality — that is
what the Rung-2 judges add. Kept deterministic so the loop is reproducible and auditable.
"""
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


def blended_score(gene_id: str, rubric_score: float,
                  ledger_path: Optional[str] = None) -> Dict[str, Any]:
    """Blend mechanical rubric score with real execution outcomes from the ledger.

    Doctrine (2026-07-06): the rubric is a keyword-presence proxy (method=MECHANICAL_PROXY).
    It is fast and $0 but measures vocabulary fit, not capability. Real gate outcomes — logged
    by record_outcome() after live executions — are ground truth and override the proxy when
    sufficient evidence exists.

    Blend formula (evidence-gated):
      - 0 outcomes  : score = rubric_score (proxy only; label MECHANICAL_PROXY)
      - 1-4 outcomes: score = 0.7*rubric + 0.3*outcome_rate*100 (label BLENDED_SPARSE)
      - 5+ outcomes : score = 0.4*rubric + 0.6*outcome_rate*100 (label BLENDED_CONFIDENT)

    Completion rate = completed / executions from the outcome ledger for this gene_id.
    Source: Sculley et al. (2015) "Hidden Technical Debt in Machine Learning Systems"
    (NeurIPS) — Goodhart's Law section; proxy metrics diverge from real objectives under
    optimisation pressure. Blend weight schedule follows Lakshminarayanan et al. (2017)
    uncertainty-weighted ensemble logic: proxy dominates until real-world evidence accumulates.
    """
    import json as _json
    from pathlib import Path as _P

    _ledger = _P(ledger_path) if ledger_path else (
        _P(__file__).resolve().parent.parent.parent /
        "data" / "prompt_brain" / "outcome_feedback_ledger.jsonl")

    executions = completions = 0
    if _ledger.exists():
        # Scan outcome ledger for this gene's real results.
        # Only COMPLETED/FAILED status entries with a matching champion_id count.
        usage_ids: set = set()
        try:
            ul = _ledger.parent / "runtime_usage_ledger.jsonl"
            if ul.exists():
                for ln in ul.read_text(encoding="utf-8").splitlines():
                    try:
                        e = _json.loads(ln)
                        if (e.get("champion_id") == gene_id
                                and not e.get("fallback_used")):
                            usage_ids.add(e.get("usage_id"))
                    except Exception:
                        pass
        except Exception:
            pass

        for ln in _ledger.read_text(encoding="utf-8").splitlines():
            try:
                e = _json.loads(ln)
                if e.get("usage_id") in usage_ids and e.get("status") in ("COMPLETED","FAILED"):
                    executions += 1
                    if e.get("status") == "COMPLETED":
                        completions += 1
            except Exception:
                pass

    if executions == 0:
        return {"score": rubric_score, "method": "MECHANICAL_PROXY",
                "executions": 0, "completions": 0, "outcome_rate": None,
                "rubric_score": rubric_score}

    outcome_rate = completions / executions
    outcome_score = round(outcome_rate * 100, 2)

    if executions < 5:
        blended = round(0.7 * rubric_score + 0.3 * outcome_score, 2)
        method = "BLENDED_SPARSE"
    else:
        blended = round(0.4 * rubric_score + 0.6 * outcome_score, 2)
        method = "BLENDED_CONFIDENT"

    return {"score": blended, "method": method,
            "executions": executions, "completions": completions,
            "outcome_rate": round(outcome_rate, 4),
            "rubric_score": rubric_score, "outcome_score": outcome_score}
