#!/usr/bin/env python3
"""REQ-NS-002 — verified_founder_minutes_per_shipped_dollar is MEASURED, not estimated.

PASS when the instrument exists and returns a structured observation:
  - value is a number when settled verified revenue > 0
  - value is UNDEFINED (not invented) when revenue is zero

FAIL when the instrument is missing or fabricates a numeric placeholder without revenue.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "coordination" / "goal" / "founder_minutes_metric_report.json"


def main() -> int:
    report = {
        "requirement": "REQ-NS-002",
        "status": "FAIL",
        "detail": "",
    }
    try:
        from backend.mission_control.hoch_ledger import HochLedger

        ns = HochLedger().north_star()
        report["north_star"] = ns
        rev = float(ns.get("revenue_settled_usd") or 0)
        val = ns.get("value")
        # Instrument present and honest about zero revenue
        if rev <= 0:
            if val == "UNDEFINED" and ns.get("revenue_chain_valid") is not False:
                report["status"] = "PASS"
                report["detail"] = (
                    "instrument LIVE; settled revenue $0 → metric UNDEFINED "
                    "(not estimated, not infinity)"
                )
            else:
                report["status"] = "FAIL"
                report["detail"] = f"zero revenue but value={val!r} (must be UNDEFINED)"
        else:
            if isinstance(val, (int, float)) and ns.get("revenue_chain_valid"):
                report["status"] = "PASS"
                report["detail"] = f"metric={val} from minutes/revenue (settled ${rev})"
            else:
                report["status"] = "FAIL"
                report["detail"] = f"revenue ${rev} but metric not numeric/chain invalid: {val}"
    except Exception as e:
        report["status"] = "FAIL"
        report["detail"] = f"instrument error: {e}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(report["detail"])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
