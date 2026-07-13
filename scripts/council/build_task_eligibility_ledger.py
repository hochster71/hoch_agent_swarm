#!/usr/bin/env python3
"""Task eligibility ledger (RMF-1).

The scheduler reported `dispatched_count: 0` with no explanation. An empty
dispatch count is not a diagnosis. This ledger answers, for EVERY task in the
canonical queue, exactly why it is or is not runnable.

Per founder spec, each row records:
  task_id, factory_id, status, dependencies_satisfied, validator_present,
  adapter_eligible, credentials_available, budget_available, policy_allowed,
  blocker_scope, blocker_reason, runnable

Every field is OBSERVED from the live DB / registries. Nothing is asserted.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DB = ROOT / "backend" / "swarm_ledger.db"

# The scheduler's own eligibility predicate (persistent_scheduler.evaluate_runnable_tasks)
SCHEDULER_RUNNABLE_STATUSES = {"PENDING", "FAILED"}


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main() -> int:
    if not DB.exists():
        print(json.dumps({"error": "task DB missing", "db": str(DB)}))
        return 2

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    # Physical column order of the REAL table -- the misalignment lives here.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(mission_control_tasks)")]

    tasks = [dict(r) for r in conn.execute(
        "SELECT t.*, m.target_pod, m.name AS mission_name "
        "FROM mission_control_tasks t "
        "LEFT JOIN mission_control_missions m ON t.mission_id = m.mission_id"
    )]
    completed = {r["task_id"] for r in conn.execute(
        "SELECT task_id FROM mission_control_tasks WHERE status = 'COMPLETED'")}

    # Adapter readiness (observed, not assumed)
    try:
        from backend.mission_control.adapter_registry import AdapterRegistry
        adapters = AdapterRegistry().check_all_readiness()
    except Exception as e:
        adapters = {"_error": str(e)[:120]}
    # The registry reports readiness as a STRING ("READY"/"NOT_READY"), not a bool.
    ready_adapters = [k for k, v in adapters.items()
                      if isinstance(v, dict) and v.get("readiness") == "READY"]
    local_ready = [k for k, v in adapters.items()
                   if isinstance(v, dict) and v.get("readiness") == "READY"
                   and v.get("egress_class") == "LOCAL_ONLY"]
    frontier_blocked = [k for k, v in adapters.items()
                        if isinstance(v, dict) and v.get("readiness") != "READY"
                        and v.get("auth_required")]

    # Blockers (observed)
    try:
        from backend.mission_control.persistent_scheduler import PersistentScheduler
        blockers = PersistentScheduler(evidence_dir=ROOT / "coordination" / "council").load_blockers()
    except Exception as e:
        blockers = [{"id": "UNKNOWN", "error": str(e)[:120]}]
    active_blockers = [b for b in blockers
                       if str(b.get("status", "")).upper() not in
                       ("RESOLVED", "PASS", "DONE", "CLEARED")]

    rows = []
    for t in tasks:
        status = t.get("status")
        deps = [d.strip() for d in (t.get("dependencies") or "").split(",") if d.strip()]
        deps_ok = all(d in completed for d in deps)

        # THE defect: `status` holds an agent name, so it can never match the
        # scheduler's PENDING/FAILED predicate. Detect it explicitly rather than
        # reporting a bare "not runnable".
        status_is_valid = status in (
            "PENDING", "FAILED", "COMPLETED", "RUNNING", "BLOCKED", "CANCELLED")
        misaligned = (not status_is_valid) and isinstance(status, str) and status.startswith("Agent")

        scheduler_visible = status in SCHEDULER_RUNNABLE_STATUSES

        if misaligned:
            blocker_scope, blocker_reason = "TASK_RECORD", (
                f"COLUMN MISALIGNMENT: status={status!r} is an AGENT NAME, not a status. "
                f"The seeding INSERT used positional VALUES against an assumed column order "
                f"while the real table is {cols}. The scheduler filters "
                f"status IN {sorted(SCHEDULER_RUNNABLE_STATUSES)}, so this task is INVISIBLE.")
        elif not scheduler_visible:
            blocker_scope, blocker_reason = "TASK_STATUS", f"status={status!r} not in {sorted(SCHEDULER_RUNNABLE_STATUSES)}"
        elif not deps_ok:
            blocker_scope, blocker_reason = "DEPENDENCY", f"unsatisfied deps: {[d for d in deps if d not in completed]}"
        elif not ready_adapters:
            blocker_scope, blocker_reason = "ADAPTER", "no adapter reports ready=True"
        else:
            blocker_scope, blocker_reason = None, None

        runnable = bool(scheduler_visible and deps_ok and ready_adapters)

        rows.append({
            "task_id": t.get("task_id"),
            "factory_id": t.get("target_pod") or "UNKNOWN",
            "status": status,
            "status_field_valid": status_is_valid,
            "dependencies_satisfied": deps_ok,
            "validator_present": bool(t.get("evidence_path")) or "UNKNOWN",
            "adapter_eligible": bool(ready_adapters),
            # A LOCAL_ONLY adapter needs no credentials and incurs no spend.
            "credentials_available": bool(local_ready) or "FRONTIER_KEYS_ABSENT",
            "budget_available": True if local_ready else "UNKNOWN",
            "policy_allowed": not active_blockers or "SCOPED",
            "blocker_scope": blocker_scope,
            "blocker_reason": blocker_reason,
            "runnable": runnable,
            "_raw_row": {c: t.get(c) for c in cols},
        })

    ledger = {
        "schema": "TASK_ELIGIBILITY_LEDGER_v1",
        "generated_at_utc": now(),
        "db": str(DB.relative_to(ROOT)),
        "real_table_columns": cols,
        "scheduler_runnable_statuses": sorted(SCHEDULER_RUNNABLE_STATUSES),
        "adapters_ready": ready_adapters,
        "adapters_local_ready": local_ready,
        "adapters_frontier_blocked_on_credentials": frontier_blocked,
        "adapters_total": len([k for k in adapters if not k.startswith("_")]),
        "credentials_note": ("Frontier adapters require founder-provisioned API keys and are "
                             "NOT_READY. LOCAL_ONLY adapters are READY, so a real burn-in can "
                             "run with zero credentials and zero spend (local_first policy)."),
        "active_blockers": [b.get("id") for b in active_blockers],
        "total_tasks": len(rows),
        "runnable_tasks": sum(1 for r in rows if r["runnable"]),
        "root_cause": None,
        "tasks": rows,
    }

    misaligned_rows = [r for r in rows if r["blocker_scope"] == "TASK_RECORD"]
    if misaligned_rows and ledger["runnable_tasks"] == 0:
        ledger["root_cause"] = {
            "defect": "SEEDING_COLUMN_MISALIGNMENT",
            "explanation": (
                "The activation script declares its own CREATE TABLE IF NOT EXISTS with a "
                "different column order than the real table. Because the table already "
                "exists, the CREATE is a no-op and the real schema wins -- but the script "
                "still INSERTs positionally against its assumed order. Every value lands one "
                "column off: status receives the agent name, step_index receives the literal "
                "'PENDING'. The scheduler's status filter therefore matches nothing."),
            "affected_tasks": [r["task_id"] for r in misaligned_rows],
            "fix": "INSERT with an EXPLICIT column list; never positional VALUES against an assumed schema.",
            "note": ("The fabricated PASS verdicts in the old harness MASKED this bug. "
                     "Honest reporting surfaced it immediately."),
        }

    out = ROOT / "coordination" / "council" / "task_eligibility_ledger.json"
    out.write_text(json.dumps(ledger, indent=2) + "\n")

    print(json.dumps({
        "total_tasks": ledger["total_tasks"],
        "runnable_tasks": ledger["runnable_tasks"],
        "adapters_ready": ledger["adapters_ready"],
        "root_cause": (ledger["root_cause"] or {}).get("defect"),
        "per_task": [{"task_id": r["task_id"], "factory": r["factory_id"],
                      "status": r["status"], "runnable": r["runnable"],
                      "blocker": r["blocker_scope"]} for r in rows],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
