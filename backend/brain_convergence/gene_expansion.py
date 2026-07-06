"""BRAIN gene expansion — the QUANTITY lever ($0, local model).

The gap analysis shows thin classes (1-3 genes) whose champions are quantity-capped: with almost
no competition, the crowned champion can't be better than the tiny pool it came from. This module
grows those pools by having the local model synthesize NEW candidate genes seeded from the class's
strongest existing gene.

Anti-Goodhart admission (dual gate) — a synthetic gene enters the pool ONLY if:
  (a) it is NOT a content duplicate of an existing/other new gene, AND
  (b) its mechanical score >= the class median (it is at least as disciplined as typical), AND
  (c) an LLM judge prefers it over the class's WEAKEST gene (real quality, not keyword stuffing).
The mechanical scorer rewards discipline keywords, so (b) alone would admit keyword-stuffed junk;
(c) is the judge veto. Every admitted gene is labeled SYNTHETIC_ADMITTED with its real source —
never presented as human-authored or as verified-on-held-out.

No live model => generates nothing and says so (honest; mechanical loop is unaffected).
"""
import hashlib
import statistics
from typing import Dict, Any, List, Optional, Callable

from backend.brain_convergence.local_model_bridge import detect_local_backend, generate_candidates
from backend.brain_convergence.improve_loop import llm_judge
from backend.brain_convergence.scorer import score_prompt


def _hash(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()


def expand_class(task_class: str,
                 class_genes: List[Dict[str, Any]],
                 n_target: int,
                 backend: Optional[Dict[str, str]] = None,
                 rubric_path: Optional[str] = None,
                 existing_hashes: Optional[set] = None,
                 generate_fn: Callable = generate_candidates,
                 judge_fn: Callable = llm_judge,
                 score_fn: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """Synthesize up to n_target admitted genes for task_class. Returns list of gene dicts
    (state=SYNTHETIC_ADMITTED). Injected generate_fn/judge_fn make the gate unit-testable.

    score_fn lets any Factory drive the gate with ITS OWN domain scorer (software/music/research);
    defaults to the software discipline scorer for backward compatibility."""
    sf = score_fn or score_prompt
    backend = backend if backend is not None else detect_local_backend()
    if not backend or not class_genes or n_target <= 0:
        return []

    scored = [(sf(g.get("prompt", ""), rubric_path)["overall"], g) for g in class_genes]
    scored.sort(key=lambda x: x[0])
    weakest_text = scored[0][1].get("prompt", "")
    strongest_text = scored[-1][1].get("prompt", "")
    class_scores = [s for s, _ in scored]
    median = statistics.median(class_scores) if class_scores else 0.0

    seen = set(existing_hashes or set())
    for _, g in scored:
        seen.add(_hash(g.get("prompt", "")))

    admitted: List[Dict[str, Any]] = []
    # Over-generate (2x) so the gate can reject and still hope to hit n_target.
    cands = generate_fn(strongest_text, task_class, n=max(2, n_target * 2), backend=backend)
    for c in cands:
        if len(admitted) >= n_target:
            break
        text = (c.get("text") or "").strip()
        if not text:
            continue
        h = _hash(text)
        if h in seen:                                   # gate (a): dedup
            continue
        mech = sf(text, rubric_path)["overall"]
        if mech < median:                               # gate (b): >= class median
            continue
        judged = judge_fn(backend, weakest_text, text, task_class)  # gate (c): beats weakest
        if judged.get("winner") != "B":
            continue
        seen.add(h)
        admitted.append({
            "gene_id": f"syn-{task_class[:6].strip().replace(' ', '')}-{h[:12]}",
            "task_class": task_class,
            "title": f"{task_class} synthetic gene",
            "prompt": text,
            "content_hash": h,
            "mech_score": mech,
            "source": c.get("source", f"LOCAL:{backend.get('kind')}:{backend.get('model')}"),
            "judge": "LOCAL_LLM_JUDGE",
            "state": "SYNTHETIC_ADMITTED",              # honest label: admitted, not verified
        })
    return admitted
