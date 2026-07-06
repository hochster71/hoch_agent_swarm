#!/usr/bin/env python3
"""
G1 Demand-Validation gate — closes on EVIDENCE, not vibes.

Reads has_live_project_tracker/data/demand_validation.json (prospects, discovery_calls,
wtp_signals, named_buyers) and checks each count against its threshold. Verdict PASS only
when real logged evidence meets ALL thresholds. With --update-register it flips blocker G-4
to PASS in goal_blocker_register.json ONLY when PASS (never fabricates a green gate).

Exit 0 always (reporter). Prints machine JSON + a human line.
"""
import json
import os
import sys
import datetime

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DV = os.path.join(REPO, "has_live_project_tracker/data/demand_validation.json")
REG = os.path.join(REPO, "has_live_project_tracker/data/goal_blocker_register.json")


def evaluate(d):
    """Pure: data -> (verdict, counts, missing). No side effects."""
    th = d.get("thresholds", {}) or {}
    counts = {
        "prospects": len(d.get("prospects", []) or []),
        "discovery_calls": len(d.get("discovery_calls", []) or []),
        "wtp_signals": len(d.get("wtp_signals", []) or []),
        "named_buyers": len(d.get("named_buyers", []) or []),
    }
    missing = {k: (th.get(k, 0) - counts[k]) for k in counts if counts[k] < th.get(k, 0)}
    return ("PASS" if not missing else "PENDING"), counts, missing


def main():
    try:
        d = json.load(open(DV))
    except Exception as e:  # noqa
        print(json.dumps({"verdict": "NO_DATA", "error": str(e)}))
        sys.exit(0)
    verdict, counts, missing = evaluate(d)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    out = {"schema": "demand-validation-check-v1", "checked_at": now, "verdict": verdict,
           "counts": counts, "thresholds": d.get("thresholds", {}), "missing": missing}
    print(json.dumps(out, indent=2))

    if "--update-register" in sys.argv and verdict == "PASS":
        try:
            reg = json.load(open(REG))
            for b in reg.get("blockers", []):
                if b.get("id") == "G-4":
                    b["status"] = "PASS"
                    b["closed_on_evidence"] = now
            json.dump(reg, open(REG, "w"), indent=2)
            print("G-4 (demand validation) flipped to PASS on real evidence.")
        except Exception as e:  # noqa
            print("register update failed:", e)

    print(f"DEMAND VALIDATION: {verdict} · {counts} · missing={missing or 'none'}")
    sys.exit(0)


if __name__ == "__main__":
    main()
