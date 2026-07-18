#!/usr/bin/env python3
"""HELM — the single front door to the continuously-running runtime.

    python helm.py            # STATUS (default): honest, read-only runtime truth
    python helm.py status     # same
    python helm.py up          # supervise the founder-facing services (lights on)
    python helm.py up --autonomous   # ALSO run the executive loop (engineering work)
    python helm.py doctor      # diagnose why the independent observer says CONTRADICTED

WHY THIS FILE EXISTS
--------------------
For two years the runtime was real but *scattered*: a launchd plist booting one
FastAPI app, a bash `helm_autoloop.sh` keeping another API + a build runner alive,
a council daemon (`scripts/council/run_helm_council_daemon.py`) that is the true
executive loop but is wired to no autostart, and three FastAPI services on three
ports. There was no one command that says "boot HELM and keep it running."

This is that command. It does NOT reimplement any of it — it *reuses the proven
pieces*:
  * founder cockpit / Mission Control API  -> backend.helm_live_api  (:8770, TLS)
  * executive loop (scheduler + ConMon + QA) -> scripts/council/run_helm_council_daemon
  * independent observer (truth vs ledgers)   -> coordination/jspace/health.json

DOCTRINE HELD
-------------
  * NO FAKE GREEN. `status` reports what the evidence shows — including that
    HELM's own observer currently says CONTRADICTED / WITHHOLD_PROMOTION. It never
    dresses a failing state as green.
  * VERIFY-FIRST. The default (`status`) is read-only and starts nothing.
  * IDEMPOTENT. `up` never double-spawns a service that is already listening, so
    it composes with the existing launchd/autoloop supervision instead of fighting
    it (one runtime, not a rival — Founding Principle #3).
  * FOUNDER GATE. The autonomous executive loop *acts* (it dispatches engineering
    work). It stays $0/local-first/fail-closed via the gateway policy, but because
    it acts it is gated behind an explicit `--autonomous` flag — `up` alone only
    keeps the dashboard reachable.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import ssl
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ---- proven surfaces we reuse (paths, never re-implemented) -----------------
GOAL_STATE = ROOT / "coordination" / "goal" / "goal_state.json"
EXEC_MISSION = ROOT / "coordination" / "goal" / "executive_mission.json"
JSPACE_HEALTH = ROOT / "coordination" / "jspace" / "health.json"
COUNCIL_HEARTBEAT = ROOT / "coordination" / "council" / "council_heartbeat.jsonl"
LOOP_METRICS = ROOT / "coordination" / "council" / "loop_metrics.json"
HELM_HEARTBEAT = ROOT / "coordination" / "council" / "helm_entrypoint_heartbeat.json"
LOOP_PIDFILE = Path("/tmp/helm_executive_loop.pid")

HELM_CERT = Path.home() / ".helm" / "dev_certs" / "helm_dev_cert.pem"
HELM_KEY = Path.home() / ".helm" / "dev_certs" / "helm_dev_key.pem"

# Founder-facing services. `probe` is a cheap liveness URL; `start` is how we boot
# it if (and only if) it is down. We reuse the exact invocations the repo already
# proved in scripts/helm_autoloop.sh and start_has_runtime.sh.
SERVICES = {
    "mission_control_api": {
        "port": 8770,
        "probe": "https://127.0.0.1:8770/api/v1/helm/health",
        "tls": True,
        "start": [
            sys.executable, "-m", "uvicorn", "backend.helm_live_api:app",
            "--host", "127.0.0.1", "--port", "8770",
            "--ssl-certfile", str(HELM_CERT), "--ssl-keyfile", str(HELM_KEY),
        ],
        "role": "Founder cockpit /founder, /overview, /council  (the screen Michael watches)",
    },
    "control_api": {
        "port": 8000,
        "probe": "http://127.0.0.1:8000/",
        "tls": False,
        "start": [
            sys.executable, "-m", "uvicorn", "backend.main:app",
            "--host", "127.0.0.1", "--port", "8000",
        ],
        "role": "Control API + React shell (launchd-supervised today)",
    },
}

_TLS = ssl.create_default_context()
_TLS.check_hostname = False
_TLS.verify_mode = ssl.CERT_NONE


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _probe(url: str, tls: bool, timeout: float = 4.0) -> tuple[bool, str]:
    try:
        ctx = _TLS if tls else None
        r = urllib.request.urlopen(url, timeout=timeout, context=ctx)
        return True, f"HTTP {r.status}"
    except Exception as e:  # timeout, refused, TLS — all mean "not serving cleanly"
        return False, f"{type(e).__name__}"


def _age_seconds(iso_ts: str) -> float | None:
    try:
        t = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:
        return None


def _last_heartbeat() -> dict | None:
    try:
        line = None
        with open(COUNCIL_HEARTBEAT, "rb") as f:
            for line in f:
                pass
        return json.loads(line.decode("utf-8")) if line else None
    except Exception:
        return None


# ============================================================================
# STATUS  — verify-first, read-only, no fake green
# ============================================================================
def cmd_status() -> int:
    print(f"\n  HELM RUNTIME STATUS   {_now()}\n  " + "─" * 58)

    # 1. Services
    print("\n  SERVICES")
    up = {}
    for name, s in SERVICES.items():
        ok, detail = _probe(s["probe"], s["tls"])
        up[name] = ok
        mark = "● UP  " if ok else "○ DOWN"
        print(f"    {mark}  :{s['port']:<5} {name:<20} {detail}")
        print(f"            {s['role']}")

    # 2. Executive loop liveness (the thing that does engineering work)
    print("\n  EXECUTIVE LOOP  (scheduler → governed dispatch → validators)")
    hb = _last_heartbeat()
    if not hb:
        print("    ○  no heartbeat found — executive loop has never run or log is absent")
        loop_live = False
    else:
        age = _age_seconds(hb.get("ts", ""))
        fresh = age is not None and age < 180
        loop_live = fresh and hb.get("state") != "ERROR"
        mark = "●" if loop_live else "○"
        age_s = f"{int(age)}s ago" if age is not None else "unknown age"
        print(f"    {mark}  cycle {hb.get('cycle','?')}  state={hb.get('state','?')}  ({age_s})")
        if hb.get("state") == "ERROR":
            print(f"       last cycle ERROR: {str(hb.get('error',''))[:80]}")
        if not fresh:
            print("       heartbeat is STALE → the loop is not currently running")

    # Continuous instrumentation — detect degradation before it becomes a failure.
    lm = _read_json(LOOP_METRICS)
    if lm:
        c = lm.get("cycles", {})
        mi = lm.get("missions", {})
        lc = lm.get("lock_contention", {})
        h = lm.get("health", {})
        hstate = h.get("state", "UNKNOWN")
        hmark = {"HEALTHY": "●", "DEGRADED": "◐", "AT_RISK": "✗"}.get(hstate, "○")
        print(f"       telemetry   uptime {lm.get('uptime_seconds', 0)}s · boots {lm.get('boot_count', '?')} · "
              f"cycles {c.get('total', 0)} (idle {c.get('idle', 0)}/active {c.get('active', 0)}/err {c.get('error', 0)})")
        print(f"       throughput  {mi.get('throughput_per_min', 0)} missions/min · "
              f"passed {mi.get('passed', 0)} · failed {mi.get('failed', 0)}")
        print(f"       contention  {lc.get('retries_total', 0)} lock-retries · {lc.get('wait_seconds_total', 0)}s waited on locks")
        print(f"       {hmark} loop health {hstate}  ({'; '.join(h.get('reasons', []))})")

    # 3. GOAL / mission truth (control object + derived scoreboard)
    print("\n  MISSION")
    em = _read_json(EXEC_MISSION) or {}
    gs = _read_json(GOAL_STATE) or {}
    mission = (em.get("mission") or {})
    print(f"    mission        {mission.get('id','?')}  ({mission.get('name','?')})")
    print(f"    op status      {em.get('operational_status','UNKNOWN')}")
    metrics = gs.get("metrics", {})
    print(f"    north star     {metrics.get('north_star_completion','UNKNOWN')}% "
          f"| autonomy coverage {metrics.get('autonomous_execution_coverage','UNKNOWN')}%")
    print(f"    blocker        {metrics.get('current_critical_path_blocker','—')}")

    # 4. THE INDEPENDENT OBSERVER — this is the anti-fake-green truth
    print("\n  INDEPENDENT OBSERVER  (coordination/jspace/health.json)")
    jh = _read_json(JSPACE_HEALTH) or {}
    overall = jh.get("overall", "UNKNOWN")
    findings = jh.get("unresolved_findings", jh.get("open_findings", "?"))
    action = jh.get("recommended_action", "UNKNOWN")
    contradicted = str(overall).upper() == "CONTRADICTED"
    mark = "✗" if contradicted else ("●" if str(overall).upper() in ("CONSISTENT", "CLEAN") else "○")
    print(f"    {mark}  overall={overall}  action={action}  unresolved_findings={findings}")

    # 5. Honest one-line verdict
    print("\n  VERDICT")
    all_services = all(up.values())
    if contradicted:
        print("    ⚠  UP but NOT verified-clean. HELM's own observer says CONTRADICTED /")
        print("       WITHHOLD_PROMOTION. Reporting this GREEN would be fake green.")
        print("       → run `python helm.py doctor` to see the root cause.")
    elif all_services and loop_live:
        print("    ●  RUNNING and observer-consistent.")
    else:
        gaps = []
        if not all_services:
            gaps.append("a service is down")
        if not loop_live:
            gaps.append("executive loop is not running")
        print(f"    ○  Partially up: {', '.join(gaps)}.  `python helm.py up --autonomous` to engage.")
    print()
    return 0


# ============================================================================
# DOCTOR — diagnose the CONTRADICTED gap (read-only)
# ============================================================================
def cmd_doctor() -> int:
    print(f"\n  HELM DOCTOR   {_now()}\n  " + "─" * 58)
    jh = _read_json(JSPACE_HEALTH) or {}
    print(f"\n  observer.overall = {jh.get('overall')}   action = {jh.get('recommended_action')}")
    print(f"  unresolved_findings = {jh.get('unresolved_findings', jh.get('open_findings'))}")

    # Surface the alerts / contradiction detail the observer recorded.
    for key in ("alerts", "contradictions", "signals", "detail", "reasons"):
        val = jh.get(key)
        if val:
            print(f"\n  {key}:")
            txt = json.dumps(val, indent=2)
            for ln in txt.splitlines()[:24]:
                print(f"    {ln}")

    # The known structural cause: the canonical lease-ledger pointer vs the dir the
    # running scheduler actually writes to (persistent_scheduler.py evidence_dir).
    print("\n  POINTER CHECK  (lease/dispatch ledger the observer reconciles against)")
    daemon_dir = ROOT / "coordination" / "council" / "daemon"
    mock_dir = ROOT / "coordination" / "council" / "live_proof_packages" / "HELM-24X7-MOCK"
    for d in (daemon_dir, mock_dir):
        lease = d / "task_lease_ledger.jsonl"
        print(f"    {'exists' if lease.exists() else 'MISSING'}  {lease.relative_to(ROOT)}")
    print("\n    → If the observer's canonical pointer names a ledger path that is MISSING,")
    print("      the fix is to reconcile the pointer with the dir the live scheduler writes")
    print("      (backend/mission_control/persistent_scheduler.py evidence_dir), not to")
    print("      suppress the finding. This is the first thing to close before claiming green.")
    print()
    return 0


# ============================================================================
# UP — idempotent supervisor: ensure services (and optionally the loop) run
# ============================================================================
class Supervisor:
    def __init__(self, autonomous: bool):
        self.autonomous = autonomous
        self.children: dict[str, subprocess.Popen] = {}
        self.running = True
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, *_):
        print("\n[helm] shutdown requested — stopping children we started …", flush=True)
        self.running = False
        for name, p in list(self.children.items()):
            if p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=5)
                except Exception:
                    p.kill()

    def _ensure_service(self, name: str, s: dict):
        ok, _ = _probe(s["probe"], s["tls"], timeout=4.0)
        if ok:
            return  # already served by launchd/autoloop — never double-spawn (Principle #3)
        if name in self.children and self.children[name].poll() is None:
            return
        if s["tls"] and not (HELM_CERT.exists() and HELM_KEY.exists()):
            print(f"[helm] {name}: TLS cert/key absent at ~/.helm/dev_certs — skipping (founder sets up TLS)", flush=True)
            return
        print(f"[helm] {name} down → starting on :{s['port']}", flush=True)
        self.children[name] = subprocess.Popen(
            s["start"], cwd=str(ROOT),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def _ensure_loop(self):
        if not self.autonomous:
            return
        # singleton via pidfile so we compose with any existing daemon
        if LOOP_PIDFILE.exists():
            try:
                pid = int(LOOP_PIDFILE.read_text())
                os.kill(pid, 0)
                return  # already alive
            except Exception:
                pass
        if "executive_loop" in self.children and self.children["executive_loop"].poll() is None:
            return
        print("[helm] executive loop not running → launching council daemon (LOCAL_ONLY, $0)", flush=True)
        p = subprocess.Popen(
            [sys.executable, "scripts/council/run_helm_council_daemon.py", "--interval", "20"],
            cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.children["executive_loop"] = p
        try:
            LOOP_PIDFILE.write_text(str(p.pid))
        except Exception:
            pass

    def _heartbeat(self):
        status = {n: ("RUNNING" if p.poll() is None else f"STOPPED({p.poll()})")
                  for n, p in self.children.items()}
        HELM_HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        try:
            HELM_HEARTBEAT.write_text(json.dumps({
                "ts": _now(), "supervisor_pid": os.getpid(),
                "autonomous": self.autonomous,
                "children_started_by_helm": status,
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    def run(self) -> int:
        mode = "autonomous (executive loop engaged)" if self.autonomous else "lights-on (dashboard only)"
        print(f"[helm] up — {mode}. Ctrl-C to stop. Reusing anything already running.", flush=True)
        while self.running:
            for name, s in SERVICES.items():
                self._ensure_service(name, s)
            self._ensure_loop()
            self._heartbeat()
            for _ in range(50):  # ~5s, responsive to SIGINT
                if not self.running:
                    break
                time.sleep(0.1)
        print("[helm] supervisor stopped.", flush=True)
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="helm", description="HELM runtime front door")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status", help="honest read-only runtime truth (default)")
    sub.add_parser("doctor", help="diagnose the CONTRADICTED observer gap")
    up = sub.add_parser("up", help="supervise services; --autonomous also runs the executive loop")
    up.add_argument("--autonomous", action="store_true",
                    help="engage the engineering loop (LOCAL_ONLY/$0/fail-closed; it ACTS, so it is gated)")
    args = ap.parse_args()

    if args.cmd in (None, "status"):
        return cmd_status()
    if args.cmd == "doctor":
        return cmd_doctor()
    if args.cmd == "up":
        return Supervisor(autonomous=args.autonomous).run()
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
