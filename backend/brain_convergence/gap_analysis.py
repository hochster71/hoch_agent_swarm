"""BRAIN gap-analysis — the audit, codified and repeatable.

Reads the REAL state (gene pool, champion registry, convergence status) and computes, per task
class, the *binding constraint* on getting smarter:

  THIN_POOL      gene_count < min_pool  -> quantity is the cap; expansion lever
  NO_CHAMPION    genes exist but no champion crowned -> coverage gap; run selection
  LOW_CEILING    pool adequate but champion score < target -> quality lever; improve
  SATURATED      score >= target -> class is near its honest ceiling (for now)

Also detects taxonomy DRIFT: near-duplicate class names ("Governance" vs "Governance / Compliance")
that fragment pools which should compete together.

Pure stdlib, deterministic, no network, no live model. Safe at Rung 1. Writes a machine-readable
gaps JSON (for the console) and a human report. No fabrication: every number traces to a state file;
missing inputs degrade to explicit "UNKNOWN", never invented values.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Honest thresholds — tune in one place, surfaced in the report so the reader sees the policy.
MIN_POOL = 6          # below this, a champion has too little competition -> quantity-capped
TARGET_SCORE = 70.0   # below this with an adequate pool -> quality lever is the constraint
DRIFT_RATIO = 0.72    # normalized-name similarity above which two classes are merge candidates


def _load(p: str, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def _norm(name: str) -> str:
    """Normalize a class name for drift comparison: lowercase, punctuation->space, de-pluralize.
    Deliberately does NOT strip domain words — removing them can empty a name and hide the very
    overlap we are looking for (e.g. 'Governance' vs 'Governance / Compliance')."""
    s = re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()
    toks = [re.sub(r"s$", "", t) if len(t) > 3 else t for t in s.split()]  # trivial singularize
    return " ".join(toks)


def _similar(a: str, b: str) -> float:
    """max(Jaccard, containment). Containment catches subset drift ('gov' ⊂ 'gov compliance')
    where Jaccard alone dilutes it. Deterministic, no deps."""
    ta, tb = set(_norm(a).split()), set(_norm(b).split())
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    jaccard = inter / len(ta | tb)
    containment = inter / min(len(ta), len(tb))
    return max(jaccard, containment)


def analyze(gene_pool_path: str, registry_path: str, status_path: str,
            min_pool: int = MIN_POOL, target: float = TARGET_SCORE) -> Dict[str, Any]:
    gp = _load(gene_pool_path, {})
    reg = _load(registry_path, {})
    conv = _load(status_path, {})

    class_sizes: Dict[str, int] = gp.get("class_sizes") or {}
    if not class_sizes:  # derive from genes if class_sizes absent
        genes = gp.get("genes", {})
        vals = genes.values() if isinstance(genes, dict) else genes
        for g in vals:
            c = g.get("task_class", "uncategorized")
            class_sizes[c] = class_sizes.get(c, 0) + 1

    champs = reg.get("champions", {})
    champ_scores = {k: v.get("score", 0.0) for k, v in champs.items()}
    champ_states = {k: v.get("state", "") for k, v in champs.items()}

    # Union of class namespaces (gene-pool classes and champion classes can differ — itself a gap).
    all_classes = sorted(set(class_sizes) | set(champs))
    per_class: List[Dict[str, Any]] = []
    for c in all_classes:
        genes = class_sizes.get(c, 0)
        has_champ = c in champs
        score = champ_scores.get(c)
        if genes < min_pool and genes > 0:
            constraint = "THIN_POOL"
        elif genes == 0 and has_champ:
            constraint = "ORPHAN_CHAMPION"     # champion but no genes in pool (namespace drift)
        elif genes > 0 and not has_champ:
            constraint = "NO_CHAMPION"
        elif score is not None and score < target:
            constraint = "LOW_CEILING"
        elif score is not None:
            constraint = "SATURATED"
        else:
            constraint = "UNKNOWN"
        per_class.append({
            "class": c, "genes": genes, "has_champion": has_champ,
            "score": score, "state": champ_states.get(c), "constraint": constraint,
            "pool_deficit": max(0, min_pool - genes) if genes > 0 else 0,
        })

    # Taxonomy drift: pairs of distinct classes whose normalized names are highly similar.
    names = list(class_sizes) + [c for c in champs if c not in class_sizes]
    drift = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            sim = _similar(names[i], names[j])
            if sim >= DRIFT_RATIO and _norm(names[i]) and _norm(names[j]):
                drift.append({"a": names[i], "b": names[j], "similarity": round(sim, 2)})
    drift.sort(key=lambda d: -d["similarity"])

    # Global rollups.
    total_genes = sum(class_sizes.values())
    top5 = sorted(class_sizes.values(), reverse=True)[:5]
    by_constraint: Dict[str, int] = {}
    for r in per_class:
        by_constraint[r["constraint"]] = by_constraint.get(r["constraint"], 0) + 1

    thin = [r for r in per_class if r["constraint"] == "THIN_POOL"]
    lowc = [r for r in per_class if r["constraint"] == "LOW_CEILING"]
    # Total synthetic genes needed to bring every thin class up to min_pool.
    expansion_needed = sum(r["pool_deficit"] for r in thin)

    return {
        "schema": "brain-gap-analysis-v1",
        "policy": {"min_pool": min_pool, "target_score": target, "drift_ratio": DRIFT_RATIO},
        "totals": {
            "gene_classes": len(class_sizes),
            "champion_classes": len(champs),
            "total_genes": total_genes,
            "top5_share": round(sum(top5) / total_genes, 3) if total_genes else 0.0,
            "mean_champion_score": conv.get("mean_score"),
            "generation": conv.get("generation"),
            "state": conv.get("state", "UNKNOWN"),
        },
        "by_constraint": by_constraint,
        "expansion_needed_genes": expansion_needed,
        "thin_classes": sorted(thin, key=lambda r: (r["genes"], r["class"])),
        "low_ceiling_classes": sorted(lowc, key=lambda r: (r["score"] if r["score"] is not None else 0, r["class"])),
        "taxonomy_drift": drift,
        "per_class": sorted(per_class, key=lambda r: (r["score"] if r["score"] is not None else -1)),
    }


def write_report(result: Dict[str, Any], json_out: str, md_out: str) -> Dict[str, str]:
    Path(json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(json_out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    t = result["totals"]
    lines = [
        "# BRAIN Gap Analysis", "",
        f"- generation: **{t['generation']}**  |  mean champion score: **{t['mean_champion_score']}**  |  state: **{t['state']}**",
        f"- gene classes: **{t['gene_classes']}**  |  champion classes: **{t['champion_classes']}**  |  total genes: **{t['total_genes']}**",
        f"- concentration (top-5 share of gene pool): **{t['top5_share']*100:.1f}%**",
        f"- policy: min_pool={result['policy']['min_pool']}, target_score={result['policy']['target_score']}",
        "",
        "## Binding constraint by class",
        "",
        "| constraint | classes |", "|---|---|",
    ]
    for k, v in sorted(result["by_constraint"].items(), key=lambda x: -x[1]):
        lines.append(f"| {k} | {v} |")
    lines += ["", f"**Synthetic genes needed to lift every thin class to min_pool: {result['expansion_needed_genes']}**", ""]

    lines += ["## Thin classes (quantity-capped — expansion lever)", "", "| class | genes | need | score |", "|---|---|---|---|"]
    for r in result["thin_classes"]:
        lines.append(f"| {r['class']} | {r['genes']} | +{r['pool_deficit']} | {r['score']} |")
    lines += ["", "## Low-ceiling classes (adequate pool, quality lever)", "", "| class | genes | score |", "|---|---|---|"]
    for r in result["low_ceiling_classes"]:
        lines.append(f"| {r['class']} | {r['genes']} | {r['score']} |")
    if result["taxonomy_drift"]:
        lines += ["", "## Taxonomy drift (merge candidates)", "", "| a | b | similarity |", "|---|---|---|"]
        for d in result["taxonomy_drift"]:
            lines.append(f"| {d['a']} | {d['b']} | {d['similarity']} |")

    Path(md_out).parent.mkdir(parents=True, exist_ok=True)
    Path(md_out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": json_out, "md": md_out}


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent.parent
    D = ROOT / "data" / "prompt_brain"
    res = analyze(str(D / "gene_pool_m0.json"), str(D / "champion_registry.json"),
                  str(D / "convergence_status.json"))
    out = write_report(res, str(D / "gap_analysis.json"),
                       str(ROOT / "docs" / "moonshot" / "BRAIN_GAP_ANALYSIS.md"))
    t = res["totals"]
    print(f"gap-analysis: {t['gene_classes']} classes, {t['total_genes']} genes, "
          f"top5={t['top5_share']*100:.0f}% | thin={len(res['thin_classes'])} "
          f"low_ceiling={len(res['low_ceiling_classes'])} drift={len(res['taxonomy_drift'])} "
          f"| need {res['expansion_needed_genes']} genes -> {out['json']}")
