#!/usr/bin/env python3
"""HELM COUNCIL DAEMON — the council leads; the founder stops being the transport.

Until now a human (Michael) was the loop: seed a task, run a script, read the
output, paste it somewhere, run the next script. That is the "copy-paste transport
layer" the North Star explicitly forbids:

    "Michael must not remain the routine transport layer between agents,
     models, IDEs, or execution systems."

This daemon closes the loop. It runs continuously and, each cycle:

  1. asks the scheduler what is genuinely runnable (mission/capability scope,
     dependencies, adapter readiness, blockers);
  2. dispatches everything eligible CONCURRENTLY through the real governed path
     (per-task lease -> fencing token -> CouncilDispatchGateway -> real adapter);
  3. lets the INDEPENDENT validators judge the artifacts;
  4. writes an append-only heartbeat of what it OBSERVED.

Guarantees kept:
  * founder-only gates stay founder-only (an Apple/App-Store capability is
    BLOCKED_EXTERNAL and the daemon never touches it);
  * LOCAL_ONLY adapters by default -> zero credentials, zero spend;
  * nothing is invented: if a cycle dispatches nothing, it records IDLE and why.

Stop it with SIGINT. It holds no global lock, so it never blocks you.
"""
from __future__ import annotations

import argparse
import datetime
import json
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

HEARTBEAT = ROOT / "coordination" / "council" / "council_heartbeat.jsonl"

_stop = False


def _sigint(*_):
    global _stop
    _stop = True
    print("\n[council] stop requested; finishing current cycle...", flush=True)


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=20.0, help="seconds between cycles")
    ap.add_argument("--max-cycles", type=int, default=0, help="0 = run forever")
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _sigint)

    from backend.mission_control.persistent_scheduler import PersistentScheduler

    evidence = ROOT / "coordination" / "council" / "daemon"
    evidence.mkdir(parents=True, exist_ok=True)
    sched = PersistentScheduler(evidence_dir=evidence)

    conc = sched.concurrency_report()
    print(f"[council] HELM council daemon online", flush=True)
    print(f"[council] concurrency: {conc['concurrency_mode']} "
          f"effective={conc['effective_limit']}/{conc['configured_limit']} ({conc['status']})",
          flush=True)

    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    cycle = 0
    while not _stop:
        cycle += 1
        t0 = time.time()
        try:
            blockers = sched.load_blockers()
            runnable = sched.evaluate_runnable_tasks()
            ranked = sched.rank_tasks(runnable, blockers)

            if not ranked:
                # IDLE is a real state with a real reason. Never dressed up.
                rec = {"ts": now(), "cycle": cycle, "state": "IDLE",
                       "runnable": len(runnable), "ranked": 0,
                       "reason": ("no task passed scope/dependency/adapter eligibility"
                                  if runnable else "no PENDING/FAILED tasks in the queue")}
                print(f"[council] cycle {cycle}: IDLE ({rec['reason']})", flush=True)
            else:
                res = sched.run_once()
                ok = [d["task_id"] for d in res["dispatched"] if d["success"]]
                bad = [d["task_id"] for d in res["dispatched"] if not d["success"]]
                rec = {"ts": now(), "cycle": cycle, "state": "ACTIVE",
                       "dispatched": res["dispatched_count"],
                       "passed": ok, "failed": bad,
                       "concurrency": res.get("concurrency"),
                       "seconds": round(time.time() - t0, 1)}
                print(f"[council] cycle {cycle}: dispatched={res['dispatched_count']} "
                      f"pass={len(ok)} fail={len(bad)} in {rec['seconds']}s", flush=True)

            # CONTINUOUS MONITORING (NIST SP 800-137): re-derive HELM's own control
            # posture from live evidence every cycle. Compliance is not a document you
            # file once; it is a property you must keep proving.
            try:
                from backend.security.helm_conmon import assess
                pos = assess()
                rec["security_posture_percent"] = pos["posture_percent"]
                rec["open_findings"] = pos["open_findings"]
                if pos["high_findings"]:
                    print(f"[council] !! {pos['high_findings']} HIGH security finding(s)", flush=True)
            except Exception as e:
                rec["security_posture_percent"] = "UNKNOWN"
                rec["conmon_error"] = str(e)[:120]

            with open(HEARTBEAT, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")

        except Exception as e:      # a cycle may fail; the council must not die silently
            rec = {"ts": now(), "cycle": cycle, "state": "ERROR", "error": str(e)[:300]}
            # CONTINUOUS MONITORING (NIST SP 800-137): re-derive HELM's own control
            # posture from live evidence every cycle. Compliance is not a document you
            # file once; it is a property you must keep proving.
            try:
                from backend.security.helm_conmon import assess
                pos = assess()
                rec["security_posture_percent"] = pos["posture_percent"]
                rec["open_findings"] = pos["open_findings"]
                if pos["high_findings"]:
                    print(f"[council] !! {pos['high_findings']} HIGH security finding(s)", flush=True)
            except Exception as e:
                rec["security_posture_percent"] = "UNKNOWN"
                rec["conmon_error"] = str(e)[:120]

            with open(HEARTBEAT, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
            print(f"[council] cycle {cycle}: ERROR {e}", flush=True)

        if args.max_cycles and cycle >= args.max_cycles:
            break
        for _ in range(int(args.interval * 10)):
            if _stop:
                break
            time.sleep(0.1)

    print(f"[council] offline after {cycle} cycles", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
