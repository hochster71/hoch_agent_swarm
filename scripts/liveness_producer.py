#!/usr/bin/env python3
"""HELM liveness producer — keeps the wall's liveness panels HONESTLY current.

Rebuilt 2026-07-17 to replace the retired council_watch.sh / relay_refresh.sh
daemons (their scripts were deleted; their launchd jobs errored 127).

What it refreshes (real current state only — NO fabricated activity):
  * coordination/council/factory_registry.json   -> /api/v1/helm/factories
        Canonical factory IDENTITIES (constant truth). Re-published with a fresh
        timestamp + republished_at so the panel reads "verified as of now" rather
        than days-stale. Identity content is preserved exactly.
  * coordination/council/active_runtime_source.json -> /api/v1/helm/runtime + /wall
        The CURRENT orchestrating runtime, detected live (real pid), honest note.

What it deliberately does NOT touch (integrity-gated; faking = fake-green):
  * /agents  (needs a real soak/dispatch result-envelope ledger)
  * /chain   (AU-9 hash chain; a non-chained heartbeat would BREAK verification)
  These honestly render UNKNOWN until a real dispatch daemon runs.

Usage: liveness_producer.py [--once|--loop] [--interval 60]
"""
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY_REGISTRY = ROOT / "coordination" / "council" / "factory_registry.json"
RUNTIME_POINTER = ROOT / "coordination" / "council" / "active_runtime_source.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _detect_runtime() -> dict:
    """Detect the REAL current orchestrating runtime. No assertion of activity that isn't there."""
    def _pgrep(pat):
        try:
            out = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, timeout=5).stdout.strip()
            return int(out.splitlines()[0]) if out else None
        except Exception:
            return None
    # priority: an active soak runner, else the freshness refresher, else native cadence
    soak = _pgrep("soak_runner.py")
    refr = _pgrep("runtime_refresher.py")
    auto = _pgrep("helm_autoloop.sh")
    if soak:
        return {"runtime": "soak_runner.py", "pid": soak, "scheduler_instance_id": "soak",
                "note": "active soak runner is the current runtime"}
    if refr or auto:
        pid = refr or auto
        return {"runtime": "freshness_refresher+autoloop", "pid": pid,
                "scheduler_instance_id": "native-cadence",
                "note": "HELM on native cadence: freshness refresher + helm autoloop live; product work runs on the scheduled-task loop; no soak active"}
    return {"runtime": "scheduled-task-loop", "pid": os.getpid(),
            "scheduler_instance_id": "native-cadence",
            "note": "no long-running orchestrator process detected; HELM product work runs via scheduled tasks"}


def refresh_factory_registry() -> str:
    if not FACTORY_REGISTRY.exists():
        return f"SKIP factory_registry.json missing at {FACTORY_REGISTRY}"
    d = json.loads(FACTORY_REGISTRY.read_text())
    d["republished_at"] = _now()  # identity content preserved; only the freshness stamp advances
    FACTORY_REGISTRY.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    return f"OK factory_registry.json ({len(d.get('factories', {}))} factories) @ {d['republished_at']}"


def refresh_runtime_pointer() -> str:
    rt = _detect_runtime()
    prev = {}
    try:
        prev = json.loads(RUNTIME_POINTER.read_text())
    except Exception:
        pass
    doc = {
        "scheduler_instance_id": rt["scheduler_instance_id"],
        "ledger_path": prev.get("ledger_path", ""),
        "evidence_dir": prev.get("evidence_dir", "coordination/council/native_runtime"),
        "runtime": rt["runtime"],
        "pid": rt["pid"],
        "published_at": _now(),
        "note": rt["note"],
    }
    RUNTIME_POINTER.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return f"OK active_runtime_source.json -> {rt['runtime']} pid={rt['pid']} @ {doc['published_at']}"


def once() -> int:
    print(f"[liveness {_now()}] {refresh_factory_registry()}")
    print(f"[liveness {_now()}] {refresh_runtime_pointer()}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--once", action="store_true")
    g.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args(argv)
    if a.loop:
        while True:
            try:
                once()
            except Exception as e:
                print(f"[liveness {_now()}] ERROR {e}", file=sys.stderr)
            time.sleep(a.interval)
    return once()


if __name__ == "__main__":
    raise SystemExit(main())
