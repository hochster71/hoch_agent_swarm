#!/usr/bin/env python3
"""HELM Neural Cortex — a cinematic full-screen TUI where the runtime is a living nervous
system. Every mission is a pulse traveling HELM -> Council -> Capability -> Model ->
Validator -> Evidence.

TRUTH CONTRACT (enforced by cortex_state.CortexReader):
  * a pulse fires ONLY for a mission that actually completed (a real ledger record);
  * idle looks idle; a provider that is not exercised is IDLE/UNKNOWN, never fake-active;
  * no fake green — every glyph and number traces to observed state.

Run:  .venv/bin/python -m scripts.neural_cortex.cortex_app
Keys: q quit · space pause · l legend
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Header, Footer, RichLog

from scripts.neural_cortex.cortex_state import CortexReader, CAPABILITIES
from scripts.neural_cortex import brand as B
from scripts.neural_cortex.constellation import Constellation
from scripts.neural_cortex.swarm_bus import SwarmBus

# ---- palette (Michael's traffic semantics) ----
C_DONE, C_RUN, C_DISP, C_RESEARCH, C_FAIL, C_IDLE, C_UNK = (
    "green3", "yellow2", "dodger_blue1", "magenta", "red3", "grey42", "grey30")
GLYPH = {"idle": "○", "thinking": "◐", "working": "●", "completed": "◎",
         "blocked": "✕", "unknown": "·"}
GLYPH_STYLE = {"idle": C_IDLE, "thinking": "cyan", "working": C_RUN,
               "completed": C_DONE, "blocked": C_FAIL, "unknown": C_UNK}

W, H = 68, 22
# node layout: key -> (row, col, label)
NODES = {
    "HELM":    (1, 30, "HELM"),
    "ORCH":    (5, 12, "Orchestr"),
    "COUNCIL": (5, 30, "Council"),
    "AUDIT":   (5, 48, "Auditor"),
    "HASF":    (9, 6, "HASF"), "HRF": (9, 18, "HRF"), "HCF": (9, 29, "HCF"),
    "HSF":     (9, 40, "HSF"), "HMF": (9, 50, "HMF"), "HPF": (9, 60, "HPF"),
    "MODELS":  (14, 30, "Models"),
    "EVIDENCE": (19, 29, "Evidence"),
}
CENTER = (14, 33)  # models spine point pulses pass through


def _seg(a, b):
    (r0, c0), (r1, c1) = a, b
    n = max(abs(r1 - r0), abs(c1 - c0)) or 1
    return [(round(r0 + (r1 - r0) * i / n), round(c0 + (c1 - c0) * i / n)) for i in range(n + 1)]


def _path_for(cap: str):
    """The nervous-system route a mission travels."""
    helm = NODES["HELM"][:2]
    council = NODES["COUNCIL"][:2]
    capn = NODES.get(cap, NODES["HASF"])[:2]
    models = CENTER
    evidence = NODES["EVIDENCE"][:2]
    pts = []
    for a, b in [(helm, council), (council, capn), (capn, models), (models, evidence)]:
        pts += _seg(a, b)
    return pts


class Pulse:
    __slots__ = ("points", "idx", "color", "glyph", "mid")
    def __init__(self, cap, color, glyph, mid):
        self.points = _path_for(cap)
        self.idx = 0.0
        self.color = color
        self.glyph = glyph
        self.mid = mid
    def advance(self, speed=1.4):
        self.idx += speed
        return self.idx < len(self.points)
    def pos(self):
        return self.points[min(int(self.idx), len(self.points) - 1)]


class Cortex(Static):
    """The neural map canvas — rendered fresh each frame from live state + active pulses."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.state = {}
        self.pulses: list[Pulse] = []
        self.frame = 0

    def render(self):
        self.frame += 1
        grid = [[(" ", None) for _ in range(W)] for _ in range(H)]

        def put(r, c, ch, style):
            if 0 <= r < H and 0 <= c < W:
                grid[r][c] = (ch, style)

        # dim spine + branches (the "axons")
        for (r, c) in _seg(NODES["HELM"][:2], NODES["COUNCIL"][:2]) + \
                      _seg(NODES["COUNCIL"][:2], CENTER) + _seg(CENTER, NODES["EVIDENCE"][:2]):
            put(r, c, "·", "grey19")
        for cap in CAPABILITIES:
            for (r, c) in _seg(NODES["COUNCIL"][:2], NODES[cap][:2]):
                put(r, c, "·", "grey19")

        nodes = self.state.get("nodes", {})
        activity = self.state.get("activity", 0.0)

        # HELM glow — scales with real activity
        gr, gc = NODES["HELM"][:2]
        glow_style = (C_RUN if activity > 0.66 else "cyan" if activity > 0.2 else C_IDLE)
        ring = "█" if activity > 0.66 else "▓" if activity > 0.33 else "▒" if activity > 0.05 else "░"
        span = 3 if activity > 0.66 else 2 if activity > 0.2 else 1
        for dc in range(-span, span + 1):
            put(gr, gc + dc, ring, glow_style)
            put(gr - 1, gc + dc, ring if abs(dc) < span else " ", glow_style)

        # nodes: glyph + label colored by live state
        for key, (r, c, label) in NODES.items():
            st = nodes.get(key, "unknown")
            g = GLYPH.get(st, "·"); style = GLYPH_STYLE.get(st, C_UNK)
            if key == "HELM":
                put(r + 1, c, "◉", C_RUN if activity > 0.2 else "cyan")
            else:
                put(r, c, g, f"bold {style}")
            for i, ch in enumerate(label):
                put(r + 1, c - len(label) // 2 + i, ch, style if st != "idle" else "grey35")

        # models row: 9 dots whose brightness reflects real in-flight dispatches
        disp = self.state.get("dispatches", 0) or 0
        mr = NODES["MODELS"][0] + 1
        for i in range(9):
            lit = i < min(9, disp)
            put(mr, 22 + i * 2, "●" if lit else "•", C_RUN if lit else "grey23")

        # active pulses (real missions in motion)
        for p in self.pulses:
            r, c = p.pos()
            put(r, c, p.glyph, f"bold {p.color}")
            tr, tc = p.points[max(0, min(int(p.idx) - 1, len(p.points) - 1))]
            put(tr, tc, "•", p.color)

        # compose to Text
        out = Text()
        for r in range(H):
            for c in range(W):
                ch, style = grid[r][c]
                out.append(ch, style=style)
            out.append("\n")
        return out


class Telemetry(Static):
    """Branded side column: Executive Status Strip · Provider Matrix · Factory Overview ·
    Runtime — every indicator driven by real state, UNKNOWN rendered explicitly."""
    def render(self):
        s = self.state if hasattr(self, "state") else {}
        m = s.get("metrics", {})
        t = Text()

        def hdr(x):
            t.append(f"\n {x}\n", style=f"bold {B.ACCENT}")

        def val(x, suf="", unk="UNKNOWN"):
            return f"{x}{suf}" if x is not None else unk

        # ---- Executive Status Strip ----
        hdr("EXECUTIVE STATUS")
        for name, d in (s.get("exec_strip") or {}).items():
            t.append(f"  {name:<9}", "grey54")
            t.append_text(B.dot(d.get("state", "UNKNOWN")))
            if d.get("detail"):
                t.append(f"  {d['detail']}", "grey58")
            t.append("\n")

        # ---- Provider Matrix ----
        hdr("PROVIDERS")
        for name, d in (s.get("provider_matrix") or {}).items():
            t.append(f"  {name:<9}", "grey54")
            t.append_text(B.dot(d.get("state", "UNKNOWN")))
            if d.get("detail"):
                t.append(f"  {d['detail']}", "grey42")
            t.append("\n")

        # ---- Factory Overview (load bar tied to real mission counts) ----
        hdr("FACTORIES")
        for cap, d in (s.get("factories") or {}).items():
            g, st = B.glyph(d.get("state", "UNKNOWN"))
            t.append(f"  {cap:<5} ", "grey54")
            t.append_text(B.pulse_bar(d.get("load") or 0.0, width=12,
                                      style="cyan" if d.get("state") == "ACTIVE" else "grey37"))
            t.append(f" {d.get('state','?'):<9}", st)
            t.append(f"{d.get('missions',0)}\n", "grey58")

        # ---- Runtime core ----
        hdr("RUNTIME")
        sr = m.get("success_rate")
        t.append(f"  uptime    {val(m.get('uptime'))}\n", "white")
        t.append(f"  missions  {val(m.get('completed'))}   "
                 f"sr {f'{sr*100:.1f}%' if isinstance(sr,(int,float)) else 'UNKNOWN'}\n", "white")
        t.append(f"  tput      {val(m.get('throughput_per_hour'),'/h')}   "
                 f"p95 {val(m.get('p95_latency_s'),'s')}\n", "white")
        t.append(f"  cpu {val(m.get('cpu'),'%')}  mem {val(m.get('mem'),'%')}  "
                 f"lockretry {val(m.get('lock_retries'))}\n", "grey62")
        alerts = m.get("alerts") or []
        if alerts:
            t.append("  degradation: ", "grey54")
            t.append(", ".join(alerts) + "\n", B.STATE["WARNING"][1])
        return t


class NeuralCortex(App):
    CSS = """
    Screen { background: #05070d; }
    #canvas { width: 2fr; border: round #14324a; padding: 0 1; }
    #tele   { width: 1fr; border: round #14324a; }
    #timeline { height: 9; border: round #14324a; }
    #northstar { height: 3; }
    #missionsview, #screenview { border: round #14324a; }
    """
    # Keyboard-first operator console. Implemented screens show REAL state; the rest are
    # honest NOT-INSTRUMENTED placeholders that name their signal source (per the contract).
    NAV = {
        "1": ("HELM · Neural Cortex", "cortex", True),
        "2": ("J-SPACE · Mission Constellation", "missions", True),
        "3": ("Swarm Conversation Bus", "bus", True),
        "4": ("Dispatch", None, False),
        "5": ("Evidence", None, False),
        "6": ("Factories", None, False),
        "7": ("Mission Replay", None, False),
        "8": ("Knowledge Graph", None, False),
        "9": ("Live Builder", None, False),
        "0": ("Founder Gates", None, False),
    }
    BINDINGS = [("q", "quit", "Quit"), ("space", "pause", "Pause"), ("l", "legend", "Legend")] + \
               [(k, f"screen('{k}')", v[0].split(' ')[0]) for k, v in NAV.items()]

    def __init__(self):
        super().__init__()
        self.reader = CortexReader()
        self.paused = False
        self._poll_accum = 0.0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self.northstar = Static(id="northstar")
        yield self.northstar
        with Horizontal(id="cortexview"):
            self.canvas = Cortex(id="canvas")
            yield self.canvas
            self.tele = Telemetry(id="tele")
            yield self.tele
        self.constellation = Constellation(id="missionsview")
        yield self.constellation
        self.bus = SwarmBus(id="busview")
        yield self.bus
        self.screenview = Static(id="screenview")
        yield self.screenview
        self.timeline = RichLog(id="timeline", markup=True, highlight=False)
        yield self.timeline
        yield Footer()

    def on_mount(self):
        self.title = "HELM · J-SPACE"
        self.sub_title = f"{B.TAGLINE} — live runtime, no fake green"
        self.tele.state = {}
        self.active = "1"
        self.constellation.display = False
        self.bus.display = False
        self.screenview.display = False
        self.timeline.write(B.banner_text("J-SPACE Operations Bridge"))
        self.timeline.write(B.legend_text())
        self.timeline.write(Text("screens:  1 HELM   2 J-SPACE   3-0 planned "
                                 "(NOT-INSTRUMENTED — see JSPACE_SIGNAL_CONTRACT.md)", style="grey42"))
        self.set_interval(1 / 15, self.tick)  # ~15 fps

    def action_screen(self, key: str):
        title, view, built = self.NAV.get(key, (None, None, False))
        if title is None:
            return
        self.active = key
        cortex_on, miss_on, bus_on = (view == "cortex"), (view == "missions"), (view == "bus")
        self.query_one("#cortexview").display = cortex_on
        self.constellation.display = miss_on
        self.bus.display = bus_on
        self.screenview.display = not (cortex_on or miss_on or bus_on)
        self.sub_title = f"{title}  ·  {B.TAGLINE}"
        if not built:
            src = {
                "Council": "backend/dispatch council_router + /council/status — REAL, screen not yet built",
                "Dispatch": "coordination/council/relay/gateway_dispatch_ledger.jsonl — REAL, screen not yet built",
                "Evidence": "artifacts/factory/*, verification_ledger — REAL, screen not yet built",
                "Factories": "capability routing — REAL (in the side panel); dedicated screen planned",
                "Mission Replay": "append-only ledgers support deterministic replay — Time Machine planned",
                "Knowledge Graph": "knowledge_engine — NEEDS-INSTRUMENTATION for per-mission file reads",
                "Live Builder": "Claude builder-lane tool events — OFF-LIMITS for the local text-gen path",
                "Founder Gates": "executive_mission critical_path — REAL (in North Star strip); screen planned",
            }.get(title, "see JSPACE_SIGNAL_CONTRACT.md")
            body = Text()
            body.append(f"\n  {title} is not rendered as a fake.\n\n", "grey70")
            body.append(f"  Signal source: {src}\n\n", B.ACCENT)
            body.append("  Per the J-SPACE Signal Contract, a screen appears only once its real\n"
                        "  runtime signal is wired. Nothing here is invented.\n", "grey54")
            self.screenview.update(B.box(f"{title.upper()} — SCREEN NOT YET WIRED", body))

    def action_pause(self):
        self.paused = not self.paused
        self.sub_title = ("PAUSED" if self.paused else "live runtime nervous system — no fake green")

    def action_legend(self):
        self.timeline.write("[grey54]HELM → Council → Capability → Model → Validator → Evidence · "
                            "every pulse is one real completed mission[/]")

    def tick(self):
        if self.paused:
            return
        if self.active == "1":  # advance neural pulses only when the cortex is visible
            self.canvas.pulses = [p for p in self.canvas.pulses if p.advance()]
        self._poll_accum += 1 / 15
        if self._poll_accum >= 1.0:
            self._poll_accum = 0.0
            try:
                s = self.reader.poll()
            except Exception:
                s = {}
            self.canvas.state = s
            self.tele.state = s
            self.northstar.update(B.north_star_strip(s.get("north_star", {})))
            self.bus.pump()  # ingest real events always so history accrues; refresh when shown
            if self.active == "1":
                self.tele.refresh()
            elif self.active == "2":
                self.constellation.refresh()
            elif self.active == "3":
                self.bus.refresh()
            for ev in s.get("events", []):  # timeline is the black-box recorder — always on
                fail = ev["result"] == "FAIL"
                if self.active == "1":
                    self.canvas.pulses.append(
                        Pulse(ev["cap"], C_FAIL if fail else C_DONE,
                              "✕" if fail else "◎", ev["mission_id"]))
                col = C_FAIL if fail else C_DONE
                d = ev.get("duration_s")
                self.timeline.write(
                    f"[{col}]{'✕ FAIL' if fail else '◎ PASS'}[/] "
                    f"[white]{ev['mission_id']}[/] [grey54]{ev['cap']} · {ev['model']} · "
                    f"{d}s · ${ev.get('cost',0)}[/]")
            if len(self.canvas.pulses) > 16:
                self.canvas.pulses = self.canvas.pulses[-16:]
        if self.active == "1":
            self.canvas.refresh()


if __name__ == "__main__":
    NeuralCortex().run()
