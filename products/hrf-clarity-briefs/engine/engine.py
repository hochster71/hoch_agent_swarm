"""Orchestrator: BriefRequest -> validated, cited Brief (fail-closed).

Pipeline (the deterministic part that is REAL here):
  1. Assemble a candidate Brief from the request (topic, sources, drafted claims,
     uncertainty).
  2. Auto-seed the uncertainty section if the author left it empty (mandatory
     section can never be empty-by-omission): claims with only single-source
     support and any source with no verifiable text are surfaced as limits.
  3. Run the citation-coverage linter. If it fails, RAISE — the brief does not
     render. This is the moat.
  4. Return the Brief (coverage stamped). Rendering is done by `engine.assembler`.

Optional gate: pass `entitlement_token` to require a paid entitlement first
(no real payment; see `engine.entitlement`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .schemas import Brief, BriefRequest, DISCLAIMER
from .linter import lint_brief, LintResult
from .entitlement import require_entitlement, EntitlementStore


class BriefLintError(Exception):
    def __init__(self, result: LintResult):
        self.result = result
        super().__init__("brief failed the citation-coverage linter:\n"
                         + result.summary())


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _auto_uncertainty(brief: Brief) -> None:
    """Guarantee the mandatory uncertainty section is never empty-by-omission.

    Only fills when the author supplied nothing, and only with HONEST,
    machine-derivable limits — it never invents topical doubts."""
    if any(u.strip() for u in brief.uncertainty):
        return
    notes = []
    single = [c.text for c in brief.claims if len(c.citations) == 1]
    if single:
        notes.append(
            f"{len(single)} finding(s) rest on a single source; treat as "
            "provisional until corroborated."
        )
    thin_sources = [s.url or s.id for s in brief.sources if s.text.strip() == ""]
    if thin_sources:
        notes.append(
            "Some sources could not be quote-grounded from retrieved text; "
            "their exact support was not machine-verified."
        )
    notes.append(
        "This brief covers only what the provided sources state; it is not an "
        "exhaustive review, and newer evidence may exist."
    )
    brief.uncertainty = notes


def generate_brief(
    request: BriefRequest,
    entitlement_token: Optional[str] = None,
    entitlement_store: Optional[EntitlementStore] = None,
    consume_entitlement: bool = True,
) -> Brief:
    """Produce a linter-validated Brief or raise BriefLintError."""

    # Optional paid gate (no real payment; token comes from the checkout flow).
    if entitlement_token is not None:
        require_entitlement(
            entitlement_token, store=entitlement_store, consume=consume_entitlement
        )

    brief = Brief(
        topic=request.topic,
        claims=list(request.claims),
        uncertainty=list(request.uncertainty),
        sources=list(request.sources),
        disclaimer=DISCLAIMER,
        generated_at=_utcnow_iso(),
    )

    _auto_uncertainty(brief)

    result = lint_brief(brief)
    brief.coverage_pct = result.coverage_pct
    if not result.passed:
        raise BriefLintError(result)

    return brief
