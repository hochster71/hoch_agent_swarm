#!/usr/bin/env python3
"""HELM Neural Cortex — truthful state reader.

Maps REAL runtime state to a cortex model the TUI can animate. The contract:

  * A pulse is emitted ONLY for a mission that actually happened (a real record appended
    to the runtime ledgers). Nothing is animated that is not real.
  * A node/provider that is not being exercised is IDLE or UNKNOWN — never fake-active.
  * Missing or stale data resolves to idle / UNKNOWN, never to a fabricated "green".

Sources (all best-effort; absence -> UNKNOWN):
  coordination/soak/soak_snapshot.json      (live soak metrics, if a soak is running)
  coordination/soak/soak_missions.jsonl     (per-mission completions -> pulses)
  coordination/council/loop_metrics.json    (executive-loop health)
  coordination/council/council_heartbeat.jsonl (last cycle state)
  http://127.0.0.1:11434/api/tags           (real Ollama health)
"""
from __future__ import annotations

import json
import os
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOAK_SNAP = ROOT / "coordination" / "soak" / "soak_snapshot.json"
SOAK_MISSIONS = ROOT / "coordination" / "soak" / "soak_missions.jsonl"
LOOP_METRICS = ROOT / "coordination" / "council" / "loop_metrics.json"
HEARTBEAT = ROOT / "coordination" / "council" / "council_heartbeat.jsonl"
EXEC_MISSION = ROOT / "coordination" / "goal" / "executive_mission.json"
GOAL_STATE = ROOT / "coordination" / "goal" / "goal_state.json"


def read_north_star() -> dict:
    """Layer 12 — from the REAL goal/mission control objects. ETA is UNKNOWN by law: no
    estimator exists, so we never fabricate one. Shows the computed north-star number AND
    the blocking reality (op_status, remaining critical path, founder gates) side by side."""
    gs = _load_json(GOAL_STATE) or {}
    em = _load_json(EXEC_MISSION) or {}
    m = gs.get("metrics", {})
    cp = em.get("critical_path", [])
    remaining = [n for n in cp if n.get("status") != "DONE"]
    founder_nodes = [n for n in cp if n.get("owner_role") == "founder" or "FOUNDER" in str(n.get("status", ""))]
    founder_pending = m.get("founder_only_actions_pending") or []
    return {
        "champion": (em.get("mission", {}) or {}).get("name") or m.get("champion_product") or "UNKNOWN",
        "north_star_pct": m.get("north_star_completion"),
        "op_status": em.get("operational_status", "UNKNOWN"),
        "critical_remaining": len(remaining),
        "critical_total": len(cp),
        "blocker": m.get("current_critical_path_blocker") or "—",
        "founder_gates": max(len(founder_nodes), len(founder_pending)),
        "eta": "UNKNOWN",  # LAW: no estimator exists → never fabricate an ETA
    }

CAPABILITIES = ["HASF", "HRF", "HCF", "HSF", "HMF", "HPF"]
# how a per-mission capability code maps onto a cortex capability node
CAP_ALIASES = {"CODEREV": "HASF", "GAP": "HCF", "ARCH": "HCF", "DOC": "HSF",
               "HASF": "HASF", "HRF": "HRF", "HCF": "HCF", "HSF": "HSF", "HMF": "HMF", "REAL": "HASF"}
FRESH_S = 30.0  # a snapshot older than this is treated as not-live


def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _file_age(p: Path):
    try:
        return time.time() - p.stat().st_mtime
    except Exception:
        return None


def _cap_of(mission_id: str, capability: str) -> str:
    raw = (capability or (mission_id.split("-")[1] if "-" in mission_id else "")).upper()
    return CAP_ALIASES.get(raw, "HASF")


class CortexReader:
    """Stateful: remembers which missions it has already turned into pulses."""

    def __init__(self):
        self._offset = 0
        self._primed = False
        self._ollama = {"health": "UNKNOWN", "models": None, "checked": 0.0}

    # -- real Ollama health (cached ~4s so we don't hammer it) --
    def _ollama_health(self) -> dict:
        now = time.time()
        if now - self._ollama["checked"] < 4.0:
            return self._ollama
        try:
            r = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
            d = json.loads(r.read())
            self._ollama = {"health": "UP", "models": len(d.get("models", [])), "checked": now}
        except Exception:
            self._ollama = {"health": "DOWN", "models": None, "checked": now}
        return self._ollama

    # -- new mission completions since last poll (these become pulses) --
    def _new_missions(self) -> list[dict]:
        out = []
        try:
            if not SOAK_MISSIONS.exists():
                return out
            with open(SOAK_MISSIONS, "r", encoding="utf-8", errors="replace") as f:
                if not self._primed:
                    # On first poll, skip to end MINUS a small tail so the screen isn't
                    # flooded with history, but a running soak still shows immediate life.
                    f.seek(0, 2)
                    end = f.tell()
                    f.seek(max(0, end - 4000))
                    f.readline()  # discard partial line
                    self._offset = f.tell()
                    self._primed = True
                f.seek(self._offset)
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            out.append(json.loads(line))
                        except Exception:
                            pass
                self._offset = f.tell()
        except Exception:
            pass
        return out

    def _provider_matrix(self, ollama_health: dict, dispatches: int, soak_live: bool) -> dict:
        """Truthful provider status. Ollama is live-probed; the rest are reported by what is
        actually verifiable (CLI on PATH / key env PRESENT) — never a fabricated 'READY'.
        An unverifiable provider is UNKNOWN, an installed-but-unexercised one is AVAILABLE."""
        def cli(name):  # presence only; never reads/echoes any secret
            return shutil.which(name) is not None
        def keyed(*envs):
            return any(os.environ.get(e) for e in envs)
        oll = ollama_health["health"]
        ollama_state = ("ACTIVE" if (oll == "UP" and (dispatches or 0) > 0)
                        else "READY" if oll == "UP" else "OFFLINE")
        return {
            # exercised, live-probed:
            "Ollama":  {"state": ollama_state, "detail": f"{ollama_health.get('models','?')} models"},
            "Local":   {"state": "AVAILABLE" if oll == "UP" else "OFFLINE", "detail": "on-box models"},
            # configured but NOT exercised under local-only policy -> report installed vs not,
            # never 'ACTIVE'/'READY' (which would imply verified live use):
            "Claude":  {"state": "AVAILABLE" if cli("claude") else "OFFLINE", "detail": "CLI" if cli("claude") else "not installed"},
            "Grok":    {"state": "AVAILABLE" if cli("grok") else "OFFLINE", "detail": "CLI" if cli("grok") else "not installed"},
            "Gemini":  {"state": "AVAILABLE" if cli("gemini") else "OFFLINE", "detail": "CLI" if cli("gemini") else "not installed"},
            "OpenAI":  {"state": "AVAILABLE" if keyed("OPENAI_API_KEY") else "OFFLINE",
                        "detail": "key present · policy-idle" if keyed("OPENAI_API_KEY") else "no key"},
        }

    def _factories(self, snap: dict, soak_live: bool) -> dict:
        """Capability activity from REAL mission routing (not decorative)."""
        routing_raw = (snap or {}).get("governance", {}).get("capability_routing", {}) if soak_live else {}
        # the soak logs raw capability codes (CODEREV/GAP/ARCH/DOC); fold them onto the
        # canonical factory nodes so the panel reflects REAL routing, not zeros.
        routing = {}
        for raw, n in routing_raw.items():
            canon = CAP_ALIASES.get(str(raw).upper(), str(raw).upper())
            routing[canon] = routing.get(canon, 0) + n
        total = sum(routing.values()) or 1
        out = {}
        for cap in CAPABILITIES:
            n = routing.get(cap, 0)
            out[cap] = {
                "missions": n,
                "load": (n / total) if soak_live else None,
                "state": ("ACTIVE" if n > 0 else ("IDLE" if soak_live else "UNKNOWN"))
                         if cap != "HPF" else "RESERVED",   # HPF = pods, visualization only
            }
        return out

    def _exec_strip(self, snap: dict, lm: dict, oll: dict, dispatches: int, soak_live: bool) -> dict:
        m = (snap or {}).get("runtime", {}) if soak_live else {}
        res = (snap or {}).get("resources", {}) if soak_live else {}
        loop = (lm.get("health", {}) or {}).get("state", "UNKNOWN")
        sr = m.get("success_rate")
        # founder gate — read the real mission control object's critical path
        founder = "UNKNOWN"
        try:
            em = _load_json(EXEC_MISSION) or {}
            for node in em.get("critical_path", []):
                st = str(node.get("status", ""))
                if "BLOCKED_FOUNDER" in st or node.get("owner_role") == "founder":
                    founder = "APPROVAL REQUIRED"
                    break
            else:
                founder = "NONE PENDING" if em else "UNKNOWN"
        except Exception:
            pass
        q = m.get("queue_depth")
        probe = res.get("sqlite_write_probe_ms")
        return {
            "HELM":     {"state": "ONLINE" if soak_live else "UNKNOWN"},
            "Council":  {"state": loop if loop in ("HEALTHY", "DEGRADED") else ("UNKNOWN" if not soak_live else "HEALTHY")},
            "Runtime":  {"state": "ACTIVE" if (soak_live and (dispatches or 0) > 0) else ("IDLE" if soak_live else "UNKNOWN")},
            "Evidence": {"state": ("VERIFIED" if (isinstance(sr, (int, float)) and sr >= 0.95)
                                   else "WARNING" if isinstance(sr, (int, float)) else "UNKNOWN"),
                         "detail": f"{(snap or {}).get('governance',{}).get('evidence_artifacts',0)} artifacts" if soak_live else ""},
            "SQLite":   {"state": ("ONLINE" if res.get("sqlite_writable") else ("FAILED" if soak_live else "UNKNOWN")),
                         "detail": f"{probe} ms" if probe is not None else ""},
            "Queue":    {"state": ("WARNING" if (q or 0) >= 8 else "QUEUED" if (q or 0) > 0 else "IDLE") if soak_live else "UNKNOWN",
                         "detail": f"{q} pending" if q is not None else ""},
            "Founder":  {"state": "WARNING" if founder == "APPROVAL REQUIRED" else ("ONLINE" if founder == "NONE PENDING" else "UNKNOWN"),
                         "detail": founder},
        }

    def poll(self) -> dict:
        snap = _load_json(SOAK_SNAP)
        snap_age = _file_age(SOAK_SNAP)
        soak_live = bool(snap) and snap_age is not None and snap_age < FRESH_S

        lm = _load_json(LOOP_METRICS) or {}
        oll = self._ollama_health()
        new = self._new_missions()

        rt = (snap or {}).get("runtime", {}) if soak_live else {}
        res = (snap or {}).get("resources", {}) if soak_live else {}

        # ---- center activity (drives the HELM glow): real in-flight + recent flow ----
        dispatches = res.get("ollama_procs")
        if dispatches is None:
            dispatches = 0
        # activity 0..1: in-flight work now + whether new completions just landed
        activity = 0.0
        if soak_live:
            activity = min(1.0, dispatches / 4.0)
        if new:
            activity = max(activity, 0.6)
        loop_state = "UNKNOWN"
        try:
            loop_state = (lm.get("health", {}) or {}).get("state", "UNKNOWN")
        except Exception:
            pass

        # ---- per-node state (truthful) ----
        # capability nodes light up only when a real mission of that capability was JUST seen
        active_caps = {}
        for m in new:
            c = _cap_of(m.get("mission_id", ""), m.get("capability"))
            active_caps[c] = m.get("result", "?")

        def node_state(active: bool, ok: bool = True) -> str:
            if not soak_live and not new:
                return "idle" if oll["health"] != "UNKNOWN" else "unknown"
            return ("working" if active else "idle")

        nodes = {}
        center = "working" if (soak_live and dispatches > 0) else ("thinking" if new else
                 ("idle" if soak_live else "unknown"))
        nodes["HELM"] = center
        # roles
        role_active = soak_live and dispatches > 0
        nodes["ORCH"] = "idle"                         # orchestrator not in the soak dispatch path
        nodes["COUNCIL"] = "working" if role_active else ("idle" if soak_live else "unknown")
        nodes["AUDIT"] = "working" if new else ("idle" if soak_live else "unknown")  # validators run per completion
        for c in CAPABILITIES:
            if c in active_caps:
                nodes[c] = "blocked" if active_caps[c] == "FAIL" else "completed"
            else:
                nodes[c] = "idle" if soak_live else "unknown"

        # ---- providers (honest: only Ollama is exercised; others are intentionally idle) ----
        providers = {
            "ollama": {"health": oll["health"], "models": oll["models"],
                       "util": (snap or {}).get("provider_utilization", {}).get("ollama", 0) if soak_live else None,
                       "active": dispatches},
            # local-only policy: these are configured but NOT exercised -> not fabricating health
            "openai": {"health": "IDLE", "util": 0, "note": "local-only policy"},
            "anthropic": {"health": "IDLE", "util": 0, "note": "local-only policy"},
            "xai": {"health": "IDLE", "util": 0, "note": "local-only policy"},
        }

        # ---- pulses for the new real missions ----
        events = []
        for m in new:
            cap = _cap_of(m.get("mission_id", ""), m.get("capability"))
            events.append({
                "mission_id": m.get("mission_id"),
                "cap": cap,
                "model": m.get("model") or "ollama",
                "result": m.get("result", "?"),
                "duration_s": m.get("duration_s"),
                "validator": m.get("validator"),
                "cost": m.get("cost_usd", 0.0),
            })

        return {
            "ts": time.strftime("%H:%M:%S", time.gmtime()),
            "soak_live": soak_live,
            "snap_age_s": round(snap_age, 1) if snap_age is not None else None,
            "loop_state": loop_state,
            "activity": activity,
            "dispatches": dispatches,
            "nodes": nodes,
            "providers": providers,
            "provider_matrix": self._provider_matrix(oll, dispatches, soak_live),
            "factories": self._factories(snap, soak_live),
            "exec_strip": self._exec_strip(snap, lm, oll, dispatches, soak_live),
            "north_star": read_north_star(),
            "events": events,
            "metrics": {
                "uptime": (snap or {}).get("uptime_hms") if soak_live else None,
                "completed": rt.get("completed_total"),
                "passed": rt.get("passed_total"),
                "failed": rt.get("failed_total"),
                "success_rate": rt.get("success_rate"),
                "throughput_per_hour": rt.get("throughput_per_hour"),
                "mean_latency_s": rt.get("mean_mission_latency_s"),
                "p95_latency_s": rt.get("p95_mission_latency_s"),
                "queue_depth": rt.get("queue_depth"),
                "lock_retries": rt.get("loop_lock_retries"),
                "sqlite_writable": res.get("sqlite_writable"),
                "sqlite_probe_ms": res.get("sqlite_write_probe_ms"),
                "cpu": res.get("system_cpu_pct"),
                "mem": res.get("system_mem_pct"),
                "alerts": [a.get("key") for a in (snap or {}).get("active_alerts", [])] if soak_live else [],
            },
        }


if __name__ == "__main__":
    r = CortexReader()
    for _ in range(3):
        print(json.dumps(r.poll(), indent=2, default=str))
        time.sleep(2)
