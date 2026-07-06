#!/usr/bin/env python3
"""HOCH fleet audit — enumerate EVERY autonomous runtime on this machine, classify it, and flag
overlaps so competing loops can be reconciled.

The per-component agent audit only saw the factories/orchestrator/swarm this project added. This one
reads the real `launchctl list`, so it sees the whole existing fleet (mesh, family, phase, trackers,
CI, the pre-existing swarms/executors) and tells the truth about how many autonomous runtimes are
actually live — and which ones duplicate each other.

Run on the Mac (needs launchctl). No fabrication: RUNNING = has a live PID; LOADED = registered but
not currently running.
"""
import json
import re
import subprocess
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "prompt_brain" / "fleet_audit.json"

# label pattern -> functional class
CLASS = [
    (r"\.mesh|mesh-broker", "MESH"),
    (r"\.family", "FAMILY (Pods)"),
    (r"live-swarm|cyber|\.swarm\.|swarm\.runtime", "SWARM/SECURITY"),
    (r"autonomous-audit|agent_audit|\.audit", "AUDIT"),
    (r"autonomous\.executor|autopulse|tool\.bridge|\.daemon|factory\.tick|cadence", "EXECUTOR/CADENCE"),
    (r"runtime|\.api|console|event\.server|pert-server|sidecar", "RUNTIME/API"),
    (r"tracker|actions\.runner|e2e|\.ci|burnin", "CI/TRACKER"),
    (r"memory", "MEMORY"),
    (r"health|watchdog|supervisor|gowatch|reconciler", "OPS/HEALTH"),
    (r"phase", "PHASE (build)"),
]

# Known overlaps introduced by this project vs the pre-existing fleet (reconcile these).
OVERLAPS = {
    "SWARM/SECURITY": ["com.hoch.live-swarm", "com.hoch.phase72a.cyber.rag", "cyber_swarm (new)"],
    "EXECUTOR/CADENCE": ["com.hoch.agent.autonomous.executor", "com.hoch.phase73b.factory.tick",
                          "com.hoch.daemon (new)", "com.hoch.brain.cadence (retired)"],
    "AUDIT": ["com.hochmesh.autonomous-audit", "agent_audit + self_heal (new)"],
}


def _classify(label):
    for rx, c in CLASS:
        if re.search(rx, label):
            return c
    return "OTHER"


def audit():
    try:
        raw = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=20).stdout
    except Exception as e:
        return {"error": f"launchctl unavailable ({e}) — run this on the Mac"}
    running, loaded, by_class = [], [], {}
    for line in raw.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, status, label = parts
        if "hoch" not in label.lower():
            continue
        cls = _classify(label)
        rec = {"label": label, "pid": pid if pid != "-" else None, "status": status, "class": cls}
        (running if pid != "-" else loaded).append(rec)
        by_class.setdefault(cls, {"running": 0, "loaded": 0})
        by_class[cls]["running" if pid != "-" else "loaded"] += 1

    out = {
        "schema": "hoch-fleet-audit-v1",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "totals": {"running": len(running), "loaded": len(loaded), "fleet": len(running) + len(loaded)},
        "by_class": by_class,
        "overlaps_to_reconcile": OVERLAPS,
        "running": sorted(running, key=lambda r: r["class"]),
        "loaded": sorted(loaded, key=lambda r: r["class"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    a = audit()
    if "error" in a:
        print(a["error"]); raise SystemExit(1)
    t = a["totals"]
    print(f"HOCH FLEET — {t['running']} RUNNING · {t['loaded']} loaded · {t['fleet']} total")
    print("  by class (running/loaded):")
    for c, n in sorted(a["by_class"].items(), key=lambda x: -x[1]["running"]):
        print(f"    {c:20} {n['running']:>2} / {n['loaded']:>2}")
    print("  OVERLAPS to reconcile (competing loops — pick one source of truth per row):")
    for c, items in a["overlaps_to_reconcile"].items():
        print(f"    {c}: {', '.join(items)}")
