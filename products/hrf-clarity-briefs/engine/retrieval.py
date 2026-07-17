"""Source gathering — the honest boundary.

WHAT IS REAL HERE
-----------------
`ProvidedSourceProvider` returns the sources the caller supplies (as text/URLs).
This is the mode the engine runs in today: you bring the sources, the engine
enforces the rigor. Everything downstream (linter, quote-grounding, assembly) is
real and runnable on these.

WHAT IS A DOCUMENTED INTEGRATION POINT (NOT FABRICATED)
-------------------------------------------------------
`LiveWebSourceProvider.gather()` is where live retrieval wires in. This repo and
runtime already expose real retrieval capability:
  * the `WebSearch` / `web_fetch` tools, and
  * connected research MCPs (PubMed, bioRxiv, Consensus, ClinicalTrials.gov).
Auto-gathering means: run those tools, capture each result's URL + title +
retrieved-at timestamp + fetched text, and hand back `Source` objects. Until
that wiring is added, this provider RAISES rather than returning anything — it
will never invent a source, URL, or quote. (NO FAKE GREEN.)

Similarly, turning raw sources into DRAFT CLAIMS is an LLM "compose" step. The
engine's job is to VERIFY drafted claims (coverage + quote grounding), not to
hallucinate them. See README "REAL vs STUB".
"""

from __future__ import annotations

from typing import List, Optional

from .schemas import Source


class SourceProvider:
    def gather(self, topic: str, recency_days: Optional[int] = None,
               domains: Optional[List[str]] = None) -> List[Source]:
        raise NotImplementedError


class ProvidedSourceProvider(SourceProvider):
    """Return caller-supplied sources unchanged. This is the REAL default path."""

    def __init__(self, sources: List[Source]):
        self._sources = list(sources)

    def gather(self, topic: str, recency_days: Optional[int] = None,
               domains: Optional[List[str]] = None) -> List[Source]:
        return list(self._sources)


class LiveWebSourceProvider(SourceProvider):
    """Integration point for live retrieval. Deliberately fails closed until an
    operator wires the real WebSearch / web_fetch / research-MCP calls in.

    To implement (operator task): replace the body of `gather` with real tool
    calls that produce Source(id, title, url, retrieved_at=<UTC now>, text=<fetched>).
    """

    WIRED = False  # flip to True only once the real calls below are implemented

    def gather(self, topic: str, recency_days: Optional[int] = None,
               domains: Optional[List[str]] = None) -> List[Source]:
        if not self.WIRED:
            raise NotImplementedError(
                "Live source gathering is not wired in this build. Provide sources "
                "explicitly (ProvidedSourceProvider) or implement the WebSearch / "
                "web_fetch / research-MCP calls here. This provider will not "
                "fabricate sources."
            )
        # --- Operator implements real retrieval here, e.g.: ---------------
        #   results = websearch(topic, recency_days=recency_days)
        #   sources = []
        #   for r in results:
        #       page = web_fetch(r.url)
        #       sources.append(Source(id=..., title=r.title, url=r.url,
        #                             retrieved_at=utcnow_iso(), text=page.text))
        #   return sources
        raise NotImplementedError  # pragma: no cover
