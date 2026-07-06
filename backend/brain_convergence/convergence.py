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
           epsilon: float = 0.5, patience: int = 3,
           improver_online: bool = True) -> Dict[str, Any]:
    """Record a generation and decide convergence — HONESTLY.

    A no-gain generation only counts toward the convergence streak if the improver was actually
    ONLINE (a live local model able to GENERATE). Flat-because-the-model-was-offline is NOT
    evidence the brain can't get smarter — counting it would be fake-green convergence. Such
    generations are recorded with improver_online=False and state=STALLED_NO_IMPROVER, and are
    excluded from the patience streak so the loop can never declare CONVERGED while blind.
    """
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
    hist.append({"generation": generation, "mean_score": mean_score, "gain": gain,
                 "improver_online": bool(improver_online), "at": _now()})

    if not improver_online:
        # Blind generation: cannot support a convergence claim. Never converged here.
        converged, state = False, "STALLED_NO_IMPROVER"
    else:
        # plateau streak counts ONLY generations where the improver was online.
        online_gains = [h["gain"] for h in hist[-patience:]
                        if h["gain"] is not None and h.get("improver_online", True)]
        converged = len(online_gains) >= patience and all(abs(g) < epsilon for g in online_gains)
        state = ("CONVERGED" if converged
                 else "IMPROVING" if (gain is None or gain > 0)
                 else "PLATEAUING")

    status = {
        "schema": "brain-convergence-status-m0",
        "generation": generation,
        "mean_score": mean_score,
        "last_gain": gain,
        "epsilon": epsilon,
        "patience": patience,
        "improver_online": bool(improver_online),
        "converged": converged,
        "state": state,
        "history": hist,
    }
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status
