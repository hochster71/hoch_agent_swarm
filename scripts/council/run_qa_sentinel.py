#!/usr/bin/env python3
"""run_qa_sentinel.py — the autonomous auditor. Does the "asking" Michael is tired of.

Michael's role in this program was the intelligence layer: asking "is that observed? what's
the source? prove it." This runs that interrogation continuously, on a schedule, so he
doesn't have to. Each cycle it executes a battery of MACHINE checks (not model opinions),
classifies each result OBSERVED / ASSERTED / UNKNOWN, and:

  * silently records everything it can prove (that is the point — proven things don't
    interrupt you);
  * files a founder-contract escalation ONLY when a check reveals something that needs
    judgment or a founder-only action.

It never escalates something it could verify. It never performs a PROPOSE_ONLY or
FOUNDER_ONLY action. It is read-only about the world and write-only to the evidence trail.

    python scripts/council/run_qa_sentinel.py            # one pass
    python scripts/council/run_qa_sentinel.py --loop 900 # every 15 min, forever
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HEARTBEAT = ROOT / "coordination" / "founder" / "qa_sentinel_heartbeat.jsonl"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sh(cmd: str, timeout: int = 60) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except Exception as e:  # noqa: BLE001
        return 255, str(e)


# ── the checks. Each returns (name, classification, ok, detail, needs_founder). ──
def check_factory_census() -> tuple:
    try:
        from backend.mission_control.factory_census import census
        c = census()
        earning = c["earning"]
        return ("factory_census", "OBSERVED", True,
                f"declared {c['declared']} · ran {c['ever_ran']} · producing {c['producing']} · EARNING {earning}",
                False)
    except Exception as e:  # noqa: BLE001
        return ("factory_census", "UNKNOWN", False, f"census unreadable: {e}", False)


def check_security_posture() -> tuple:
    pos = ROOT / "coordination" / "security" / "helm_control_posture.json"
    if not pos.exists():
        return ("security_posture", "UNKNOWN", False, "no ConMon assessment on disk", False)
    d = json.loads(pos.read_text())
    high = d.get("high_findings", 0)
    return ("security_posture", "OBSERVED", high == 0,
            f"{d.get('posture_percent')}% · high findings {high}",
            high > 0)  # a HIGH finding is judgment-worthy -> escalate


def check_spend_caps() -> tuple:
    try:
        from backend.mission_control.spend_meter import SpendMeter
        s = SpendMeter().summary()
        return ("spend_caps", "OBSERVED", True,
                f"today ${s.get('today_usd', 0):.2f} / cap ${s.get('daily_cap_usd', 5):.2f}", False)
    except Exception as e:  # noqa: BLE001
        return ("spend_caps", "UNKNOWN", False, f"spend meter unreadable: {e}", False)


def check_open_escalations() -> tuple:
    q = ROOT / "coordination" / "founder" / "escalation_queue.jsonl"
    n = len(q.read_text().splitlines()) if q.exists() else 0
    return ("open_escalations", "OBSERVED", True, f"{n} awaiting founder", False)


CHECKS = [check_factory_census, check_security_posture, check_spend_caps, check_open_escalations]


def one_pass() -> dict:
    from backend.council.founder_model import Escalation, escalate

    results = []
    for fn in CHECKS:
        name, cls, ok, detail, needs_founder = fn()
        results.append({"check": name, "class": cls, "ok": ok, "detail": detail})
        if needs_founder:
            escalate(
                Escalation(
                    one_sentence_question=f"QA sentinel found something needing you: {name}",
                    why_it_needs_you="a HIGH-severity or judgment condition was OBSERVED",
                    options=["Review and direct", "Acknowledge and defer"],
                    recommendation_and_why=f"review: {detail}",
                    evidence_sanitized=detail,
                    cost_of_delay="rises with time for security findings",
                    reversible=True,
                ),
                can_prove_answer=False,
            )

    rec = {"ts": _now(), "cycle_results": results,
           "provable_now": sum(1 for r in results if r["class"] == "OBSERVED"),
           "unknown": sum(1 for r in results if r["class"] == "UNKNOWN")}
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    with open(HEARTBEAT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=float, default=0, help="seconds between passes; 0 = one pass")
    args = ap.parse_args()

    while True:
        rec = one_pass()
        print(f"[qa-sentinel] {rec['ts']} — {rec['provable_now']} OBSERVED, {rec['unknown']} UNKNOWN")
        for r in rec["cycle_results"]:
            mark = "OK " if r["ok"] else "!! "
            print(f"    {mark}{r['check']:20s} [{r['class']}] {r['detail']}")
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == "__main__":
    raise SystemExit(main())
