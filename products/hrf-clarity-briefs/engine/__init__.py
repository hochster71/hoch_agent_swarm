"""HRF Clarity Briefs — engine package.

A research -> cited plain-English brief generator. Given a topic and a set of
INPUT SOURCES, it produces a structured brief where every factual claim carries
an inline citation to one of the provided sources, plus a mandatory
"What we're uncertain about" section.

The rigor discipline (a claim without a citation does not ship) is enforced by
the citation-coverage linter in `engine.linter` and is the product's moat.

Honesty boundary (NO FAKE GREEN):
  * The deterministic core — schema validation, the citation-coverage linter,
    verbatim quote-grounding, brief assembly, and the entitlement gate — is REAL
    and runnable with the Python standard library alone.
  * Two steps are documented INTEGRATION POINTS, not fabricated here:
      1. Live source gathering (WebSearch / web_fetch / research MCPs) — see
         `engine.retrieval`. The engine accepts provided sources today.
      2. LLM composition of draft claims from sources — the engine verifies
         drafted claims; it does not invent them. See `engine.retrieval` notes.
  * No source, URL, or quote is ever fabricated by this engine.
"""

from .schemas import Source, Citation, Claim, Brief, BriefRequest
from .linter import lint_brief, LintResult, LintViolation
from .assembler import assemble_markdown, assemble_html, assemble_json
from .engine import generate_brief, BriefLintError

__all__ = [
    "Source",
    "Citation",
    "Claim",
    "Brief",
    "BriefRequest",
    "lint_brief",
    "LintResult",
    "LintViolation",
    "assemble_markdown",
    "assemble_html",
    "assemble_json",
    "generate_brief",
    "BriefLintError",
]
