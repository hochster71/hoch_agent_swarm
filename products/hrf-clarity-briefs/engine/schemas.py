"""Data model for a Clarity Brief.

Pure stdlib dataclasses so the engine and its tests run anywhere with no
third-party dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


# The mandatory disclaimer that must appear on every rendered brief.
DISCLAIMER = (
    "This is an information digest synthesized from cited public sources. "
    "It is NOT professional medical, legal, or financial advice. "
    "Verify with a qualified professional before acting."
)


@dataclass
class Source:
    """One retrievable source. `text` is the retrieved passage/content used to
    ground quotes. In production this is populated by live retrieval
    (`engine.retrieval`); here it may be supplied as provided input.
    """

    id: str
    title: str
    url: str
    retrieved_at: str  # ISO-8601 UTC timestamp of when the source was fetched
    text: str = ""     # retrieved content used for verbatim quote-grounding

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Citation:
    """Binds a claim to the specific source (and, ideally, verbatim quote) that
    supports it."""

    source_id: str
    quote: str = ""  # verbatim passage from the source that supports the claim

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    """One declarative finding. MUST carry >=1 citation or the linter fails
    the whole brief (the product's moat)."""

    text: str
    citations: List[Citation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "citations": [c.to_dict() for c in self.citations]}


@dataclass
class BriefRequest:
    """Input to the engine."""

    topic: str
    sources: List[Source] = field(default_factory=list)
    # Draft claims. In production these come from an LLM compose step; the
    # engine VERIFIES them (citation coverage + quote grounding). See README.
    claims: List[Claim] = field(default_factory=list)
    uncertainty: List[str] = field(default_factory=list)
    recency_days: Optional[int] = None
    depth: str = "brief"  # "brief" | "deep"


@dataclass
class Brief:
    """A fully assembled, linter-validated brief."""

    topic: str
    claims: List[Claim]
    uncertainty: List[str]
    sources: List[Source]
    coverage_pct: float = 0.0
    disclaimer: str = DISCLAIMER
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "claims": [c.to_dict() for c in self.claims],
            "uncertainty": list(self.uncertainty),
            "sources": [s.to_dict() for s in self.sources],
            "coverage_pct": self.coverage_pct,
            "disclaimer": self.disclaimer,
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# Convenience constructors from plain dicts (e.g. parsed JSON request files).
# ---------------------------------------------------------------------------

def source_from_dict(d: Dict[str, Any]) -> Source:
    return Source(
        id=str(d["id"]),
        title=str(d.get("title", "")),
        url=str(d.get("url", "")),
        retrieved_at=str(d.get("retrieved_at", "")),
        text=str(d.get("text", "")),
    )


def claim_from_dict(d: Dict[str, Any]) -> Claim:
    cites = [
        Citation(source_id=str(c["source_id"]), quote=str(c.get("quote", "")))
        for c in d.get("citations", [])
    ]
    return Claim(text=str(d["text"]), citations=cites)


def request_from_dict(d: Dict[str, Any]) -> BriefRequest:
    return BriefRequest(
        topic=str(d["topic"]),
        sources=[source_from_dict(s) for s in d.get("sources", [])],
        claims=[claim_from_dict(c) for c in d.get("claims", [])],
        uncertainty=[str(u) for u in d.get("uncertainty", [])],
        recency_days=d.get("recency_days"),
        depth=str(d.get("depth", "brief")),
    )
