"""M0 BRAIN Convergence — Held-out splits.

Deterministic train / dev / held-out partition per task_class, with a provenance manifest of
per-item hashes. The held-out set is SACRED: candidates are scored on it but never generated or
tuned from it. assert_disjoint() proves no leakage — the anti-Goodhart foundation of the loop.

Deterministic given (gene_ids, seed): the split is a stable hash ordering, so re-runs reproduce
the exact partition and any leakage is detectable by comparing provenance manifests.
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def _rank(gid: str, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{gid}".encode()).hexdigest()


def make_splits(by_class: Dict[str, List[str]], ratios: Tuple[float, float, float] = (0.70, 0.15, 0.15),
                seed: str = "hoch-m0-v1") -> Dict[str, Any]:
    assert abs(sum(ratios) - 1.0) < 1e-9, "ratios must sum to 1.0"
    train, dev, heldout = [], [], []
    per_class = {}
    for cls, gids in by_class.items():
        ordered = sorted(gids, key=lambda g: _rank(g, seed))
        n = len(ordered)
        n_tr = int(round(n * ratios[0]))
        n_dev = int(round(n * ratios[1]))
        c_tr = ordered[:n_tr]
        c_dev = ordered[n_tr:n_tr + n_dev]
        c_ho = ordered[n_tr + n_dev:]
        train += c_tr; dev += c_dev; heldout += c_ho
        per_class[cls] = {"train": len(c_tr), "dev": len(c_dev), "heldout": len(c_ho)}
    return {
        "seed": seed, "ratios": list(ratios),
        "train": train, "dev": dev, "heldout": heldout,
        "per_class": per_class,
        "provenance_hash": hashlib.sha256(json.dumps(
            {"train": sorted(train), "dev": sorted(dev), "heldout": sorted(heldout)},
            sort_keys=True).encode()).hexdigest(),
    }


def assert_disjoint(splits: Dict[str, Any]) -> Dict[str, Any]:
    """Raise if any gene appears in more than one split (leakage). Returns overlap report."""
    tr, dv, ho = set(splits["train"]), set(splits["dev"]), set(splits["heldout"])
    overlaps = {
        "train∩dev": sorted(tr & dv),
        "train∩heldout": sorted(tr & ho),
        "dev∩heldout": sorted(dv & ho),
    }
    leaks = {k: v for k, v in overlaps.items() if v}
    if leaks:
        raise AssertionError(f"HELD-OUT LEAKAGE detected: {leaks}")
    return {"disjoint": True, "counts": {"train": len(tr), "dev": len(dv), "heldout": len(ho)}}


def write_splits(splits: Dict[str, Any], out_path: str) -> str:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(splits, indent=2), encoding="utf-8")
    return str(p)
