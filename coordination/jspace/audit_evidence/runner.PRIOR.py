"""HJOS cycle runner — observe → ledger → health → (gated) quarantine.

Default path is read-only. Auto-quarantine only after burn-in and only for
charter-permitted classes (+ optional expired-orphan lease hygiene).
Never promotes. Never executes HELM tasks. Never rewrites soak seals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from backend.jspace.burn_in import BurnInTracker
from backend.jspace.charter import HJOS_CHARTER
from backend.jspace.ledger import JSpaceLedger
from backend.jspace.observers import SPECIALISTS, MetaObserver
from backend.jspace.quarantine import (
    execute_quarantine_if_allowed,
    quarantine_expired_orphan_locks,
)
from backend.jspace.schema import JSpaceEvent, new_id
from backend.jspace.sources import collect_wall_inputs


def run_hjos_cycle(
    *,
    repo_root: Optional[Path] = None,
    ledger_root: Optional[Path] = None,
    snapshot: Optional[Dict[str, Any]] = None,
    enable_orphan_hygiene: bool = True,
) -> Dict[str, Any]:
    """Run one full HJOS observation cycle."""
    charter = HJOS_CHARTER
    cycle_id = new_id("JCYC")
    ledger = JSpaceLedger(ledger_root)
    burn = BurnInTracker(ledger.root)
    exception: Optional[str] = None
    quarantine_results: list = []

    try:
        snap = snapshot if snapshot is not None else collect_wall_inputs(repo_root)

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
                # Always record request
                if al.recommended_action.startswith("QUARANTINE_REQUEST") or al.severity == "CRITICAL":
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

        burn_state = burn.record_cycle(
            cycle_id=cycle_id,
            overall=health.overall.value,
            state_mutated=False,
            exception=None,
        )
        auto_q = bool(burn_state.get("automatic_quarantine_enabled"))

        # Gated auto-quarantine for permitted security classes
        if auto_q:
            for res in specialist_results:
                for al in res.alerts:
                    if al.severity not in ("HIGH", "CRITICAL") and not al.recommended_action.startswith("QUARANTINE"):
                        continue
                    reason = al.recommended_action
                    if al.subject == "secret_exposure_scan":
                        reason = "secret_exposure"
                    qr = execute_quarantine_if_allowed(
                        enabled=True,
                        reason=reason,
                        subject=al.subject,
                        evidence=list(al.evidence),
                        cycle_id=cycle_id,
                        observer=al.observer,
                        ledger_append=ledger.request_quarantine,
                        repo_root=repo_root,
                    )
                    quarantine_results.append(qr)

        # Orphan expired lease hygiene (post burn-in only; never live instance)
        if enable_orphan_hygiene and auto_q:
            ptr = (snap.get("runtime") or {}).get("pointer") or {}
            hy = quarantine_expired_orphan_locks(
                enabled=True,
                current_instance_id=ptr.get("scheduler_instance_id"),
                ledger_append=ledger.request_quarantine,
                repo_root=repo_root,
                cycle_id=cycle_id,
            )
            quarantine_results.append(hy)

        ledger.append_event(JSpaceEvent(
            event_type="HJOS_CYCLE_END",
            source="jspace_runner",
            subject=cycle_id,
            payload={
                "overall": health.overall.value,
                "open_alerts": health.open_alerts,
                "recommended_action": health.recommended_action,
                "promotion_authority": "NONE",
                "burn_in_complete": burn_state.get("burn_in_complete"),
                "automatic_quarantine_enabled": auto_q,
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
            "burn_in": {
                "complete": burn_state.get("burn_in_complete"),
                "clean_cycles": burn_state.get("clean_cycles"),
                "completed_cycles": burn_state.get("completed_cycles"),
                "automatic_quarantine_enabled": auto_q,
            },
            "quarantine_results": quarantine_results,
        }
    except Exception as e:
        exception = f"{type(e).__name__}: {e}"
        burn.record_cycle(
            cycle_id=cycle_id,
            overall="UNKNOWN",
            state_mutated=False,
            exception=exception,
        )
        raise
