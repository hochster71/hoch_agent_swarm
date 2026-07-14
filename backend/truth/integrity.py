"""F-1: integrity must be COMPUTED, never asserted. F-4: ONE canonical factory source.

The wall previously displayed the hardcoded slogan:

    EVERY NODE OBSERVED · 0 FABRICATED

That is a claim, not a measurement -- printed in green regardless of what the runtime
actually contained. It is exactly the fake-green this system exists to prevent, sitting in
the header of the instrument meant to detect fake-green.

Integrity is now derived from the live nodes, or it reports UNKNOWN. It never asserts.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from backend.truth.task_status import TaskStatus, coerce_for_display

ROOT = Path(__file__).resolve().parents[2]
FACTORY_REGISTRY = ROOT / "coordination" / "council" / "factory_registry.json"

UNKNOWN = "UNKNOWN"


def compute_integrity(nodes: list[dict[str, Any]] | Any) -> dict[str, Any]:
    """Mechanically classify every node. If we cannot, say UNKNOWN -- never 'all observed'."""
    if not isinstance(nodes, list):
        return {"integrity_status": UNKNOWN,
                "reason": "node set unavailable; integrity cannot be computed",
                "truth_source": "none", "observed_at": _now()}

    # VACUOUS-GREEN GUARD. An EMPTY node set produced
    #     integrity_status: CLEAN  (observed 0/0, fabricated 0)
    # -- clean because nothing was examined. Zero nodes checked is not zero problems found;
    # it is NO EVIDENCE. "I looked at nothing and found nothing wrong" is the exact fake-green
    # this instrument exists to catch, and it was sitting inside the instrument.
    if len(nodes) == 0:
        return {"nodes_total": 0, "nodes_observed": 0, "nodes_asserted": 0,
                "nodes_unknown": 0, "fabricated_detected": 0,
                "integrity_status": UNKNOWN,
                "reason": ("no nodes were examined -- integrity is UNKNOWN, not CLEAN. "
                           "An empty check is not a passed check."),
                "truth_source": "runtime_verification", "observed_at": _now()}

    observed = asserted = unknown = fabricated = 0
    for n in nodes:
        if not isinstance(n, dict):
            unknown += 1
            continue
        # OBSERVED = the node carries runtime evidence we can point at.
        has_evidence = bool(n.get("evidence_path") or n.get("artifact_sha256")
                            or n.get("validator_verdict"))
        st, err = coerce_for_display(n.get("status"))
        if err:
            # an illegal status reaching the node set IS a fabrication signal
            fabricated += 1
            unknown += 1
            continue
        if st == TaskStatus.UNKNOWN.value:
            unknown += 1
        elif has_evidence:
            observed += 1
        else:
            asserted += 1          # a state with no evidence behind it

    return {
        "nodes_total": len(nodes),
        "nodes_observed": observed,
        "nodes_asserted": asserted,
        "nodes_unknown": unknown,
        "fabricated_detected": fabricated,
        "integrity_status": ("CLEAN" if fabricated == 0 and asserted == 0 and unknown == 0
                             else "DEGRADED" if fabricated == 0
                             else "FABRICATION_DETECTED"),
        "truth_source": "runtime_verification",
        "observed_at": _now(),
    }


def canonical_factories() -> dict[str, Any]:
    """F-4: ONE canonical identity source (factory_registry.json) + ONE derived runtime state.

    The wall must not blend scope champions, census records, static config, cached mission
    state and hardcoded frontend labels into a single number.
    """
    if not FACTORY_REGISTRY.exists():
        return {"truth_source": UNKNOWN, "reason": "factory_registry.json missing",
                "factories": UNKNOWN, "observed_at": _now()}
    try:
        reg = json.loads(FACTORY_REGISTRY.read_text()).get("factories", {})
    except Exception as e:
        return {"truth_source": UNKNOWN, "reason": f"registry unreadable: {e}",
                "factories": UNKNOWN, "observed_at": _now()}

    runtime: Any = UNKNOWN
    try:
        from backend.mission_control.persistent_scheduler import PersistentScheduler
        from backend.mission_control.scoped_states import ScopedStateEvaluator
        s = PersistentScheduler(evidence_dir=ROOT / "coordination" / "council")
        runtime = ScopedStateEvaluator(s.repo_root).evaluate_states(
            global_hold=False, blockers=s.load_blockers()).get("FACTORY_STATE", UNKNOWN)
    except Exception as e:
        runtime = UNKNOWN
        return {"truth_source": "factory_registry.json",
                "identity_count": len(reg),
                "runtime_state": UNKNOWN,
                "reason": f"runtime state underivable: {e}",
                "factories": {k: {"identity": v.get("name", UNKNOWN), "runtime": UNKNOWN}
                              for k, v in reg.items()},
                "observed_at": _now()}

    out = {}
    for fid, ident in reg.items():
        rt = runtime.get(fid) if isinstance(runtime, dict) else None
        out[fid] = {
            "identity": ident.get("name", UNKNOWN),
            "runtime_state": (rt or {}).get("state", UNKNOWN) if rt else UNKNOWN,
            "blocked_missions": (rt or {}).get("blocked_missions", []) if rt else UNKNOWN,
        }
    return {"truth_source": "factory_registry.json + derived FACTORY_STATE",
            "identity_count": len(reg), "factories": out, "observed_at": _now()}


def concurrency_facts(sched) -> dict[str, Any]:
    """Capacity and utilisation are DIFFERENT facts. Do not show 'effective 4' when nothing
    is running."""
    rep = sched.concurrency_report()
    lease_dir = ROOT / "coordination" / "leases"
    active = len(list(lease_dir.glob("*.lock"))) if lease_dir.exists() else 0
    return {
        "configured_capacity": rep.get("configured_limit"),
        "currently_active": active,
        "observed_peak": rep.get("observed_peak_concurrency"),
        "lease_mode": "PER_TASK" if rep.get("concurrency_mode") == "PER_TASK_LEASE" else UNKNOWN,
        "status": rep.get("status"),
        "truth_source": "OBSERVED_RUNTIME",
    }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
