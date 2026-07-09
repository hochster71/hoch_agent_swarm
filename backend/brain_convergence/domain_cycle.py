"""Domain improvement cycle — give HMF / HRF (and any factory) the SAME loop as HASF.

One tick: EXPAND thin classes with the factory's own scorer + the $0 local model -> re-SELECT the
best champion per class -> record CONVERGENCE with history (so the mean can climb and the console
draws a real improvement graph). Honest: with no local model it just re-selects (flat, accumulates a
history point); with a model, admitted genes lift champions and the mean genuinely improves. State
comes from the honest-convergence guard — a factory only reads IMPROVING when it truly gained.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any

from backend.factory.registry import get_factory
from backend.brain_convergence.local_model_bridge import detect_local_backend
from backend.brain_convergence.gene_expansion import expand_class
from backend.brain_convergence import convergence as C


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _min_pool(domain: str) -> int:
    return 6 if domain == "software" else 3


def cycle(domain: str, per_class_cap: int = 4) -> Dict[str, Any]:
    f = get_factory(domain)
    if not f or not Path(f.gene_pool).exists():
        return {"error": f"no gene pool for {domain}"}
    pool = json.loads(Path(f.gene_pool).read_text(encoding="utf-8"))
    genes = pool.get("genes", {})
    score = f.scorer()
    rubric = str(f.rubric)
    backend = detect_local_backend()

    by_class: Dict[str, list] = {}
    existing = set()
    for gid, g in genes.items():
        by_class.setdefault(g.get("task_class", "uncategorized"), []).append(g)
        if g.get("content_hash"):
            existing.add(g["content_hash"])

    # 1. EXPAND thin classes (only if a live model is up — $0 generate path).
    admitted_total = 0
    if backend:
        mp = _min_pool(domain)
        for cls, items in list(by_class.items()):
            if len(items) >= mp:
                continue
            admitted = expand_class(cls, items, n_target=min(per_class_cap, mp - len(items)),
                                    backend=backend, rubric_path=rubric,
                                    existing_hashes=existing, score_fn=score)
            for a in admitted:
                genes[a["gene_id"]] = a
                by_class[cls].append(a)
                existing.add(a["content_hash"])
            admitted_total += len(admitted)
        if admitted_total:
            sizes = {}
            for g in genes.values():
                sizes[g.get("task_class", "uncategorized")] = sizes.get(g.get("task_class", "uncategorized"), 0) + 1
            pool["genes"] = genes
            pool["count"] = len(genes)
            pool["class_sizes"] = dict(sorted(sizes.items(), key=lambda x: -x[1]))
            Path(f.gene_pool).write_text(json.dumps(pool, indent=2), encoding="utf-8")

    # 2. SELECT champion per class with the domain scorer.
    champions = {}
    from backend.brain_convergence.scorer import blended_score as _blend
    for cls, items in by_class.items():
        scored_items = []
        for g in items:
            rub_score = score(g.get("prompt", ""), rubric)["overall"]
            gid = g.get("gene_id")
            blend = _blend(gid, rub_score)
            scored_items.append((blend["score"], rub_score, blend["method"], g))
        
        best_blend_s, best_rub_s, best_method, best = max(scored_items, key=lambda x: x[0])
        champions[cls] = {
            "gene_id": best.get("gene_id"),
            "title": best.get("title", ""),
            "score": best_rub_s,
            "blended_score": best_blend_s,
            "fitness_method": best_method,
            "state": "SELECTED",
            "domain": domain,
            "pool_size": len(items)
        }
    gen = 1
    if Path(f.champion_registry).exists():
        try:
            gen = json.loads(Path(f.champion_registry).read_text()).get("generation", 0) + 1
        except Exception:
            gen = 1
    Path(f.champion_registry).parent.mkdir(parents=True, exist_ok=True)
    Path(f.champion_registry).write_text(json.dumps(
        {"schema": "brain-champion-registry", "domain": domain, "generation": gen,
         "champions": champions, "at": _now()}, indent=2), encoding="utf-8")

    mean = round(sum(c.get("blended_score", c["score"]) for c in champions.values()) / len(champions), 3) if champions else 0.0

    # 3. CONVERGENCE with history (honest state machine, per factory).
    conv = C.update(str(f.convergence_status), gen, mean, epsilon=0.5, patience=3,
                    improver_online=bool(backend))
    return {"domain": domain, "code": f.code, "generation": gen, "champions": len(champions),
            "mean": mean, "admitted": admitted_total, "state": conv["state"]}



if __name__ == "__main__":
    import sys
    for d in (sys.argv[1:] or ["music", "research"]):
        r = cycle(d)
        if "error" in r:
            print(f"{d}: {r['error']}")
        else:
            print(f"{r['code']} ({r['domain']}): gen {r['generation']} · mean {r['mean']} · "
                  f"+{r['admitted']} genes · {r['state']}")
