"""HJOS cycle runner — read-only observe → ledger → health.

Does not execute tasks, mutate HELM state, or promote anything.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from backend.jspace.charter import HJOS_CHARTER
from backend.jspace.ledger import JSpaceLedger
from backend.jspace.observers import SPECIALISTS, MetaObserver
from backend.jspace.schema import JSpaceEvent, new_id
from backend.jspace.sources import collect_wall_inputs


def run_hjos_cycle(
    *,
    repo_root: Optional[Path] = None,
    ledger_root: Optional[Path] = None,
    snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run one full HJOS observation cycle.

    Returns a machine-readable summary suitable for CLI / API / dashboard.
    """
    charter = HJOS_CHARTER
    cycle_id = new_id("JCYC")
    ledger = JSpaceLedger(ledger_root)

    snap = snapshot if snapshot is not None else collect_wall_inputs(repo_root)

    # Bus event: cycle start (evidence only)
    ledger.append_event(JSpaceEvent(
        event_type="HJOS_CYCLE_START",
        source="jspace_runner",
        subject=cycle_id,
        payload={
            "charter": charter.short_name,
            "mode": charter.default_mode.value,
            "promotion_authority": charter.promotion_authority,
            "observers": list(charter.observers),
        },
        event_id=f"JEVT-{cycle_id[-6:]}-START",
    ))

    specialist_results = []
    for cls in SPECIALISTS:
        obs = cls(cycle_id=cycle_id)
        res = obs.observe(snap)
        for a in res.assessments:
            a.cycle_id = cycle_id
            charter.assert_read_only(state_mutated=a.state_mutated)
            ledger.append_assessment(a)
        for al in res.alerts:
            al.cycle_id = cycle_id
            ledger.append_alert(al)
            # Quarantine REQUEST only for permitted classes — never auto-execute
            if (
                al.recommended_action.startswith("QUARANTINE_REQUEST")
                and not charter.automatic_quarantine_enabled
            ):
                ledger.request_quarantine({
                    "cycle_id": cycle_id,
                    "alert_id": al.alert_id,
                    "subject": al.subject,
                    "reason": al.recommended_action,
                    "observer": al.observer,
                    "observed_at": al.observed_at,
                })
        specialist_results.append(res)

    meta = MetaObserver(cycle_id=cycle_id)
    health, meta_res = meta.reconcile(specialist_results)
    for a in meta_res.assessments:
        ledger.append_assessment(a)
    health_doc = ledger.write_health(health)

    ledger.append_event(JSpaceEvent(
        event_type="HJOS_CYCLE_END",
        source="jspace_runner",
        subject=cycle_id,
        payload={
            "overall": health.overall.value,
            "open_alerts": health.open_alerts,
            "recommended_action": health.recommended_action,
            "promotion_authority": "NONE",
        },
        event_id=f"JEVT-{cycle_id[-6:]}-END",
    ))

    return {
        "schema": "HJOS_CYCLE_RESULT_v1",
        "cycle_id": cycle_id,
        "charter": charter.short_name,
        "mode": charter.default_mode.value,
        "promotion_authority": "NONE",
        "state_mutated": False,
        "overall": health.overall.value,
        "open_alerts": health.open_alerts,
        "recommended_action": health.recommended_action,
        "observer_counts": health.observer_counts,
        "worst_findings": health.worst_findings,
        "health_digest": health_doc.get("health_digest"),
        "ledger_root": str(ledger.root),
        "observed_at": health.observed_at,
    }
