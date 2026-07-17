"""Citation-coverage LINTER — the product's moat.

The rule: a factual claim without a citation does not ship. This module fails
the brief (fail-closed) if ANY of the following is true:

  * A findings claim has zero citations                (COVERAGE)
  * A citation references a source id that doesn't exist (UNRESOLVED_SOURCE)
  * A citation's quote is not found verbatim in that source's retrieved text
    (UNGROUNDED_QUOTE)  -- deterministic anti-fabrication check
  * The mandatory "What we're uncertain about" section is empty (EMPTY_UNCERTAINTY)
  * The mandatory disclaimer is missing (MISSING_DISCLAIMER)

`coverage_pct` is (claims with >=1 citation) / (total claims) * 100. The hard
invariant for a shippable brief is `coverage_pct == 100.0` AND no violations of
any other kind. Anything less -> the brief must NOT render; it fails with the
offending claims listed.

Note on scope (honest): verbatim quote-grounding proves a quote was really
present in the source. It does NOT prove the quote semantically SUPPORTS the
claim — that deeper fact-check is the LLM "council" pass documented as an
integration point in the README. This linter is the deterministic floor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .schemas import Brief, Claim, Source


# Violation kinds
COVERAGE = "COVERAGE"
UNRESOLVED_SOURCE = "UNRESOLVED_SOURCE"
UNGROUNDED_QUOTE = "UNGROUNDED_QUOTE"
EMPTY_UNCERTAINTY = "EMPTY_UNCERTAINTY"
MISSING_DISCLAIMER = "MISSING_DISCLAIMER"
EMPTY_CLAIM = "EMPTY_CLAIM"


@dataclass
class LintViolation:
    kind: str
    message: str
    claim_index: Optional[int] = None
    claim_text: str = ""

    def __str__(self) -> str:
        loc = f" [claim #{self.claim_index}]" if self.claim_index is not None else ""
        return f"{self.kind}{loc}: {self.message}"


@dataclass
class LintResult:
    passed: bool
    coverage_pct: float
    violations: List[LintViolation] = field(default_factory=list)
    total_claims: int = 0
    cited_claims: int = 0

    def summary(self) -> str:
        head = "PASS" if self.passed else "FAIL"
        lines = [
            f"[{head}] citation coverage = {self.coverage_pct:.1f}% "
            f"({self.cited_claims}/{self.total_claims} claims cited); "
            f"{len(self.violations)} violation(s)."
        ]
        for v in self.violations:
            lines.append(f"  - {v}")
        return "\n".join(lines)


def _normalize(text: str) -> str:
    """Collapse whitespace and lowercase for tolerant substring matching, so
    quote-grounding survives reflow/indentation differences but still requires
    the actual words to be present in the source."""
    return re.sub(r"\s+", " ", text or "").strip().lower()


def quote_is_grounded(quote: str, source: Source) -> bool:
    """True iff `quote` appears (whitespace-normalized) within source.text.

    If the source has no retrieved text at all we cannot verify grounding, so we
    fail closed (return False) UNLESS the quote itself is empty. An empty quote
    is allowed only as a citation-by-reference (source id resolves) and is NOT
    subject to grounding — but it also earns no anti-fabrication guarantee.
    """
    if quote.strip() == "":
        return True  # citation-by-reference only; nothing to ground
    if source.text.strip() == "":
        return False  # cannot verify -> fail closed
    return _normalize(quote) in _normalize(source.text)


def lint_brief(brief: Brief) -> LintResult:
    """Run the full linter over an assembled/candidate brief."""
    violations: List[LintViolation] = []
    source_ids = {s.id: s for s in brief.sources}

    total = len(brief.claims)
    cited = 0

    for i, claim in enumerate(brief.claims):
        if claim.text.strip() == "":
            violations.append(
                LintViolation(EMPTY_CLAIM, "empty claim text", i, claim.text)
            )
            continue

        # --- The moat: coverage ---
        if len(claim.citations) == 0:
            violations.append(
                LintViolation(
                    COVERAGE,
                    "claim has no citation (uncited claims may not ship)",
                    i,
                    claim.text,
                )
            )
        else:
            cited += 1

        # --- Each citation must resolve, and its quote must be grounded ---
        for c in claim.citations:
            src = source_ids.get(c.source_id)
            if src is None:
                violations.append(
                    LintViolation(
                        UNRESOLVED_SOURCE,
                        f"citation references unknown source_id '{c.source_id}'",
                        i,
                        claim.text,
                    )
                )
                continue
            if not quote_is_grounded(c.quote, src):
                violations.append(
                    LintViolation(
                        UNGROUNDED_QUOTE,
                        (
                            f"quote not found verbatim in source '{c.source_id}' "
                            f"({src.url or 'no url'}) — possible fabrication"
                        ),
                        i,
                        claim.text,
                    )
                )

    coverage_pct = (cited / total * 100.0) if total > 0 else 0.0

    # --- Mandatory uncertainty section ---
    if len([u for u in brief.uncertainty if u.strip()]) == 0:
        violations.append(
            LintViolation(
                EMPTY_UNCERTAINTY,
                "the mandatory 'What we're uncertain about' section is empty",
            )
        )

    # --- Mandatory disclaimer ---
    if brief.disclaimer.strip() == "":
        violations.append(
            LintViolation(MISSING_DISCLAIMER, "mandatory disclaimer is missing")
        )

    # A brief with zero claims is not a shippable brief.
    if total == 0:
        violations.append(
            LintViolation(COVERAGE, "brief has no claims")
        )

    passed = (
        coverage_pct == 100.0
        and total > 0
        and not any(
            v.kind
            in (
                COVERAGE,
                UNRESOLVED_SOURCE,
                UNGROUNDED_QUOTE,
                EMPTY_UNCERTAINTY,
                MISSING_DISCLAIMER,
                EMPTY_CLAIM,
            )
            for v in violations
        )
    )

    return LintResult(
        passed=passed,
        coverage_pct=coverage_pct,
        violations=violations,
        total_claims=total,
        cited_claims=cited,
    )
