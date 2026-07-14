#!/usr/bin/env python3
"""Run one HJOS (HELM J-SPACE Observability Swarm) cycle.

Read-only. Writes assessments/alerts/health under coordination/jspace/.
Never promotes, executes tasks, or mutates HELM authoritative state.

Usage:
  .venv/bin/python scripts/jspace/run_hjos_cycle.py
  .venv/bin/python scripts/jspace/run_hjos_cycle.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="HJOS read-only observation cycle")
    ap.add_argument("--json", action="store_true", help="print full JSON result")
    ap.add_argument("--ledger", type=Path, default=None, help="override ledger root")
    args = ap.parse_args()

    from backend.jspace.runner import run_hjos_cycle

    result = run_hjos_cycle(ledger_root=args.ledger)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"HJOS {result['cycle_id']}  overall={result['overall']}  "
            f"alerts={result['open_alerts']}  action={result['recommended_action']}  "
            f"promotion={result['promotion_authority']}  mutated={result['state_mutated']}"
        )
        for f in (result.get("worst_findings") or [])[:5]:
            print(
                f"  - [{f.get('assessment')}] {f.get('observer')}: "
                f"{f.get('subject')} → {f.get('recommended_action')}"
            )
    # Non-zero if withhold/block recommended (still not a mutation)
    if result.get("recommended_action") in (
        "WITHHOLD_PROMOTION",
        "ESCALATE_FOUNDER_GATE",
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
