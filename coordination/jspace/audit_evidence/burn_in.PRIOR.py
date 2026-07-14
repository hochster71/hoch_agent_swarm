"""HJOS read-only burn-in tracker.

Automatic quarantine stays OFF until a proven read-only burn-in completes.
Burn-in criteria (all required):
  - min_cycles consecutive *clean* cycles
  - each clean cycle: no exception, state_mutated=false
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_MIN_CYCLES = 5


class BurnInTracker:
    def __init__(self, root: Path, *, min_cycles: int = DEFAULT_MIN_CYCLES) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "burn_in.json"
        self.min_cycles = min_cycles

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            st = json.loads(self.path.read_text(encoding="utf-8"))
            st.setdefault("min_cycles", self.min_cycles)
            return st
        except Exception:
            e = self._empty()
            e["corrupt"] = True
            return e

    def _empty(self) -> Dict[str, Any]:
        return {
            "schema": "HJOS_BURN_IN_v1",
            "min_cycles": self.min_cycles,
            "completed_cycles": 0,
            "clean_cycles": 0,
            "burn_in_complete": False,
            "automatic_quarantine_enabled": False,
            "history": [],
        }

    def record_cycle(
        self,
        *,
        cycle_id: str,
        overall: str,
        state_mutated: bool,
        exception: Optional[str] = None,
    ) -> Dict[str, Any]:
        st = self.load()
        st["min_cycles"] = self.min_cycles
        st["completed_cycles"] = int(st.get("completed_cycles") or 0) + 1

        clean = (not state_mutated) and (exception is None)
        if clean:
            st["clean_cycles"] = int(st.get("clean_cycles") or 0) + 1
        else:
            st["clean_cycles"] = 0
            st["last_dirty"] = {
                "cycle_id": cycle_id,
                "overall": overall,
                "state_mutated": state_mutated,
                "exception": exception,
                "at": _now(),
            }

        hist = list(st.get("history") or [])
        hist.append({
            "cycle_id": cycle_id,
            "overall": overall,
            "state_mutated": state_mutated,
            "exception": exception,
            "clean": clean,
            "at": _now(),
        })
        st["history"] = hist[-50:]

        if st.get("burn_in_complete"):
            st["automatic_quarantine_enabled"] = True
        elif (
            int(st["clean_cycles"]) >= self.min_cycles
            and int(st["completed_cycles"]) >= self.min_cycles
        ):
            st["burn_in_complete"] = True
            st["burn_in_completed_at"] = _now()
            st["automatic_quarantine_enabled"] = True

        st["updated_at"] = _now()
        self.path.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return st


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
