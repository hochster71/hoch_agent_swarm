"""M0 BRAIN Convergence — Harvest stage.

First stage of the self-improving prompt loop (see docs/moonshot/HAS_BRAIN_CONVERGENCE_MOONSHOT.md).
Loads the canonical prompt library into a normalized, deduped gene pool keyed by task_class.

Pure stdlib, deterministic, no network, no live LLM — safe to run at Rung 1 on the burn-in daemon.
Dedup is two-layer: exact content-hash collisions AND capability-signature aliases (PL010) are
collapsed so the gene pool carries one representative per distinct capability.
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional


def _hash(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()


def normalize_gene(rec: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(rec.get("prompt", "")).strip()
    outputs = rec.get("outputs", "")
    if isinstance(outputs, list):
        outputs = ", ".join(str(o) for o in outputs)
    gid = rec.get("id") or _hash(str(rec.get("title", "")) + prompt)[:16]
    return {
        "gene_id": gid,
        "task_class": rec.get("category", "uncategorized"),
        "industry": rec.get("industry", ""),
        "title": rec.get("title", ""),
        "mission": rec.get("mission", ""),
        "outputs": outputs,
        "prompt": prompt,
        "content_hash": _hash(prompt),
    }


def harvest(library_path: str, aliases_path: Optional[str] = None) -> Dict[str, Any]:
    """Return {genes, by_class, count, collapsed, task_classes}. Deterministic."""
    recs = json.loads(Path(library_path).read_text(encoding="utf-8"))
    if isinstance(recs, dict):
        recs = recs.get("entries", recs.get("prompts", []))
    aliases = {}
    if aliases_path and Path(aliases_path).exists():
        aliases = json.loads(Path(aliases_path).read_text(encoding="utf-8"))

    genes: Dict[str, Any] = {}
    by_class: Dict[str, list] = {}
    seen_content = set()
    collapsed = 0
    for r in recs:
        g = normalize_gene(r)
        if g["gene_id"] in aliases:            # capability-duplicate → collapse to canonical
            collapsed += 1
            continue
        if g["content_hash"] in seen_content:  # exact content duplicate
            collapsed += 1
            continue
        seen_content.add(g["content_hash"])
        genes[g["gene_id"]] = g
        by_class.setdefault(g["task_class"], []).append(g["gene_id"])
    return {
        "genes": genes,
        "by_class": by_class,
        "count": len(genes),
        "collapsed": collapsed,
        "task_classes": len(by_class),
    }


def write_gene_pool(result: Dict[str, Any], out_path: str) -> str:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "schema": "brain-convergence-gene-pool-m0",
        "count": result["count"],
        "collapsed": result["collapsed"],
        "task_classes": result["task_classes"],
        "class_sizes": {k: len(v) for k, v in sorted(result["by_class"].items(), key=lambda x: -len(x[1]))},
        "genes": result["genes"],
    }, indent=2), encoding="utf-8")
    return str(p)
