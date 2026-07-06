"""Domain-agnostic champion selection — crown a champion per class for ANY Factory.

The software `run_m0` pipeline is tied to the software library + scorer. This crowns a champion per
class for any registered Factory (HMF/HRF/...) using THAT factory's own scorer and gene pool, so a
seeded domain becomes live champion-bearing state without the software-specific machinery.

Mechanical, $0, deterministic. Honest labeling: champions crowned here are state SELECTED_FROM_SEED
(best-scoring seed per class), and the domain convergence state is SELECTED — NOT 'improving' or
'converged'. It becomes IMPROVING only once the live-model improvement loop actually beats a seed.
No fabrication: every score comes from the domain scorer applied to real gene text.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any

from backend.factory.registry import get_factory


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def select(domain: str) -> Dict[str, Any]:
    f = get_factory(domain)
    if not f:
        return {"error": f"unknown domain {domain}"}
    if not Path(f.gene_pool).exists():
        return {"error": f"no gene pool for {domain}"}

    pool = json.loads(Path(f.gene_pool).read_text(encoding="utf-8"))
    genes = pool.get("genes", {})
    score = f.scorer()
    rubric = str(f.rubric)

    by_class: Dict[str, list] = {}
    for gid, g in genes.items():
        by_class.setdefault(g.get("task_class", "uncategorized"), []).append((gid, g))

    champions: Dict[str, Any] = {}
    for cls, items in by_class.items():
        scored = [(score(g.get("prompt", ""), rubric)["overall"], gid, g) for gid, g in items]
        best_s, best_gid, best_g = max(scored, key=lambda x: x[0])
        champions[cls] = {
            "gene_id": best_gid, "title": best_g.get("title", ""),
            "score": best_s, "state": "SELECTED_FROM_SEED", "domain": domain,
            "pool_size": len(items),
        }

    # bump generation off any prior registry
    gen = 1
    if Path(f.champion_registry).exists():
        try:
            gen = json.loads(Path(f.champion_registry).read_text()).get("generation", 0) + 1
        except Exception:
            gen = 1

    reg = {"schema": "brain-champion-registry", "domain": domain,
           "generation": gen, "champions": champions, "at": _now()}
    Path(f.champion_registry).parent.mkdir(parents=True, exist_ok=True)
    Path(f.champion_registry).write_text(json.dumps(reg, indent=2), encoding="utf-8")

    mean = round(sum(c["score"] for c in champions.values()) / len(champions), 3) if champions else 0.0
    conv = {"schema": "brain-convergence-status-m0", "domain": domain, "generation": gen,
            "mean_score": mean, "state": "SELECTED", "champions": len(champions), "at": _now()}
    Path(f.convergence_status).write_text(json.dumps(conv, indent=2), encoding="utf-8")

    return {"domain": domain, "code": f.code, "champions": len(champions), "mean": mean, "generation": gen}


if __name__ == "__main__":
    import sys
    doms = sys.argv[1:] or ["music", "research"]
    for d in doms:
        r = select(d)
        if "error" in r:
            print(f"{d}: {r['error']}")
        else:
            print(f"{r['code']} ({r['domain']}): crowned {r['champions']} champions, mean {r['mean']}, gen {r['generation']}")
