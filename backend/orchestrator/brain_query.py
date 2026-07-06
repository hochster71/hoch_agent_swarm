"""Chat with the BRAIN — grounded, cited, $0 query layer.

Ask the BRAIN intelligent questions about itself. This does retrieval-augmented answering over the
BRAIN's OWN knowledge — every factory's gene pool + champions + gaps + factory states + AI Michael's
latest decision — then (if a local model is up) synthesizes an answer that MUST stay grounded in the
retrieved context and cite the gene_ids / state it used.

Evidence discipline (no fake-green, applied to Q&A):
  - The answer is built ONLY from real retrieved context; the model is instructed to say
    "insufficient evidence in the BRAIN" rather than invent.
  - Sources (gene_ids / state keys actually used) are returned so any claim is traceable.
  - No local model up => retrieval_only mode: returns the relevant genes/state WITHOUT synthesis,
    so it can never hallucinate. Honest, still useful.
Pure stdlib + the local model bridge; deterministic retrieval.
"""
import re
import json
from pathlib import Path
from typing import Dict, Any, List

from backend.factory.registry import list_factories

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "prompt_brain"

_STOP = set("the a an of to for and or in on is are be do does how what which who when where why "
            "with from this that these those it its our we i you can should would could our my me "
            "brain hoch factory please tell show give".split())


def _toks(s: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if t and t not in _STOP and len(t) > 2]


def _load(p, d):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


def _all_genes() -> List[Dict[str, Any]]:
    out = []
    for f in list_factories():
        gp = _load(f.gene_pool, {})
        genes = gp.get("genes", {})
        items = genes.values() if isinstance(genes, dict) else genes
        for g in items:
            out.append({"gene_id": g.get("gene_id"), "domain": f.domain, "code": f.code,
                        "task_class": g.get("task_class", ""), "title": g.get("title", ""),
                        "prompt": g.get("prompt", "")})
    return out


def retrieve(question: str, k: int = 6) -> List[Dict[str, Any]]:
    q = set(_toks(question))
    if not q:
        return []
    scored = []
    for g in _all_genes():
        title_t = set(_toks(g["title"])) | set(_toks(g["task_class"]))
        body_t = set(_toks(g["prompt"]))
        score = 3 * len(q & title_t) + len(q & body_t)
        if score:
            scored.append((score, g))
    scored.sort(key=lambda x: -x[0])
    return [{"gene_id": g["gene_id"], "code": g["code"], "task_class": g["task_class"],
             "title": g["title"], "snippet": g["prompt"][:240], "score": s}
            for s, g in scored[:k]]


def _state_context() -> Dict[str, Any]:
    facs = []
    for f in list_factories():
        conv = _load(f.convergence_status, {})
        reg = _load(f.champion_registry, {})
        facs.append({"code": f.code, "domain": f.domain, "state": conv.get("state", "SEEDED"),
                     "mean": conv.get("mean_score"), "champions": len(reg.get("champions", {}))})
    return {"factories": facs,
            "gaps": _load(DATA / "gap_analysis.json", {}).get("by_constraint", {}),
            "orchestrator": _load(DATA / "orchestrator_brief.json", {}).get("summary")}


def ask(question: str, k: int = 6) -> Dict[str, Any]:
    hits = retrieve(question, k)
    state = _state_context()
    sources = [h["gene_id"] for h in hits]

    # Build grounded context.
    ctx_lines = [f"[{h['code']}·{h['task_class']}] {h['title']}: {h['snippet']}" for h in hits]
    ctx = "FACTORY STATE: " + json.dumps(state) + "\n\nRELEVANT GENES:\n" + "\n".join(ctx_lines)

    try:
        from backend.brain_convergence.local_model_bridge import (
            detect_local_backend, _ollama_generate, _lmstudio_generate)
        backend = detect_local_backend()
    except Exception:
        backend = None

    if not backend:
        return {"mode": "retrieval_only", "grounded": True, "answer": None,
                "hits": hits, "state": state, "sources": sources,
                "note": "No local model up — returning the relevant genes/state without synthesis "
                        "(cannot hallucinate). Start Ollama for a written answer."}

    prompt = (
        "You are the HOCH BRAIN answering a question about YOURSELF. Answer ONLY from the context "
        "below. Cite the factory codes / gene titles you used. If the context does not contain the "
        "answer, reply exactly: 'Insufficient evidence in the BRAIN.' Be concise and concrete.\n\n"
        f"CONTEXT:\n{ctx}\n\nQUESTION: {question}\n\nANSWER:"
    )
    try:
        if backend["kind"] == "ollama":
            ans = _ollama_generate(backend["base"], backend["model"], prompt, 60.0)
        else:
            ans = _lmstudio_generate(backend["base"], backend["model"], prompt, 60.0)
    except Exception as e:
        ans = None
        return {"mode": "retrieval_only", "grounded": True, "answer": None, "hits": hits,
                "state": state, "sources": sources, "note": f"model error: {e}"}

    return {"mode": "synthesized", "grounded": True, "answer": ans, "model": backend["model"],
            "hits": hits, "state": state, "sources": sources,
            "note": "Answer synthesized by the local model, grounded in the cited genes/state."}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Which factories are weakest and what should they work on next?"
    r = ask(q)
    print(f"Q: {q}\nmode: {r['mode']}")
    if r.get("answer"):
        print("A:", r["answer"])
    print("sources:", r["sources"])
    for h in r["hits"][:4]:
        print(f"  [{h['code']}] {h['title']} (score {h['score']})")
