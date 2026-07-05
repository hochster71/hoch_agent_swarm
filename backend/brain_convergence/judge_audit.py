"""M0 BRAIN Convergence — Judge audit (seeded fault).

The anti-Goodhart guard for the *scorer itself*. A scoring function that never fails is
indistinguishable from one that is broken, so before trusting any promotion we prove the scorer
can still tell a deliberately-bad prompt from a strong one:

  - a KNOWN-BAD prompt (vague, no scope/evidence/guardrails) MUST score below `floor`
  - a KNOWN-GOOD prompt (full rubric discipline) MUST score above `ceiling`

If either fails, the audit returns passed=False and the loop must freeze promotions until the
scorer/rubric is fixed. This is the seeded-fault clause from HAS_EVIDENCE_DISCIPLINE_BASELINE.md
pointed at the evaluation harness.
"""
from typing import Dict, Any, Optional

from backend.brain_convergence.scorer import score_prompt

KNOWN_BAD = "do the thing. make it good. figure it out."

KNOWN_GOOD = (
    "ROLE: build the X module. SCOPE: edit only backend/x.py and tests/test_x.py (non-goals: do "
    "not touch the daemon or config). METHOD: 1) implement 2) run pytest gate 3) verify runtime "
    "truth via the API healthcheck. EVIDENCE: write an artifact to docs/evidence/x_<timestamp>.md "
    "with file paths, test names, and hashes. ANTI-FAKE-GREEN: no unverified PASS; a seeded-fault "
    "negative test must fail the build; only VERIFIED renders green. OUTPUT: STATUS=<VERIFIED|BLOCKED> "
    "in JSON schema. ROLLBACK: stop and revert on any red gate. INTEGRATION: run existing regression "
    "checks; changes must be non-destructive and backward compatible."
)


def audit_scorer(floor: float = 30.0, ceiling: float = 60.0, rubric_path: Optional[str] = None) -> Dict[str, Any]:
    bad = score_prompt(KNOWN_BAD, rubric_path)["overall"]
    good = score_prompt(KNOWN_GOOD, rubric_path)["overall"]
    bad_ok = bad < floor
    good_ok = good > ceiling
    passed = bad_ok and good_ok
    reasons = []
    if not bad_ok:
        reasons.append(f"KNOWN-BAD scored {bad} >= floor {floor} — scorer cannot detect a bad prompt (BROKEN)")
    if not good_ok:
        reasons.append(f"KNOWN-GOOD scored {good} <= ceiling {ceiling} — scorer cannot recognize a good prompt (BROKEN)")
    return {
        "passed": passed,
        "known_bad_score": bad,
        "known_good_score": good,
        "floor": floor,
        "ceiling": ceiling,
        "separation": round(good - bad, 2),
        "verdict": "SCORER_AUDIT_PASS" if passed else "SCORER_AUDIT_FAIL — FREEZE PROMOTIONS",
        "reasons": reasons,
    }
