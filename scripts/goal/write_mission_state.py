#!/usr/bin/env python3
"""Write coordination/goal/mission_state.json and print executive dashboard."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.mission_control.mission_state import (  # noqa: E402
    render_executive_text,
    write_mission_state,
)


def main() -> int:
    mid = sys.argv[1] if len(sys.argv) > 1 else None
    state = write_mission_state(mission_id=mid)
    print(render_executive_text(state))
    print()
    print(f"written: coordination/goal/mission_state.json")
    print(f"overall: {state['overall']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
