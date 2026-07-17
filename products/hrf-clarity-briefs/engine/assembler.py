"""Brief assembler: a validated Brief -> Markdown / HTML / JSON.

Inline citations render as [n] where n is the source's number in the numbered
reference list. The mandatory disclaimer banner and the "What we're uncertain
about" section are always emitted.

PDF: HTML output is print-ready (a plain, self-contained document). Converting
to PDF is an optional handoff to the repo's `anthropic-skills:pdf` skill or any
html->pdf tool (weasyprint / wkhtmltopdf / headless Chrome). That conversion is
a documented integration point, not bundled here, so the engine keeps a zero
third-party-dependency core.
"""

from __future__ import annotations

import html
import json
from typing import Dict, List

from .schemas import Brief, Source


def _source_number_map(brief: Brief) -> Dict[str, int]:
    """Assign 1-based reference numbers in the order sources are listed."""
    return {s.id: i + 1 for i, s in enumerate(brief.sources)}


def _inline_marks(citation_source_ids: List[str], numbers: Dict[str, int]) -> str:
    nums = sorted({numbers[sid] for sid in citation_source_ids if sid in numbers})
    return "".join(f"[{n}]" for n in nums)


def assemble_json(brief: Brief) -> str:
    """The `brief.json` sidecar."""
    return json.dumps(brief.to_dict(), indent=2, ensure_ascii=False)


def assemble_markdown(brief: Brief) -> str:
    numbers = _source_number_map(brief)
    out: List[str] = []

    out.append(f"# Clarity Brief: {brief.topic}")
    out.append("")
    out.append(f"> {brief.disclaimer}")
    out.append("")
    if brief.generated_at:
        out.append(f"*Generated: {brief.generated_at} · Citation coverage: "
                   f"{brief.coverage_pct:.0f}%*")
        out.append("")

    out.append("## Findings")
    out.append("")
    for claim in brief.claims:
        marks = _inline_marks([c.source_id for c in claim.citations], numbers)
        out.append(f"- {claim.text} {marks}".rstrip())
    out.append("")

    out.append("## What we're uncertain about")
    out.append("")
    for u in brief.uncertainty:
        out.append(f"- {u}")
    out.append("")

    out.append("## References")
    out.append("")
    for s in brief.sources:
        n = numbers[s.id]
        retrieved = f" (retrieved {s.retrieved_at})" if s.retrieved_at else ""
        out.append(f"{n}. [{s.title or s.url}]({s.url}){retrieved}")
    out.append("")

    return "\n".join(out)


def assemble_html(brief: Brief) -> str:
    numbers = _source_number_map(brief)

    def esc(x: str) -> str:
        return html.escape(x or "")

    parts: List[str] = []
    parts.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    parts.append(f"<title>Clarity Brief: {esc(brief.topic)}</title>")
    parts.append(
        "<style>"
        "body{font:16px/1.6 -apple-system,Segoe UI,Roboto,sans-serif;"
        "max-width:720px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
        ".disclaimer{background:#fff8e1;border:1px solid #f0d98c;"
        "padding:.75rem 1rem;border-radius:8px;font-size:.9rem}"
        "sup a{text-decoration:none} h1{font-size:1.5rem}"
        ".meta{color:#666;font-size:.85rem} ol{padding-left:1.2rem}"
        "</style></head><body>"
    )
    parts.append(f"<h1>Clarity Brief: {esc(brief.topic)}</h1>")
    parts.append(f"<p class='disclaimer'>{esc(brief.disclaimer)}</p>")
    if brief.generated_at:
        parts.append(
            f"<p class='meta'>Generated: {esc(brief.generated_at)} · "
            f"Citation coverage: {brief.coverage_pct:.0f}%</p>"
        )

    parts.append("<h2>Findings</h2><ul>")
    for claim in brief.claims:
        nums = sorted({numbers[c.source_id] for c in claim.citations
                       if c.source_id in numbers})
        marks = "".join(
            f"<sup><a href='#ref{n}'>[{n}]</a></sup>" for n in nums
        )
        parts.append(f"<li>{esc(claim.text)} {marks}</li>")
    parts.append("</ul>")

    parts.append("<h2>What we're uncertain about</h2><ul>")
    for u in brief.uncertainty:
        parts.append(f"<li>{esc(u)}</li>")
    parts.append("</ul>")

    parts.append("<h2>References</h2><ol>")
    for s in brief.sources:
        n = numbers[s.id]
        retrieved = f" (retrieved {esc(s.retrieved_at)})" if s.retrieved_at else ""
        label = esc(s.title or s.url)
        parts.append(
            f"<li id='ref{n}'><a href='{esc(s.url)}'>{label}</a>{retrieved}</li>"
        )
    parts.append("</ol>")

    parts.append("</body></html>")
    return "".join(parts)
