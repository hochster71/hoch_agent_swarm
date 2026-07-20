#!/usr/bin/env python3
"""HELM terminal identity — one visual language across boot, dashboards, and logs.

Design language (Michael, 2026-07-18):
  center = HELM (decision core) · downward flow = execution · horizontal branches =
  specialization · █ block pulses = real work in motion · ● ◉ ○ = health · ▲ ▼ = state
  transitions · and UNKNOWN is ALWAYS rendered explicitly (?/UNKNOWN), never implied
  healthy — matching HELM's runtime philosophy.
"""
from __future__ import annotations

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

BANNER = r"""██╗  ██╗███████╗██╗     ███╗   ███╗
██║  ██║██╔════╝██║     ████╗ ████║
███████║█████╗  ██║     ██╔████╔██║
██╔══██║██╔══╝  ██║     ██║╚██╔╝██║
██║  ██║███████╗███████╗██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝"""
TAGLINE = "Hybrid Execution & Lifecycle Manager"

# canonical state -> (glyph, style). The SAME mapping everywhere.
STATE = {
    "ONLINE":    ("●", "green3"),
    "HEALTHY":   ("●", "green3"),
    "READY":     ("●", "green3"),
    "ACTIVE":    ("◉", "cyan"),
    "AVAILABLE": ("●", "spring_green3"),
    "VERIFIED":  ("✔", "green3"),
    "EXECUTING": ("█", "cyan"),
    "BUILDING":  ("█", "cyan"),
    "WARNING":   ("▲", "yellow2"),
    "THROTTLED": ("▓", "yellow2"),
    "DEGRADED":  ("◆", "dark_orange3"),
    "WAITING":   ("▒", "grey54"),
    "QUEUED":    ("▒", "grey54"),
    "PLANNING":  ("▒", "grey54"),
    "RESERVED":  ("▒", "grey37"),
    "IDLE":      ("○", "grey42"),
    "OFFLINE":   ("○", "grey42"),
    "FAILED":    ("✖", "red3"),
    "BLOCKED":   ("✖", "red3"),
    "UNKNOWN":   ("?", "grey35"),
}
ACCENT = "deep_sky_blue1"
FRAME = "#1c3a52"

# the legend exactly as specified
LEGEND = [
    ("●", "ONLINE", "green3"), ("◉", "ACTIVE", "cyan"), ("○", "OFFLINE", "grey42"),
    ("▲", "WARNING", "yellow2"), ("◆", "DEGRADED", "dark_orange3"), ("✖", "FAILED", "red3"),
    ("✔", "VERIFIED", "green3"), ("▒", "QUEUED", "grey54"), ("█", "EXECUTING", "cyan"),
    ("▓", "THROTTLED", "yellow2"), ("?", "UNKNOWN", "grey35"),
]


def dot(state: str) -> Text:
    """A status glyph + label in the canonical style. Unknown states render as '? UNKNOWN'."""
    st = (state or "UNKNOWN").upper()
    glyph, style = STATE.get(st, STATE["UNKNOWN"])
    t = Text()
    t.append(glyph + " ", style=style)
    t.append(st, style=style)
    return t


def glyph(state: str) -> tuple[str, str]:
    return STATE.get((state or "UNKNOWN").upper(), STATE["UNKNOWN"])


def pulse_bar(frac: float, width: int = 18, style: str = "cyan", head: bool = True) -> Text:
    """A █-block work bar (0..1). Real work in motion — length ties to a real quantity."""
    frac = 0.0 if frac is None else max(0.0, min(1.0, frac))
    n = int(round(frac * width))
    t = Text()
    if n <= 0:
        t.append("░" * width, style="grey23")
        return t
    t.append("█" * max(0, n - 1), style=style)
    t.append("▶" if head else "█", style=style)
    t.append("░" * (width - n), style="grey23")
    return t


def banner_text(subtitle: str | None = None) -> Text:
    t = Text()
    for i, line in enumerate(BANNER.splitlines()):
        # subtle vertical gradient for depth
        shade = ["deep_sky_blue1", "deep_sky_blue2", "dodger_blue1",
                 "dodger_blue2", "blue3", "blue3"][min(i, 5)]
        t.append(line + "\n", style=f"bold {shade}")
    t.append(TAGLINE, style="grey62")
    if subtitle:
        t.append("   ·   ", style="grey42")
        t.append(subtitle, style=ACCENT)
    return t


def boot_banner_panel(subtitle: str | None = None) -> Panel:
    return Panel(Align.center(banner_text(subtitle)), border_style=FRAME, padding=(0, 2))


def legend_text() -> Text:
    t = Text()
    for i, (g, label, style) in enumerate(LEGEND):
        t.append(f"{g} ", style=style)
        t.append(f"{label}  ", style="grey54")
        if (i + 1) % 4 == 0:
            t.append("\n")
    return t


def north_star_strip(ns: dict):
    """Layer 12 — the persistent goal reminder. Renders the computed north-star number AND
    the blocking reality; ETA is shown as UNKNOWN (no estimator — never fabricated)."""
    ns = ns or {}
    t = Text()
    t.append(" ★ NORTH STAR ", style="bold gold1")
    t.append("│ ", FRAME)
    t.append(f"{ns.get('champion', 'UNKNOWN')} ", ACCENT)
    t.append("│ ", FRAME)
    pct = ns.get("north_star_pct")
    if isinstance(pct, (int, float)):
        t.append_text(pulse_bar(pct / 100.0, width=14, style="gold1", head=False))
        t.append(f" {pct:.0f}% ", "gold1")
    else:
        t.append("UNKNOWN ", STATE["UNKNOWN"][1])
    t.append("│ ", FRAME)
    op = str(ns.get("op_status", "UNKNOWN"))
    op_style = STATE["WARNING"][1] if "BLOCK" in op else ("green3" if op in ("LIVE", "READY_FOR_RELEASE") else "grey62")
    t.append("op ", "grey54"); t.append(f"{op} ", op_style)
    t.append("│ ", FRAME)
    t.append("critical ", "grey54")
    t.append(f"{ns.get('critical_remaining','?')}/{ns.get('critical_total','?')} open ", "white")
    t.append("│ ", FRAME)
    fg = ns.get("founder_gates", 0)
    t.append("founder gates ", "grey54"); t.append(f"{fg} ", STATE["WARNING"][1] if fg else "green3")
    t.append("│ ", FRAME)
    t.append("ETA ", "grey54"); t.append(f"{ns.get('eta', 'UNKNOWN')} ", STATE["UNKNOWN"][1])
    return Panel(t, border_style="gold1", padding=(0, 1))


def box(title: str, body, border: str = FRAME) -> Panel:
    return Panel(body, title=Text(title, style=f"bold {ACCENT}"),
                 title_align="left", border_style=border, padding=(0, 1))


if __name__ == "__main__":
    from rich.console import Console
    c = Console()
    c.print(boot_banner_panel("v1 · runtime identity"))
    c.print(box("STATUS LEGEND", legend_text()))
    c.print(dot("ACTIVE"), dot("UNKNOWN"), dot("VERIFIED"), dot("OFFLINE"))
    c.print(pulse_bar(0.75, style="cyan"))
