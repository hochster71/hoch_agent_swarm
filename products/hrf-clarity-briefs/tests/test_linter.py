"""Tests for the citation-coverage linter — the product's moat.

The load-bearing test is `test_catches_uncited_claim`: it PROVES the linter
fails a brief that contains an uncited claim. Run:

    cd products/hrf-clarity-briefs
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

# Make the engine importable when running from tests/ directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.schemas import Source, Citation, Claim, Brief, BriefRequest, DISCLAIMER
from engine.linter import (
    lint_brief, COVERAGE, UNGROUNDED_QUOTE, UNRESOLVED_SOURCE, EMPTY_UNCERTAINTY,
)
from engine.engine import generate_brief, BriefLintError


SRC = Source(
    id="s1",
    title="Example Source",
    url="https://example.org/a",
    retrieved_at="2026-07-16T00:00:00Z",
    text="Drinking water supports normal body temperature regulation during exercise.",
)
SRC2 = Source(
    id="s2",
    title="Second Source",
    url="https://example.org/b",
    retrieved_at="2026-07-16T00:00:00Z",
    text="Electrolyte loss through sweat can affect performance in long events.",
)


def _good_brief():
    return Brief(
        topic="Hydration during exercise",
        claims=[
            Claim(
                text="Water helps regulate body temperature during exercise.",
                citations=[Citation("s1", "supports normal body temperature regulation during exercise")],
            ),
            Claim(
                text="Sweating causes electrolyte loss that can affect performance.",
                citations=[Citation("s2", "Electrolyte loss through sweat can affect performance")],
            ),
        ],
        uncertainty=["Individual fluid needs vary; this is not personal medical advice."],
        sources=[SRC, SRC2],
        disclaimer=DISCLAIMER,
    )


class TestCitationLinter(unittest.TestCase):

    def test_good_brief_passes(self):
        result = lint_brief(_good_brief())
        self.assertTrue(result.passed, result.summary())
        self.assertEqual(result.coverage_pct, 100.0)

    def test_catches_uncited_claim(self):
        """THE MOAT: an uncited claim must fail the brief."""
        brief = _good_brief()
        # Inject an uncited claim.
        brief.claims.append(
            Claim(text="Sports drinks are always better than water.", citations=[])
        )
        result = lint_brief(brief)

        self.assertFalse(result.passed)
        self.assertLess(result.coverage_pct, 100.0)
        coverage_violations = [v for v in result.violations if v.kind == COVERAGE]
        self.assertEqual(len(coverage_violations), 1)
        self.assertIn("Sports drinks", coverage_violations[0].claim_text)

    def test_catches_fabricated_quote(self):
        """A quote not present in the source is flagged (anti-fabrication)."""
        brief = _good_brief()
        brief.claims[0].citations = [
            Citation("s1", "caffeine doubles marathon speed for everyone")
        ]
        result = lint_brief(brief)
        self.assertFalse(result.passed)
        self.assertTrue(any(v.kind == UNGROUNDED_QUOTE for v in result.violations))

    def test_catches_unknown_source(self):
        brief = _good_brief()
        brief.claims[0].citations = [Citation("does-not-exist", "")]
        result = lint_brief(brief)
        self.assertFalse(result.passed)
        self.assertTrue(any(v.kind == UNRESOLVED_SOURCE for v in result.violations))

    def test_catches_empty_uncertainty(self):
        brief = _good_brief()
        brief.uncertainty = []
        result = lint_brief(brief)
        self.assertFalse(result.passed)
        self.assertTrue(any(v.kind == EMPTY_UNCERTAINTY for v in result.violations))

    def test_engine_raises_on_uncited_claim(self):
        """End-to-end: generate_brief fails closed on an uncited claim."""
        req = BriefRequest(
            topic="Hydration during exercise",
            sources=[SRC],
            claims=[Claim(text="An uncited assertion.", citations=[])],
            uncertainty=["placeholder"],
        )
        with self.assertRaises(BriefLintError):
            generate_brief(req)

    def test_engine_autofills_uncertainty(self):
        """Mandatory uncertainty is never empty-by-omission."""
        req = BriefRequest(
            topic="Hydration during exercise",
            sources=[SRC, SRC2],
            claims=_good_brief().claims,
            uncertainty=[],  # author left it blank
        )
        brief = generate_brief(req)
        self.assertTrue(any(u.strip() for u in brief.uncertainty))


if __name__ == "__main__":
    unittest.main(verbosity=2)
