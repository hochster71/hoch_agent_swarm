"""Champion loader — the wire between the BRAIN and real execution.

Before this module, champion prompts were consumed only by the dashboard and the
Ask-the-BRAIN retrieval layer: the 700+ evolved genes influenced no agent, mission,
or product build. This closes that gap under the live-real-only doctrine:

  - operating_prompt(task_class, domain) returns the CURRENT champion prompt for a
    task class from that factory's champion registry, or the caller's fallback.
  - Every resolution is traceable: the return includes gene_id, score, generation,
    and source ("champion" | "fallback") so any output produced with it can be tied
    back to the exact gene in the evidence ledger — no silent substitution.
  - Read-only, stdlib-only, deterministic. No model calls, no writes, $0.

Usage (agents / mission runners):
    from backend.factory.champion_loader import operating_prompt
    res = operating_prompt("Incident Response", fallback=MY_HARDCODED_PROMPT)
    system_prompt = res["prompt"]        # champion text or fallback
    provenance    = res["provenance"]    # log this alongside the output
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from backend.factory.registry import get_factory


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _load_registry(domain: str) -> Dict[str, Any]:
    f = get_factory(domain)
    if not f:
        return {}
    try:
        return json.loads(Path(f.champion_registry).read_text(encoding="utf-8"))
    except Exception:
        return {}


def operating_prompt(task_class: str, domain: str = "software",
                     fallback: Optional[str] = None) -> Dict[str, Any]:
    """Resolve task_class -> current champion prompt for a factory domain.

    Exact match on normalized class name first; unique-substring match second
    (so "incident response" finds "Incident Response"). Ambiguous or missing ->
    fallback, honestly labeled. Never raises: execution must not break because
    the brain is unavailable.
    """
    reg = _load_registry(domain)
    champs = reg.get("champions", {}) or {}
    gen = reg.get("generation")

    want = _norm(task_class)
    by_norm = {_norm(k): (k, v) for k, v in champs.items()}

    hit = by_norm.get(want)
    if hit is None and want:
        subs = [(k, v) for nk, (k, v) in by_norm.items() if want in nk or nk in want]
        if len(subs) == 1:
            hit = subs[0]

    if hit is not None:
        cls, c = hit
        prompt = c.get("prompt") or c.get("text") or ""
        if not prompt and c.get("gene_id"):
            # Some registries (music/research) store only gene_id refs; dereference the pool.
            f = get_factory(domain)
            try:
                pool = json.loads(Path(f.gene_pool).read_text(encoding="utf-8")).get("genes", {})
                g = pool.get(c["gene_id"]) or next(
                    (v for v in (pool.values() if isinstance(pool, dict) else pool)
                     if v.get("gene_id") == c["gene_id"]), None)
                if g:
                    prompt = g.get("prompt") or g.get("text") or ""
            except Exception:
                pass
        if prompt:
            return {
                "prompt": prompt,
                "source": "champion",
                "provenance": {
                    "gene_id": c.get("gene_id"),
                    "task_class": cls,
                    "domain": domain,
                    "score": c.get("score"),
                    "generation": gen,
                },
            }

    return {
        "prompt": fallback or "",
        "source": "fallback",
        "provenance": {"gene_id": None, "task_class": task_class,
                       "domain": domain, "score": None, "generation": gen,
                       "reason": "no champion for class" if want else "empty task_class"},
    }
