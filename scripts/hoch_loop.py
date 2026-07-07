#!/usr/bin/env python3
"""HOCH LOOP — the single autonomous build driver.

Pulls the next task, runs the REAL engine (backend/agent_executor), records the outcome as
EXPERIENCE (a combat record → the training/telemetry data the factories never had), then
repeats until the queue drains. Founder-gated tasks are STAGED, never attempted. Runs unattended
in SAFE mode by default (docs/analysis/verification); code work waits for the capable model.

This is the loop the plan always described and never had an engine for. It is driven by the
orchestrator, not hand-cranked by the founder.
"""
from __future__ import annotations
import datetime
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

QUEUE = ROOT / "has_live_project_tracker/data/hoch_loop_queue.json"
STATE = ROOT / "has_live_project_tracker/data/hoch_loop_state.json"
EXPERIENCE = ROOT / "data/prompt_brain/outcome_feedback_ledger.jsonl"  # real combat records

FOUNDER_GATED = {"blocked_release", "blocked_monetization", "blocked_secret_handling",
                 "blocked_external_outreach", "blocked_investor_engagement"}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _load(p, d):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def _save(p, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, indent=2))


def _record_experience(task: dict, result: dict) -> None:
    EXPERIENCE.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": _now(), "kind": "combat_record", "engine": "agent_executor.v2",
        "task_id": task.get("task_id"), "task_class": task.get("task_class"),
        "task_name": task.get("task_name"), "status": result["status"],
        "tier": result.get("tier"), "task_cost_usd": result.get("task_cost_usd", 0.0),
        "month_spend_usd": result.get("month_spend_usd", 0.0),
        "month_cap_usd": result.get("month_cap_usd"),
        "summary": result["summary"][:400], "artifacts": result["artifacts"],
        "evidence": result["evidence_path"],
    }
    with open(EXPERIENCE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def main() -> None:
    from backend.agent_executor import execute_task
    max_tasks = int(os.environ.get("HOCH_LOOP_MAX", "0"))   # 0 = run until queue drains
    sleep_s = int(os.environ.get("HOCH_LOOP_SLEEP", "2"))
    done = 0
    print(f"[{_now()}] HOCH LOOP started. queue={QUEUE.name} max={max_tasks or 'drain'}")

    while True:
        q = _load(QUEUE, [])
        pending = [t for t in q if t.get("status") == "PENDING"]
        if not pending:
            print(f"[{_now()}] queue drained — {done} tasks completed. Loop idle.")
            _save(STATE, {"ts": _now(), "state": "IDLE", "completed": done})
            break

        task = pending[0]
        # Never attempt founder-gated work — stage it for the human.
        if task.get("founder_gated") or task.get("policy_category") in FOUNDER_GATED:
            task["status"] = "STAGED_FOR_FOUNDER"
            _save(QUEUE, q)
            print(f"[{_now()}] staged founder-gated → {task.get('task_id')}")
            continue

        print(f"[{_now()}] EXEC {task.get('task_id')} — {str(task.get('task_name'))[:64]}")
        task["status"] = "RUNNING"
        _save(QUEUE, q)
        _save(STATE, {"ts": _now(), "state": "RUNNING", "completed": done, "current": task.get("task_id")})
        try:
            res = execute_task(task)
            task["status"] = "completed" if res["status"] == "SUCCESS" else "RETRY_PENDING"
            task["result"] = res["summary"][:200]
            task["evidence"] = res["evidence_path"]
            _record_experience(task, res)
            print(f"[{_now()}]   -> {res['status']} [{res.get('tier')}] "
                  f"task=${res.get('task_cost_usd', 0):.4f} "
                  f"month=${res.get('month_spend_usd', 0):.2f}/${res.get('month_cap_usd', 0):.0f}: "
                  f"{res['summary'][:56]}")
            if res["status"] == "SUCCESS":
                done += 1
        except Exception as e:
            task["status"] = "RETRY_PENDING"
            print(f"[{_now()}]   -> error: {e}")
        _save(QUEUE, q)

        if max_tasks and done >= max_tasks:
            print(f"[{_now()}] reached max {max_tasks} tasks. Stopping.")
            _save(STATE, {"ts": _now(), "state": "STOPPED_MAX", "completed": done})
            break
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
