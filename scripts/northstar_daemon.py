#!/usr/bin/env python3
"""NORTHSTAR DAEMON — the persistent runner. Set a northstar, walk away.

Each cycle: (1) Planner refills the queue toward the goal, (2) run the next SAFE task through the
real engine, (3) stage founder-gated work at the doorstep, (4) write progress + a doorstep digest.
Runs forever (or NS_MAX_ITERS). SAFE by default: only research/design/verify/analysis execute
autonomously; code/'hard' tasks are DEFERRED until the founder enables code mode (AGENT_ALLOW_CODE=1);
founder-gated (launch/money/legal/submit) is always STAGED, never executed.

Governance inherited from the harness: tier router + verify gate + fail-closed cost cap + DOORSTEP
+ change-control board. This daemon never touches the control plane or itself.
"""
from __future__ import annotations
import datetime, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

QUEUE = ROOT / "has_live_project_tracker/data/hoch_loop_queue.json"
STATE = ROOT / "has_live_project_tracker/data/northstar_state.json"
DIGEST = ROOT / "has_live_project_tracker/data/doorstep_digest.json"
HANDOFF = ROOT / "has_live_project_tracker/data/founder_handoff_queue.json"
EXPERIENCE = ROOT / "data/prompt_brain/outcome_feedback_ledger.jsonl"

FOUNDER_GATED = {"blocked_release", "blocked_monetization", "blocked_secret_handling",
                 "blocked_external_outreach", "blocked_investor_engagement"}
SAFE_CLASSES = {"research", "design", "verify", "analysis"}
ALLOW_CODE = os.environ.get("AGENT_ALLOW_CODE") == "1"


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _load(p, d):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def _save(p, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, indent=2))


def _stage_founder(task):
    hq = _load(HANDOFF, {"schema_version": "1.0", "staged": []})
    if not any(s.get("id") == task["task_id"] for s in hq.get("staged", [])):
        hq.setdefault("staged", []).append({
            "id": task["task_id"], "title": task.get("task_name"),
            "status": "READY_FOR_FOUNDER", "why_founder": "launch/money/legal — founder acts",
            "staged_at": _now(), "northstar": task.get("northstar")})
        _save(HANDOFF, hq)


def _digest(planner_status):
    hq = _load(HANDOFF, {"staged": []})
    door = [s for s in hq.get("staged", []) if s.get("status") == "READY_FOR_FOUNDER"]
    _save(DIGEST, {"ts": _now(), "northstar": planner_status.get("goal"),
                   "phase": planner_status.get("phase"), "progress": planner_status,
                   "at_the_door": door,
                   "message": (f"{len(door)} decision(s) waiting for you." if door
                               else "Nothing needs you right now — the factories are working.")})


def main():
    from backend.agent_executor import execute_task
    import scripts.northstar_planner as planner

    max_iters = int(os.environ.get("NS_MAX_ITERS", "0"))
    sleep_s = int(os.environ.get("NS_SLEEP", "5"))
    i = 0
    print(f"[{_now()}] NORTHSTAR DAEMON up. code_mode={'ON' if ALLOW_CODE else 'OFF (safe)'} "
          f"max={max_iters or 'forever'}")

    while True:
        i += 1
        r = planner.refill()
        q = _load(QUEUE, [])
        allowed = SAFE_CLASSES | ({"code"} if ALLOW_CODE else set())

        # stage any founder-gated pending work
        for t in q:
            if t.get("status") == "PENDING" and (t.get("founder_gated") or t.get("policy_category") in FOUNDER_GATED):
                t["status"] = "STAGED_FOR_FOUNDER"
                _stage_founder(t)
        _save(QUEUE, q)

        # pick next executable SAFE task for the current northstar
        nxt = next((t for t in q if t.get("status") == "PENDING"
                    and not t.get("founder_gated")
                    and t.get("policy_category") not in FOUNDER_GATED
                    and t.get("task_class") in allowed), None)

        if nxt is None:
            # nothing to run: either all done, or remaining tasks need code mode
            deferred = [t for t in q if t.get("status") == "PENDING" and t.get("task_class") not in allowed]
            st = planner.status()
            st["deferred_need_code_mode"] = len(deferred)
            st["ts"] = _now()
            _save(STATE, st)
            _digest(st)
            if r.get("phase") == "DONE" and not deferred:
                print(f"[{_now()}] NORTHSTAR COMPLETE. Idle.")
                break
            print(f"[{_now()}] idle — phase={st.get('phase')} deferred(code)={len(deferred)}")
        else:
            nxt["status"] = "RUNNING"; _save(QUEUE, q)
            print(f"[{_now()}] EXEC {nxt['task_id']} [{nxt.get('task_class')}]")
            try:
                res = execute_task(nxt)
                nxt["status"] = "completed" if res["status"] == "SUCCESS" else "RETRY_PENDING"
                nxt["result"] = res["summary"][:180]
                nxt["evidence"] = res["evidence_path"]
                EXPERIENCE.parent.mkdir(parents=True, exist_ok=True)
                with open(EXPERIENCE, "a") as f:
                    f.write(json.dumps({"ts": _now(), "kind": "combat_record", "engine": "northstar.v1",
                        "task_id": nxt["task_id"], "northstar": nxt.get("northstar"),
                        "phase": nxt.get("phase"), "status": res["status"],
                        "verified": res.get("verified"), "tier": res.get("tier"),
                        "cost_usd": res.get("task_cost_usd"), "summary": res["summary"][:200]}) + "\n")
                print(f"[{_now()}]  -> {res['status']} {'✓' if res.get('verified') else ''} "
                      f"${res.get('task_cost_usd',0):.4f}")
            except Exception as e:
                nxt["status"] = "RETRY_PENDING"
                print(f"[{_now()}]  -> error: {e}")
            _save(QUEUE, q)
            st = planner.status(); st["ts"] = _now(); _save(STATE, st); _digest(st)

        if max_iters and i >= max_iters:
            print(f"[{_now()}] reached max {max_iters} iters. Stopping.")
            break
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
