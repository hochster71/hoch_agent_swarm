"""M0 BRAIN Convergence — Champion registry.

Persists one champion prompt per task_class with its held-out score and evidence trail.
Promotion rule (evidence-disciplined): a candidate replaces the incumbent ONLY if it strictly
beats it on the held-out score. Ties keep the incumbent (no churn). Every promotion records the
gene_id, score, generation, split provenance hash, and timestamp — so a champion is always
traceable to the exact evaluation that crowned it.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def load_registry(path: str) -> Dict[str, Any]:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"schema": "brain-convergence-champions-m0", "generation": 0, "champions": {}}


def promote(registry: Dict[str, Any], candidates: Dict[str, Dict[str, Any]],
            provenance_hash: str) -> Dict[str, Any]:
    """candidates: {task_class: {gene_id, title, score}}. Returns {registry, promoted, held}."""
    champs = registry.setdefault("champions", {})
    registry["generation"] = registry.get("generation", 0) + 1
    gen = registry["generation"]
    promoted, held = [], []
    for cls, cand in candidates.items():
        inc = champs.get(cls)
        if inc is None or cand["score"] > inc["score"]:
            champs[cls] = {
                "gene_id": cand["gene_id"],
                "title": cand.get("title", ""),
                "score": cand["score"],
                "state": "VERIFIED_ON_HELDOUT",  # only held-out winners are crowned
                "generation": gen,
                "provenance_hash": provenance_hash,
                "promoted_at": _now(),
                "beat_score": (inc["score"] if inc else None),
            }
            promoted.append(cls)
        else:
            held.append(cls)
    registry["last_updated"] = _now()
    return {"registry": registry, "promoted": promoted, "held": held}


def mean_champion_score(registry: Dict[str, Any]) -> float:
    champs = registry.get("champions", {})
    if not champs:
        return 0.0
    return round(sum(c["score"] for c in champs.values()) / len(champs), 3)


def save_registry(registry: Dict[str, Any], path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    return str(p)
