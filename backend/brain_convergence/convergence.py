"""M0 BRAIN Convergence — convergence tracker.

Records the mean champion score per generation and decides when the loop has CONVERGED for now:
when the marginal gain stays below `epsilon` for `patience` consecutive generations. Convergence
frees compute to focus on harder task classes; it is not "done forever" — a new candidate that
beats a plateaued champion re-opens the class.
"""
import json
import datetime
from pathlib import Path
from typing import Dict, Any


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def update(status_path: str, generation: int, mean_score: float,
           epsilon: float = 0.5, patience: int = 3) -> Dict[str, Any]:
    p = Path(status_path)
    # Defensive: a pre-existing/legacy status file may lack our "history" key.
    hist = []
    if p.exists():
        try:
            hist = json.loads(p.read_text(encoding="utf-8")).get("history", [])
        except Exception:
            hist = []
    prev = hist[-1]["mean_score"] if hist else None
    gain = None if prev is None else round(mean_score - prev, 3)
    hist.append({"generation": generation, "mean_score": mean_score, "gain": gain, "at": _now()})

    # plateau: last `patience` gains all below epsilon (in absolute value)
    recent_gains = [h["gain"] for h in hist[-patience:] if h["gain"] is not None]
    converged = len(recent_gains) >= patience and all(abs(g) < epsilon for g in recent_gains)

    status = {
        "schema": "brain-convergence-status-m0",
        "generation": generation,
        "mean_score": mean_score,
        "last_gain": gain,
        "epsilon": epsilon,
        "patience": patience,
        "converged": converged,
        "state": "CONVERGED" if converged else "IMPROVING" if (gain is None or gain > 0) else "PLATEAUING",
        "history": hist,
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status
