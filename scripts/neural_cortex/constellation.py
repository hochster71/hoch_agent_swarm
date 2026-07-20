#!/usr/bin/env python3
"""Mission Constellation — every real mission is a star.

Grounded by law: every star is a real mission record from the append-only ledger
(coordination/soak/soak_missions.jsonl). Nothing is invented.

  size      = mission duration (complexity proxy)     ·  ✧  ✦  ★
  color     = real result state (PASS green / FAIL red)
  brightness= recency (recent = bright, older fades but is not deleted — work history)

Standalone:  .venv/bin/python -m scripts.neural_cortex.constellation
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
MISSIONS = ROOT / "coordination" / "soak" / "soak_missions.jsonl"

from rich.text import Text
from textual.widgets import Static


def _read_missions(limit: int = 600) -> list[dict]:
    out = []
    try:
        lines = MISSIONS.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _pos(mission_id: str, w: int, h: int) -> tuple[int, int]:
    """Deterministic, stable star position from the mission id (not RNG)."""
    d = hashlib.md5((mission_id or "?").encode()).digest()
    c = 1 + (d[0] << 8 | d[1]) % (w - 2)
    r = 1 + (d[2] << 8 | d[3]) % (h - 2)
    return r, c


def _star_glyph(duration_s) -> str:
    d = duration_s or 0
    return "·" if d < 15 else "✧" if d < 40 else "✦" if d < 80 else "★"


class Constellation(Static):
    """A starfield of real missions. Recent = bright; failures = red; older fades."""
    W, H = 90, 26

    def render(self):
        missions = _read_missions()
        n = len(missions)
        grid = [[(" ", None) for _ in range(self.W)] for _ in range(self.H)]
        passed = failed = 0

        for i, m in enumerate(missions):
            mid = m.get("mission_id", "?")
            r, c = _pos(mid, self.W, self.H)
            recency = (i + 1) / n if n else 0.0            # 0 = oldest, 1 = newest
            result = m.get("result", "?")
            if result == "FAIL":
                failed += 1
                style = "red3" if recency > 0.6 else "red3 dim"
            elif result == "PASS":
                passed += 1
                # brightness by recency — recent bright green, older fades (history kept)
                style = ("bold green3" if recency > 0.85 else "green3" if recency > 0.5
                         else "green4" if recency > 0.2 else "grey37")
            else:
                style = "grey42"
            g = _star_glyph(m.get("duration_s"))
            # newest few twinkle brighter with a halo char
            if 0 <= r < self.H and 0 <= c < self.W:
                # don't clobber a brighter (more recent) star already placed
                existing = grid[r][c]
                if existing[0] == " ":
                    grid[r][c] = (g, style)

        out = Text()
        title = Text()
        title.append("  ✦ MISSION CONSTELLATION  ", "bold gold1")
        title.append(f"{n} stars", "grey62")
        title.append("   ", "")
        title.append(f"● {passed} verified  ", "green3")
        title.append(f"✖ {failed} failed  ", "red3")
        title.append("· recent=bright  older=dim (history kept)\n", "grey42")
        out.append_text(title)
        out.append("\n")
        for r in range(self.H):
            out.append("  ")
            for c in range(self.W):
                ch, style = grid[r][c]
                out.append(ch, style=style)
            out.append("\n")
        if n == 0:
            out.append("\n  (no missions yet — the sky is empty until real work runs)\n", "grey42")
        return out


if __name__ == "__main__":
    from rich.console import Console
    Console().print(Constellation().render())
