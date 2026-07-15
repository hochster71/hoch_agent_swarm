"""Semantic Jacobian Lens — J-Space Executive Intelligence (P1 scaffold).

Measures how sensitive the promotion decision is to each finding: the discrete gradient
∂(P withhold promotion)/∂(finding). Read-only, pure, no model — operates on assessment records.

  drivers   : the findings whose flip most moves the decision (ranked). Turns thousands of open
              findings into the handful actually holding the gate closed.
  fragility : how close the decision sits to flipping (max single-finding sensitivity). A verdict one
              perturbation would overturn is fragile and must not auto-promote — 'No Fake Green' as calculus.

This is the scaffold (semantic mode). The precise fragility metric and the neural mode (Jacobian over
model activations) are the next steps in the HELM x J-Space roadmap; see docs/HELM_JSPACE_ARCHITECTURE.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

# worst-wins severity; fail-closed (a missing/unknown verdict withholds)
_RANK = {"CONTRADICTED": 3, "BLOCKED": 2, "CONFIRMED_LIVE": 1}
_WITHHOLD = {"CONFIRMED_LIVE": 0.0, "BLOCKED": 0.6, "CONTRADICTED": 1.0, "UNKNOWN": 1.0}
_HEALTHY = "CONFIRMED_LIVE"
FRAGILITY_CEILING = 0.35   # decisions at/above this may not auto-promote (placeholder; founder-tunable)


def consensus_of(rows: List[Dict[str, Any]]) -> str:
    """Worst-wins consensus over assessments. Empty -> UNKNOWN (fail-closed)."""
    worst = 0
    for r in rows:
        worst = max(worst, _RANK.get(r.get("assessment"), 0))
    return {3: "CONTRADICTED", 2: "BLOCKED", 1: "CONFIRMED_LIVE", 0: "UNKNOWN"}[worst]


def p_withhold(verdict: str) -> float:
    """P(withhold promotion) for a consensus verdict. Unknown withholds."""
    return _WITHHOLD.get(verdict, 1.0)


class SemanticJacobianLens:
    """Discrete sensitivity of the promotion decision to each finding."""

    def __init__(self, rows: List[Dict[str, Any]]):
        self.rows = list(rows or [])

    def compute(self) -> Dict[str, Any]:
        cons = consensus_of(self.rows)
        base = p_withhold(cons)
        drivers = []
        for i, r in enumerate(self.rows):
            if r.get("assessment") == _HEALTHY:
                continue                      # a healthy finding is never a driver
            # perturb THIS finding to healthy, recompute the decision
            flipped = [dict(x) for x in self.rows]
            flipped[i]["assessment"] = _HEALTHY
            new_p = p_withhold(consensus_of(flipped))
            sensitivity = round(base - new_p, 4)     # how much clearing this finding lowers withhold
            drivers.append({"subject": r.get("subject"), "observer": r.get("observer"),
                            "assessment": r.get("assessment"), "sensitivity": sensitivity})
        drivers.sort(key=lambda d: -d["sensitivity"])
        fragility = max((d["sensitivity"] for d in drivers), default=0.0)
        promotable = (cons == _HEALTHY) and (fragility < FRAGILITY_CEILING)
        return {
            "consensus": cons,
            "p_withhold": base,
            "fragility": round(fragility, 4),
            "fragility_ceiling": FRAGILITY_CEILING,
            "promotable": bool(promotable),
            "drivers": drivers,
            "finding_count": sum(1 for r in self.rows if r.get("assessment") != _HEALTHY),
            "note": ("decision is robust" if fragility < FRAGILITY_CEILING
                     else f"decision is fragile — one finding flip moves it (sensitivity {fragility})"),
        }

    # --------------------------------------------------------------- ledger loader
    @classmethod
    def from_ledger(cls, assessments_path: Path) -> "SemanticJacobianLens":
        """Build from the append-only assessment ledger: latest verdict per (observer, subject)."""
        p = Path(assessments_path)
        latest: Dict[tuple, Dict[str, Any]] = {}
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                k = (r.get("observer"), r.get("subject"))
                if k[0] and k[1]:
                    latest[k] = {"observer": r.get("observer"), "subject": r.get("subject"),
                                 "assessment": r.get("assessment"),
                                 "recommended_action": r.get("recommended_action"),
                                 "detail": (r.get("detail") or "")[:160]}
        return cls(list(latest.values()))
