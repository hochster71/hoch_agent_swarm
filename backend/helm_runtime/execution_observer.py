#!/usr/bin/env python3
"""execution_observer.py — CYB-002. Observed execution, not inferred reachability.

WHY (founder, 2026-07-21). CYB-001 concluded that the mcp/chromadb CVEs are unreachable.
That conclusion came from AST import-site analysis — a STATIC property. The honest bound
recorded alongside it:

    "'Not reachable' is an inference from import structure, not a proven property."

This module moves one rung up the evidence ladder:

    design artifact          "the dependency is declared"
    static analysis          "no import site reaches it"          <- CYB-001 stopped here
    OBSERVED EXECUTION       "it was not loaded during mission X" <- this module
    adversarial test         "an attempt to reach it failed"      <- still UNKNOWN

WHAT IT DOES NOT DO. Observing that a module was not imported during ONE mission is not
proof it can never be imported. Snapshots certify state; histories certify behaviour. A
single observation window produces `OBSERVED_ABSENT_IN_THIS_RUN` — deliberately not
`ABSENT`. Widening that claim requires more windows, and the artifact records how many.

METHOD. sys.modules is diffed around the observed callable, so what is recorded is what
the interpreter actually loaded — not what a scanner believed would load. No import hooks
are installed and no module is patched: the observer must not change the execution it is
observing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[2]

# Packages whose LOADING is security-relevant. Presence here does not mean "banned" —
# it means "if this loads, the evidence must say so out loud".
WATCHED: Dict[str, str] = {
    "mcp": "3 HIGH CVEs in <1.28.1 (transports); local stub shadows resolution — CYB-001",
    "chromadb": "CRITICAL pre-auth code injection, NO patch available",
    "json_repair": "HIGH unbounded CPU DoS via circular $ref",
    "crewai": "dormant lane — loading it means the legacy factory woke up",
    "pillow": "remediated at 12.3.0; recorded to confirm the fixed version is the one loaded",
    "PIL": "pillow's import name",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(o: Any) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, default=str).encode()).hexdigest()


def _version_of(mod_name: str) -> Optional[str]:
    """Report the version of what ACTUALLY loaded, from the live module object where
    possible. CYB-001's whole lesson: the lockfile's version is not necessarily the
    executing one."""
    m = sys.modules.get(mod_name)
    v = getattr(m, "__version__", None) if m else None
    if v:
        return str(v)
    try:
        import importlib.metadata as md
        return md.version(mod_name)
    except Exception:
        return None


def _origin_of(mod_name: str) -> Optional[str]:
    """WHERE it loaded from. A watched package resolving to a local stub directory rather
    than site-packages is exactly the CYB-001 shadowing hazard, visible only at runtime."""
    m = sys.modules.get(mod_name)
    f = getattr(m, "__file__", None) if m else None
    return str(f) if f else None


@dataclass
class ExecutionObservation:
    """One observation window. Immutable evidence (ARCH-002)."""

    label: str
    started_at: str
    finished_at: str = ""
    modules_loaded_during: List[str] = field(default_factory=list)
    watched_loaded: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    watched_not_loaded: List[str] = field(default_factory=list)
    already_loaded_before: List[str] = field(default_factory=list)
    outcome: str = "UNKNOWN"
    error: Optional[str] = None

    def to_evidence(self) -> Dict[str, Any]:
        ev = {
            "schema_version": "HELM_EXECUTION_OBSERVATION_v1",
            "evidence_class": "OBSERVED_EXECUTION",
            "label": self.label,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "outcome": self.outcome,
            "error": self.error,
            "modules_loaded_during_window": len(self.modules_loaded_during),
            "watched_LOADED": self.watched_loaded,
            "watched_NOT_LOADED_in_this_run": self.watched_not_loaded,
            "watched_already_resident_before_window": self.already_loaded_before,
            "claim_this_supports": (
                "OBSERVED_ABSENT_IN_THIS_RUN for the not-loaded set — NOT 'unreachable'. "
                "One window is one observation. Widening to a general claim requires more "
                "windows and is not licensed by this artifact."),
            "observation_windows": 1,
            "method": "sys.modules diff around the observed callable; no import hooks, no patching",
            "generated_by": "backend.helm_runtime.execution_observer.observe",
            "generated_at": _now(),
        }
        ev["content_hash"] = _sha({k: v for k, v in ev.items() if k != "content_hash"})
        return ev


def observe(fn: Callable[[], Any], *, label: str) -> tuple[Any, ExecutionObservation]:
    """Run `fn` and record what the interpreter actually loaded while it ran.

    Fails OPEN for the observation and CLOSED for the claim: if `fn` raises, the error is
    recorded and the observation still emits. An unobserved failure would leave no trace,
    and a run that left no trace is unattributable work.
    """
    before: Set[str] = set(sys.modules)
    obs = ExecutionObservation(
        label=label,
        started_at=_now(),
        already_loaded_before=sorted(w for w in WATCHED if w in before),
    )
    result = None
    try:
        result = fn()
        obs.outcome = "COMPLETED"
    except Exception as e:                    # noqa: BLE001 - deliberate: observe failures too
        obs.outcome = "RAISED"
        obs.error = f"{type(e).__name__}: {e}"[:300]
    finally:
        after: Set[str] = set(sys.modules)
        newly = sorted(after - before)
        obs.modules_loaded_during = newly
        top_level_newly = {m.split(".")[0] for m in newly}
        for w, why in WATCHED.items():
            if w in top_level_newly:
                obs.watched_loaded[w] = {
                    "why_watched": why,
                    "version_actually_loaded": _version_of(w),
                    "loaded_from": _origin_of(w),
                }
            elif w not in before:
                obs.watched_not_loaded.append(w)
        obs.finished_at = _now()
    return result, obs


def write_evidence(obs: ExecutionObservation, path: Optional[Path] = None) -> Path:
    p = path or (ROOT / "coordination" / "evidence" / "execution_observations" /
                 f"obs_{obs.label}_{obs.started_at.replace(':', '').replace('-', '')}.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obs.to_evidence(), indent=2))
    return p


if __name__ == "__main__":  # pragma: no cover
    from backend.helm_runtime.hrf_runtime import run as hrf_run

    def _mission():
        def _stub_dispatch(lane, prompt, **kw):
            return {"ok": True, "text": f"[observer probe {lane}]", "cost": 0.0, "model": "probe"}
        return hrf_run({"query": "execution observation probe"}, dispatch=_stub_dispatch)

    res, obs = observe(_mission, label="hrf_mission")
    out = write_evidence(obs)
    print(json.dumps(obs.to_evidence(), indent=2))
    print(f"\nevidence: {out.relative_to(ROOT)}")


# --- accumulation (founder refinement 2026-07-21) ---------------------------------
# A single window supports OBSERVED_ABSENT_IN_THIS_RUN. Windows ACCUMULATE into the
# strictly stronger — and still honest — claim:
#     "not observed across N independent executions"
# never
#     "impossible".
# Runtime instrumentation is bounded by execution coverage: it can establish what
# occurred, never that an event cannot occur.

OBS_DIR = ROOT / "coordination" / "evidence" / "execution_observations"


def accumulate(obs_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Roll every recorded window into a per-package tally. Reads observations; it does
    not rewrite them (ARCH-002: observations accumulate, they are not corrected)."""
    d = obs_dir or OBS_DIR
    windows: List[Dict[str, Any]] = []
    for f in sorted(d.glob("obs_*.json")) if d.exists() else []:
        try:
            windows.append(json.loads(f.read_text()))
        except Exception:
            continue

    tally: Dict[str, Dict[str, Any]] = {
        w: {"loaded_in": 0, "not_observed_in": 0, "versions_seen": [], "origins_seen": []}
        for w in WATCHED
    }
    for win in windows:
        for pkg, det in (win.get("watched_LOADED") or {}).items():
            t = tally.setdefault(pkg, {"loaded_in": 0, "not_observed_in": 0,
                                       "versions_seen": [], "origins_seen": []})
            t["loaded_in"] += 1
            for k, dst in (("version_actually_loaded", "versions_seen"),
                           ("loaded_from", "origins_seen")):
                v = det.get(k)
                if v and v not in t[dst]:
                    t[dst].append(v)
        for pkg in win.get("watched_NOT_LOADED_in_this_run") or []:
            tally.setdefault(pkg, {"loaded_in": 0, "not_observed_in": 0,
                                   "versions_seen": [], "origins_seen": []})
            tally[pkg]["not_observed_in"] += 1

    n = len(windows)
    return {
        "schema_version": "HELM_EXECUTION_ACCUMULATION_v1",
        "evidence_class": "OBSERVED_EXECUTION_HISTORY",
        "observation_windows": n,
        "window_labels": [w.get("label") for w in windows],
        "per_package": tally,
        "claim_supported": (
            f"not observed across {n} independent execution window(s)" if n else
            "NO WINDOWS RECORDED — no runtime claim is supported"),
        "claim_NOT_supported": "impossible / unreachable / cannot occur",
        "coverage_caveat": (
            "runtime observation is bounded by execution coverage. N windows covering one "
            "code path say nothing about paths never exercised. Window COUNT is not window "
            "DIVERSITY, and this artifact reports only the count."),
        "generated_at": _now(),
    }
