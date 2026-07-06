"""Run one gene-expansion pass: grow every thin class toward min_pool using the local model.

Pipeline: gap_analysis -> for each THIN_POOL class, synthesize+admit up to its deficit ->
append admitted genes to the gene pool (gene_pool_m0.json) and log provenance. Admitted genes then
compete in the next run_m0 selection like any other gene (they may or may not become champions).

No live model => skips cleanly (mechanical loop unaffected). Never fabricates: only genes that pass
the dual gate in gene_expansion are written, each labeled SYNTHETIC_ADMITTED with its source.

    python3 -m backend.brain_convergence.expand_run [max_classes] [per_class_cap]
"""
import sys
import json
import datetime
from pathlib import Path

from backend.brain_convergence.local_model_bridge import detect_local_backend
from backend.brain_convergence.gene_expansion import expand_class
from backend.brain_convergence import gap_analysis

ROOT = Path(__file__).resolve().parent.parent.parent
D = ROOT / "data" / "prompt_brain"
GENE_POOL = D / "gene_pool_m0.json"
RUBRIC = str(ROOT / "config" / "prompt_score_rubric.yaml")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def run(max_classes: int = 8, per_class_cap: int = 6) -> dict:
    backend = detect_local_backend()
    if not backend:
        print("expand_run: no live local model — skipped (start Ollama to grow thin pools).")
        return {"skipped": True}

    pool = json.loads(GENE_POOL.read_text(encoding="utf-8"))
    genes = pool.get("genes", {})
    # index genes by class
    by_class = {}
    existing_hashes = set()
    for gid, g in genes.items():
        by_class.setdefault(g.get("task_class", "uncategorized"), []).append(g)
        h = g.get("content_hash")
        if h:
            existing_hashes.add(h)

    res = gap_analysis.analyze(str(GENE_POOL), str(D / "champion_registry.json"),
                               str(D / "convergence_status.json"))
    thin = res["thin_classes"][:max_classes]

    ts = _now()
    total_admitted = 0
    report = []
    for row in thin:
        cls = row["class"]
        deficit = min(per_class_cap, row["pool_deficit"] or per_class_cap)
        cls_genes = by_class.get(cls, [])
        if not cls_genes:
            continue
        admitted = expand_class(cls, cls_genes, n_target=deficit, backend=backend,
                                rubric_path=RUBRIC, existing_hashes=existing_hashes)
        for a in admitted:
            genes[a["gene_id"]] = a
            existing_hashes.add(a["content_hash"])
            with open(D / "expanded_genes.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"at": ts, **a}) + "\n")
        total_admitted += len(admitted)
        report.append((cls, len(admitted), deficit))

    if total_admitted:
        # recompute class_sizes + count, persist
        sizes = {}
        for g in genes.values():
            c = g.get("task_class", "uncategorized")
            sizes[c] = sizes.get(c, 0) + 1
        pool["genes"] = genes
        pool["count"] = len(genes)
        pool["class_sizes"] = dict(sorted(sizes.items(), key=lambda x: -x[1]))
        GENE_POOL.write_text(json.dumps(pool, indent=2), encoding="utf-8")

    print(f"expand_run: {total_admitted} synthetic genes admitted across {len(report)} thin classes "
          f"via {backend['model']} | pool now {len(genes)} genes")
    for cls, got, want in report:
        print(f"   {cls}: +{got}/{want}")
    return {"admitted": total_admitted, "pool_count": len(genes), "classes": report}


if __name__ == "__main__":
    mc = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    run(mc, cap)
