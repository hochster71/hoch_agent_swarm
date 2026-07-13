"""Independent per-factory validators (RMF-3).

The scheduler previously "verified" a task with:

    passed = (status == "COMPLETED" and exit_code == 0)

That is a DISPATCH check, not verification of the work. It proves a process ran,
not that it produced anything correct. A task could return empty output and still
be marked PASS.

These validators inspect the ARTIFACT the adapter actually produced and check it
against the mission's evidence contract. They are deliberately independent of the
adapter: they never see the model, only its output. A failing validator is a real
FAIL and must be reported as one.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


def _check(name: str, ok: bool, detail: str) -> Dict[str, Any]:
    return {"check": name, "passed": bool(ok), "detail": detail}


def _base_checks(artifact: str) -> List[Dict[str, Any]]:
    text = (artifact or "").strip()
    return [
        _check("artifact_non_empty", len(text) > 0, f"{len(text)} chars"),
        _check("artifact_substantive", len(text) >= 120,
               f"{len(text)} chars (>=120 required; a stub is not work)"),
        _check("not_refusal", not re.search(
            r"\b(i cannot|i can't|as an ai|unable to comply)\b", text, re.I),
            "no refusal/non-answer boilerplate"),
    ]


def validate_hasf(artifact: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Backend module inspection -> must actually engage the named module and
    surface at least one concrete, actionable observation."""
    t = (artifact or "").lower()
    module = str(ctx.get("subject", "")).lower()
    checks = _base_checks(artifact)
    checks.append(_check("references_subject_module", bool(module) and module.split("/")[-1].split(".")[0] in t,
                         f"must reference {ctx.get('subject')}"))
    checks.append(_check("has_concrete_finding", bool(re.search(
        r"(issue|defect|risk|bug|improve|refactor|missing|should|recommend)", t)),
        "at least one actionable finding"))
    return checks


def validate_hrf(artifact: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Research comparison -> must compare the named items AND cite sources."""
    t = (artifact or "").lower()
    checks = _base_checks(artifact)
    items = [str(i).lower() for i in ctx.get("compare", [])]
    checks.append(_check("covers_both_items", all(i in t for i in items),
                         f"must discuss all of {ctx.get('compare')}"))
    checks.append(_check("has_comparison_language", bool(re.search(
        r"(whereas|compared|differs|versus|vs\.?|however|unlike|while)", t)),
        "must actually compare, not merely list"))
    return checks


def validate_hcf(artifact: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Control-to-evidence gap analysis -> must map controls to evidence and name gaps."""
    t = (artifact or "").lower()
    checks = _base_checks(artifact)
    checks.append(_check("mentions_controls", bool(re.search(r"(control|policy|requirement)", t)),
                         "must reference controls"))
    checks.append(_check("mentions_evidence", bool(re.search(r"(evidence|artifact|proof|log)", t)),
                         "must reference evidence"))
    checks.append(_check("identifies_gap", bool(re.search(r"(gap|missing|absent|lack|not covered|no evidence)", t)),
                         "must identify at least one gap"))
    return checks


def validate_hsf(artifact: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Bounded creative artifact + deterministic package validation."""
    text = artifact or ""
    checks = _base_checks(artifact)
    # deterministic, checkable structural constraint stated in the mission
    min_lines = int(ctx.get("min_lines", 3))
    lines = [l for l in text.splitlines() if l.strip()]
    checks.append(_check("meets_min_lines", len(lines) >= min_lines,
                         f"{len(lines)} non-empty lines (>= {min_lines} required)"))
    theme = str(ctx.get("theme", "")).lower()
    checks.append(_check("on_theme", (not theme) or theme in text.lower(),
                         f"must be on theme: {ctx.get('theme')}"))
    return checks


VALIDATORS = {
    "HASF": validate_hasf,
    "HRF": validate_hrf,
    "HCF": validate_hcf,
    "HSF": validate_hsf,
    "HMF": validate_hsf,
}


def validate(factory: str, artifact: str, ctx: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Run the factory's independent validator over the produced artifact."""
    ctx = ctx or {}
    fn = VALIDATORS.get((factory or "").upper())
    if fn is None:
        return {"validator": "NONE", "verdict": "UNKNOWN",
                "reason": f"no validator registered for factory {factory!r}",
                "checks": []}
    checks = fn(artifact, ctx)
    passed = all(c["passed"] for c in checks)
    return {
        "validator": f"validate_{(factory or '').lower()}",
        "verdict": "PASS" if passed else "FAIL",
        "checks": checks,
        "failed_checks": [c["check"] for c in checks if not c["passed"]],
        "artifact_chars": len(artifact or ""),
    }
