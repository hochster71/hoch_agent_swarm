#!/usr/bin/env python3
"""Swarm Conversation Bus — the swarm coordinating, in its OWN real events.

Every line is an event HELM actually emitted (lease/authority/dispatch/validator/council/
governed event-bus). Nothing is invented dialogue: an agent "says" only what the runtime
literally recorded. The actor + event type are shown so the line reads as evidence, not
prose. This is "watch the organization operate", grounded.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from rich.text import Text
from textual.widgets import Static

D = ROOT / "coordination" / "council" / "daemon"
SOURCES = {
    "lease": D / "task_lease_ledger.jsonl",
    "dispatch": D / "dispatch_ledger.jsonl",
    "verify": D / "verification_ledger.jsonl",
    "council": ROOT / "coordination" / "council" / "council_heartbeat.jsonl",
    "bus": ROOT / "coordination" / "events" / "helm_events.jsonl",
}
KIND_STYLE = {"info": "grey70", "run": "yellow2", "ok": "green3", "fail": "red3",
              "warn": "dark_orange3", "dim": "grey42", "gov": "deep_sky_blue1"}
ACTOR_STYLE = {"LEASE": "cyan", "AUTHORITY": "magenta", "DISPATCH": "yellow2",
               "VALIDATOR": "green3", "COUNCIL": "deep_sky_blue1", "EVENT-BUS": "grey62"}


def _short(x, n=42):
    x = str(x or "")
    return x if len(x) <= n else x[: n - 1] + "…"


def _map(source: str, r: dict):
    """Map a real event record → (actor, verb, detail, kind). Returns None to skip."""
    tid = r.get("task_id", "")
    if source == "lease":
        st = r.get("status")
        m = {
            "ACQUIRED": ("LEASE", "acquired", f"{tid} · token {r.get('fencing_token')}", "info"),
            "DISPATCH_START": ("DISPATCH", "→ start", tid, "run"),
            "RELEASED": ("LEASE", "released", tid, "dim"),
            "LEASE_RECLAIMED_EXPIRED": ("LEASE", "reclaimed (expired)", tid, "warn"),
            "HELD_AUTHORITY": ("AUTHORITY", "bound", tid, "info"),
        }
        return m.get(st)
    if source == "dispatch" and r.get("status") == "COMPLETED":
        return ("DISPATCH", "completed", f"{tid} · {r.get('authority_class','')}", "ok")
    if source == "verify":
        v = r.get("verdict", "?")
        return ("VALIDATOR", v, tid, "ok" if v == "PASS" else "fail" if v == "FAIL" else "info")
    if source == "council":
        st = r.get("state")
        detail = f"dispatched {r.get('dispatched',0)} · pass {len(r.get('passed',[]) or [])} · fail {len(r.get('failed',[]) or [])}"
        return ("COUNCIL", f"cycle {r.get('cycle','?')} {st}", detail, "fail" if st == "ERROR" else "info")
    if source == "bus":
        return ("EVENT-BUS", r.get("type", "event"), r.get("producer") or r.get("mission_id") or "", "gov")
    return None


class _Tail:
    def __init__(self, path: Path):
        self.path = path
        self.offset = None  # None = not yet primed

    def new(self):
        out = []
        try:
            if not self.path.exists():
                return out
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                if self.offset is None:  # prime near the end so we don't flood with history
                    f.seek(0, 2)
                    self.offset = max(0, f.tell() - 2000)
                    f.seek(self.offset)
                    f.readline()
                    self.offset = f.tell()
                f.seek(self.offset)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            out.append(json.loads(line))
                        except Exception:
                            pass
                self.offset = f.tell()
        except Exception:
            pass
        return out


class SwarmBus(Static):
    """Live feed of real emitted swarm events. Call pump() to ingest, render() to show."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.buffer = deque(maxlen=200)
        self.tails = {k: _Tail(p) for k, p in SOURCES.items()}
        self.counts = {}

    def pump(self):
        for source, tail in self.tails.items():
            for r in tail.new():
                ev = _map(source, r)
                if ev:
                    actor, verb, detail, kind = ev
                    self.counts[actor] = self.counts.get(actor, 0) + 1
                    self.buffer.append({"ts": r.get("ts", ""), "actor": actor,
                                        "verb": verb, "detail": detail, "kind": kind})

    def render(self):
        t = Text()
        t.append("  ⇄ SWARM CONVERSATION BUS  ", "bold deep_sky_blue1")
        t.append("real emitted events — not invented dialogue\n", "grey42")
        if self.counts:
            t.append("  ")
            for a, n in self.counts.items():
                t.append(f"{a}:{n}  ", ACTOR_STYLE.get(a, "grey62"))
            t.append("\n")
        t.append("\n")
        rows = list(self.buffer)[-38:]
        if not rows:
            t.append("  (bus quiet — no new runtime events since open)\n", "grey42")
        for e in rows:
            ts = str(e["ts"])[11:19] if len(str(e["ts"])) >= 19 else ""
            t.append(f"  {ts:<8} ", "grey37")
            t.append(f"{e['actor']:<9} ", ACTOR_STYLE.get(e["actor"], "grey62"))
            t.append(f"{e['verb']:<20} ", KIND_STYLE.get(e["kind"], "white"))
            t.append(f"{_short(e['detail'])}\n", "grey58")
        return t


if __name__ == "__main__":
    import time
    from rich.console import Console
    b = SwarmBus()
    con = Console()
    for _ in range(3):
        b.pump()
        time.sleep(2)
    con.print(b.render())
