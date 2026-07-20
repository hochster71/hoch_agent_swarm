#!/usr/bin/env python3
"""Governed operational soak: sustained autonomous-operation validation for HELM.

Runs the executive loop (council daemon) continuously against a BOUNDED queue of REAL,
evidence-driven missions, while measuring runtime / resources / governance every sample and
detecting degradation automatically. Produces per-mission records and a live snapshot for
the Operational Readiness dashboard. Optimizes for TRUTH, not green.

  python scripts/soak/run_soak.py --hours 6            # or --minutes N for a bounded run
  # stop early: Ctrl-C / SIGTERM (writes the final report on exit)

Reuses (does not reinvent): run_helm_council_daemon (executive loop), the scheduler ledgers,
factory_validators, loop_metrics, and mission_generator.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socketserver
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DB = ROOT / "backend" / "swarm_ledger.db"
DAEMON_DIR = ROOT / "coordination" / "council" / "daemon"
SOAK_DIR = ROOT / "coordination" / "soak"
SOAK_DIR.mkdir(parents=True, exist_ok=True)

from scripts.soak import mission_generator as gen

METRICS = SOAK_DIR / "soak_metrics.jsonl"
MISSIONS = SOAK_DIR / "soak_missions.jsonl"
ALERTS = SOAK_DIR / "soak_alerts.jsonl"
SNAPSHOT = SOAK_DIR / "soak_snapshot.json"
RUNS_DIR = SOAK_DIR / "runs"
PREV_VALIDATION_RUN = RUNS_DIR / "run-VALIDATION-31min-2026-07-18T2154Z"

# Bounded-queue watermarks and cadences
LOW_WATER = int(os.getenv("SOAK_LOW_WATER", "3"))
HIGH_WATER = int(os.getenv("SOAK_HIGH_WATER", "8"))
FEED_INTERVAL = int(os.getenv("SOAK_FEED_INTERVAL", "20"))
SAMPLE_INTERVAL = int(os.getenv("SOAK_SAMPLE_INTERVAL", "10"))
DASH_PORT = int(os.getenv("SOAK_DASH_PORT", "8790"))

_stop = threading.Event()
_hard_stop = threading.Event()  # tripped on a data-integrity / unknown terminal-state anomaly
# Every status the scheduler is allowed to produce. Anything else is a terminal-state bug.
KNOWN_TASK_STATES = {"PENDING", "RUNNING", "COMPLETED", "FAILED",
                     "EXHAUSTED", "HELD_FOUNDER", "DENIED"}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


# --------------------------------------------------------------------------- ledger tailer
class Tailer:
    """Incrementally read newline-delimited JSON, remembering the byte offset."""
    def __init__(self, path: Path):
        self.path = path
        self.offset = 0

    def seek_end(self):
        """Skip everything already in the file. The daemon ledgers are append-only and
        contain history from prior runs; the soak must count ONLY entries appended during
        THIS run, or historical dispatches inflate every metric."""
        try:
            if self.path.exists():
                self.offset = self.path.stat().st_size
        except Exception:
            self.offset = 0

    def new_records(self):
        out = []
        try:
            if not self.path.exists():
                return out
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
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


# --------------------------------------------------------------------------- state
class SoakState:
    def __init__(self, started_mono, started_wall, daemon_pid):
        self.started_mono = started_mono
        self.started_wall = started_wall
        self.daemon_pid = daemon_pid
        self.dispatch_tail = Tailer(DAEMON_DIR / "dispatch_ledger.jsonl")
        self.dispatch_tail.seek_end()   # count only this run's dispatches, not history
        self.verify_tail = Tailer(DAEMON_DIR / "verification_ledger.jsonl")
        self.verify_tail.seek_end()
        self.verdicts = {}                 # task_id -> verdict (from verification ledger)
        self.recorded = set()              # task_ids already written to soak_missions
        self.missions = []                 # per-mission records (kept in memory for the report)
        self.retries_seen = {}             # task_id -> retry count observed
        self.recovered = 0                 # FAILED-then-COMPLETED
        self.seen_failed = set()
        self.rss_samples = []              # (elapsed_s, rss_mb)
        self.fd_samples = []               # (elapsed_s, fds)
        self.alerts_active = {}            # key -> alert dict (dedup)
        self.last_completion_mono = started_mono
        self.gen_added_total = 0

    def elapsed(self):
        return time.monotonic() - self.started_mono


# --------------------------------------------------------------------------- workers
def council_daemon_proc():
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    log = open(SOAK_DIR / "daemon.log", "a", buffering=1)
    return subprocess.Popen(
        [sys.executable, str(ROOT / "scripts" / "council" / "run_helm_council_daemon.py"),
         "--interval", os.getenv("SOAK_DAEMON_INTERVAL", "6"), "--max-cycles", "0"],
        cwd=str(ROOT), env=env, stdout=log, stderr=log)


def feeder(state: SoakState):
    while not _stop.is_set():
        try:
            added = gen.refill(LOW_WATER, HIGH_WATER)
            state.gen_added_total += added
        except Exception as e:
            _alert(state, "feeder_error", "ERROR", f"mission generator failed: {e}")
        _stop.wait(FEED_INTERVAL)


def dashboard_server():
    handler = partial(SimpleHTTPRequestHandler, directory=str(SOAK_DIR))
    try:
        with socketserver.TCPServer(("127.0.0.1", DASH_PORT), handler) as httpd:
            httpd.timeout = 1
            while not _stop.is_set():
                httpd.handle_request()
    except Exception:
        pass  # dashboard is best-effort; never blocks the soak


# --------------------------------------------------------------------------- degradation
def _alert(state: SoakState, key: str, severity: str, detail: str):
    if key in state.alerts_active:
        return  # already active/reported — do not spam
    rec = {"ts": now_iso(), "elapsed_s": round(state.elapsed(), 1),
           "key": key, "severity": severity, "detail": detail}
    state.alerts_active[key] = rec
    try:
        with open(ALERTS, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def _clear_alert(state: SoakState, key: str):
    state.alerts_active.pop(key, None)


def _slope_per_hour(samples):
    """Least-squares slope over (elapsed_s, value); returns units/hour."""
    n = len(samples)
    if n < 8:
        return 0.0
    xs = [s[0] for s in samples]; ys = [s[1] for s in samples]
    mx = sum(xs) / n; my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0
    slope_per_s = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / den
    return slope_per_s * 3600.0


def detect_degradation(state: SoakState, rt: dict, res: dict):
    # Leak detectors need a real baseline: extrapolating a per-hour slope from a few
    # minutes of warmup produces false alarms. Require >= 10 min of samples AND a
    # meaningful ABSOLUTE increase, not just a slope. Truthful alerts, not noise.
    MIN_TREND_SAMPLES = 60  # ~10 min at 10s sampling
    el = state.elapsed()
    # memory growth: sustained upward RSS slope + large absolute + relative increase
    if len(state.rss_samples) >= MIN_TREND_SAMPLES and el > 1200:
        rss_slope = _slope_per_hour(state.rss_samples)
        base = min(s[1] for s in state.rss_samples[:6])
        cur = res.get("daemon_rss_mb", 0)
        if rss_slope > 50 and cur > base + 100 and cur > base * 1.5:
            _alert(state, "memory_growth", "WARN",
                   f"daemon RSS rising ~{rss_slope:.0f} MB/h ({base:.0f}->{cur:.0f} MB)")
    # fd leak: sustained slope + absolute increase floor
    if len(state.fd_samples) >= MIN_TREND_SAMPLES and el > 1200:
        fd_slope = _slope_per_hour(state.fd_samples)
        base = min(s[1] for s in state.fd_samples[:6])
        cur = res.get("daemon_fds", 0) or 0
        if fd_slope > 20 and cur > base + 50:
            _alert(state, "fd_leak", "WARN", f"open fds rising ~{fd_slope:.0f}/h ({base}->{cur})")
    # stale queue / mission starvation: pending>0 but nothing completing
    idle_s = time.monotonic() - state.last_completion_mono
    if rt["queue_depth"] > 0 and idle_s > 600:
        _alert(state, "stale_queue", "WARN",
               f"{rt['queue_depth']} pending but no completion in {idle_s/60:.0f} min")
    else:
        _clear_alert(state, "stale_queue")
    # SQLite contention: write-probe latency high or loop lock-retries
    if res.get("sqlite_write_probe_ms", 0) > 3000:
        _alert(state, "sqlite_contention", "WARN",
               f"write-probe {res['sqlite_write_probe_ms']} ms (lock contention)")
    else:
        _clear_alert(state, "sqlite_contention")
    if rt.get("loop_lock_retries", 0) > 0:
        _alert(state, "loop_lock_retries", "INFO", f"executive-loop lock-retries={rt['loop_lock_retries']}")
    # repeated retries on a single mission
    hot = [t for t, c in state.retries_seen.items() if c >= 3]
    if hot:
        _alert(state, "repeated_retries", "WARN", f"tasks retried>=3x: {hot[:5]}")
    # provider failures / ollama health
    if not res.get("ollama_online", False):
        _alert(state, "ollama_down", "ERROR", "Ollama health check failed")
    else:
        _clear_alert(state, "ollama_down")
    # telemetry degradation: loop heartbeat stale
    if rt.get("loop_hb_age_s") is not None and rt["loop_hb_age_s"] > 120:
        _alert(state, "telemetry_stale", "WARN", f"loop telemetry {rt['loop_hb_age_s']}s stale")
    else:
        _clear_alert(state, "telemetry_stale")


# --------------------------------------------------------------------------- per-mission records
def ingest_ledgers(state: SoakState):
    for v in state.verify_tail.new_records():
        tid = v.get("task_id")
        if tid:
            state.verdicts[tid] = v.get("verdict", "UNKNOWN")
    for d in state.dispatch_tail.new_records():
        tid = d.get("task_id")
        status = d.get("status")
        if not tid:
            continue
        if status in ("PENDING", "RETRY", "DISPATCH_BINDING_MISMATCH"):
            state.retries_seen[tid] = state.retries_seen.get(tid, 0) + 1
        if status in ("COMPLETED", "FAILED") and tid not in state.recorded:
            start = d.get("started_at"); finish = d.get("ts")
            dur = None
            try:
                from datetime import datetime
                dur = (datetime.fromisoformat(finish.replace("Z", "+00:00"))
                       - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds()
            except Exception:
                pass
            cap = tid.split("-")[1] if "-" in tid else "?"
            art = ROOT / "artifacts" / "factory" / f"{tid}.md"
            verdict = state.verdicts.get(tid, "UNKNOWN")
            result = "PASS" if (status == "COMPLETED" and verdict == "PASS") else (
                "FAIL" if status == "FAILED" or verdict == "FAIL" else status)
            if status == "FAILED":
                state.seen_failed.add(tid)
            if status == "COMPLETED" and tid in state.seen_failed:
                state.recovered += 1
            rec = {
                "mission_id": tid, "capability": cap,
                "model": d.get("model") or "ollama:llama3.1:8b",
                "start": start, "finish": finish,
                "duration_s": round(dur, 2) if dur is not None else None,
                "validator": verdict,
                "evidence": str(art.relative_to(ROOT)) if art.exists() else None,
                "cost_usd": d.get("cost_usd", 0.0),
                "result": result,
            }
            state.recorded.add(tid)
            state.missions.append(rec)
            state.last_completion_mono = time.monotonic()
            try:
                with open(MISSIONS, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
            except Exception:
                pass


# --------------------------------------------------------------------------- sampling
def sqlite_health() -> dict:
    out = {}
    try:
        wal = DB.with_suffix(".db-wal")
        out["wal_mb"] = round(wal.stat().st_size / 1e6, 2) if wal.exists() else 0.0
    except Exception:
        out["wal_mb"] = None
    # write-probe latency (autocommit, tiny) — direct measure of contention
    import sqlite3
    t0 = time.time()
    try:
        c = sqlite3.connect(str(DB), timeout=8, isolation_level=None)
        c.execute("PRAGMA busy_timeout=8000")
        c.execute("INSERT OR REPLACE INTO mission_control_missions (mission_id,name,target_pod,command,status,created_at,updated_at) VALUES ('SOAK-PROBE','p','HASF','p','PROBE','x','x')")
        c.execute("DELETE FROM mission_control_missions WHERE mission_id='SOAK-PROBE'")
        c.close()
        out["sqlite_write_probe_ms"] = round((time.time() - t0) * 1000, 1)
        out["sqlite_writable"] = True
    except Exception as e:
        out["sqlite_write_probe_ms"] = round((time.time() - t0) * 1000, 1)
        out["sqlite_writable"] = False
        out["sqlite_error"] = str(e)[:80]
    return out


def ollama_health() -> dict:
    import urllib.request
    t0 = time.time()
    try:
        r = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=4)
        d = json.loads(r.read())
        return {"ollama_online": True, "ollama_models": len(d.get("models", [])),
                "ollama_probe_ms": round((time.time() - t0) * 1000, 1)}
    except Exception:
        return {"ollama_online": False, "ollama_probe_ms": round((time.time() - t0) * 1000, 1)}


def sample(state: SoakState):
    ingest_ledgers(state)
    el = state.elapsed()

    # ---- runtime ----
    try:
        pend = gen.pending_count()
    except Exception:
        pend = None
    # Terminal task-state breakdown from the live DB (required certification evidence:
    # held / exhausted / denied / completed / failed). Read-only, never contends.
    task_states = {}
    try:
        import sqlite3 as _sq
        _c = _sq.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
        task_states = {k: v for k, v in _c.execute(
            "SELECT status, count(*) FROM mission_control_tasks GROUP BY status").fetchall()}
        _c.close()
    except Exception:
        task_states = {}
    done = [m for m in state.missions if m["result"] in ("PASS", "FAIL", "COMPLETED", "FAILED")]
    passed = [m for m in state.missions if m["result"] == "PASS"]
    failed = [m for m in state.missions if m["result"] == "FAIL"]
    lat = sorted(m["duration_s"] for m in state.missions if m.get("duration_s") is not None)
    total = len(state.missions)
    lm = _read_json(SOAK_DIR.parent / "council" / "loop_metrics.json") or {}
    lc = lm.get("lock_contention", {})
    hb_age = None
    try:
        from datetime import datetime
        hb = lm.get("ts")
        if hb:
            hb_age = (datetime.now().astimezone() - datetime.fromisoformat(hb)).total_seconds()
    except Exception:
        pass
    runtime = {
        "queue_depth": pend,
        "completed_total": total,
        "passed_total": len(passed),
        "failed_total": len(failed),
        "recovered_total": state.recovered,
        "success_rate": round(len(passed) / total, 4) if total else None,
        "failure_rate": round(len(failed) / total, 4) if total else None,
        "throughput_per_hour": round(total / (el / 3600.0), 2) if el > 0 else 0.0,
        "mean_mission_latency_s": round(sum(lat) / len(lat), 2) if lat else None,
        "p95_mission_latency_s": (round(lat[int(len(lat) * 0.95)], 2) if len(lat) >= 20
                                  else (round(lat[-1], 2) if lat else None)),
        "loop_lock_retries": lc.get("retries_total", 0),
        "loop_hb_age_s": round(hb_age, 1) if hb_age is not None else None,
        "generated_total": state.gen_added_total,
        "task_states": task_states,
        "held_tasks": task_states.get("HELD_FOUNDER", 0),
        "exhausted_tasks": task_states.get("EXHAUSTED", 0),
        "denied_tasks": task_states.get("DENIED", 0),
    }

    # ---- INTEGRITY GUARD (founder rule: stop + preserve + report, never mask) ----
    unknown_states = [s for s in task_states if s and s not in KNOWN_TASK_STATES]
    if unknown_states:
        _alert(state, "terminal_state_integrity", "ERROR",
               f"unknown task status(es) appeared: {unknown_states} — halting to preserve evidence")
        _hard_stop.set()

    # ---- resources ----
    res = {}
    try:
        vm = psutil.virtual_memory()
        res["system_cpu_pct"] = psutil.cpu_percent(interval=None)
        res["system_mem_pct"] = vm.percent
    except Exception:
        pass
    try:
        p = psutil.Process(state.daemon_pid)
        with p.oneshot():
            res["daemon_alive"] = p.is_running()
            res["daemon_rss_mb"] = round(p.memory_info().rss / 1e6, 1)
            res["daemon_cpu_pct"] = p.cpu_percent(interval=None)
            try:
                res["daemon_fds"] = p.num_fds()
            except Exception:
                res["daemon_fds"] = None
    except Exception:
        res["daemon_alive"] = False
    res.update(sqlite_health())
    res.update(ollama_health())
    # in-flight dispatches (RUNNING leases ~ ollama processes)
    try:
        res["ollama_procs"] = sum(1 for pr in psutil.process_iter(["name"])
                                  if "ollama" in (pr.info.get("name") or "").lower())
    except Exception:
        res["ollama_procs"] = None

    if res.get("daemon_rss_mb") is not None:
        state.rss_samples.append((el, res["daemon_rss_mb"]))
    if res.get("daemon_fds") is not None:
        state.fd_samples.append((el, res["daemon_fds"]))

    # ---- governance ----
    caps = {}
    for m in state.missions:
        caps[m["capability"]] = caps.get(m["capability"], 0) + 1
    gov = {
        "capability_routing": caps,
        "validator_pass": len(passed),
        "validator_fail": len(failed),
        "evidence_artifacts": sum(1 for m in state.missions if m.get("evidence")),
        "all_local_zero_cost": all((m.get("cost_usd") or 0.0) == 0.0 for m in state.missions),
        "providers_used": sorted({(m.get("model") or "").split(":")[0] for m in state.missions}),
    }

    detect_degradation(state, runtime, res)

    # Data-integrity hard stop: SQLite must stay writable. If it doesn't, halt rather than
    # keep recording against a broken store.
    if res.get("sqlite_writable") is False:
        _alert(state, "sqlite_integrity", "ERROR",
               "SQLite not writable — data-integrity risk; halting to preserve evidence")
        _hard_stop.set()

    if _hard_stop.is_set():
        try:
            (SOAK_DIR / "soak_incident.json").write_text(json.dumps({
                "ts": now_iso(), "elapsed_s": round(el, 1),
                "reason": "HARD STOP — data-integrity / unknown terminal-state anomaly (not masked)",
                "unknown_task_states": unknown_states,
                "task_states": task_states,
                "sqlite_writable": res.get("sqlite_writable"),
                "active_alerts": list(state.alerts_active.values()),
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    snap = {
        "run_id": state.started_wall,
        "generated_at": now_iso(),
        "uptime_seconds": round(el, 1),
        "uptime_hms": time.strftime("%H:%M:%S", time.gmtime(el)),
        "runtime": runtime, "resources": res, "governance": gov,
        "active_alerts": list(state.alerts_active.values()),
        "current_dispatches": res.get("ollama_procs"),
        "provider_health": {
            "ollama": "UP" if res.get("ollama_online") else "DOWN",
            "openai": "IDLE_LOCAL_ONLY", "anthropic": "IDLE_LOCAL_ONLY", "xai": "IDLE_LOCAL_ONLY",
        },
        "provider_utilization": {
            "ollama": len([m for m in state.missions if (m.get("model") or "").startswith("ollama")]),
            "openai": 0, "anthropic": 0, "xai": 0,
        },
    }
    try:
        SNAPSHOT.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        with open(METRICS, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now_iso(), "uptime_s": round(el, 1),
                                "runtime": runtime, "resources": res, "governance": gov,
                                "alerts": list(state.alerts_active.keys())}) + "\n")
    except Exception:
        pass
    return snap


def monitor(state: SoakState):
    psutil.cpu_percent(interval=None)  # prime
    while not _stop.is_set():
        try:
            sample(state)
        except Exception as e:
            _alert(state, "monitor_error", "ERROR", f"sampler exception: {e}")
        _stop.wait(SAMPLE_INTERVAL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=None)
    ap.add_argument("--minutes", type=float, default=None)
    args = ap.parse_args()
    duration_s = (args.hours * 3600 if args.hours else
                  args.minutes * 60 if args.minutes else 6 * 3600)

    def _sig(*_):
        _stop.set()
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    # Distinct run id + exact start timestamp; previous evidence is NOT overwritten (each
    # run is archived under runs/<run_id>/ at completion).
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_id = f"CERT-{duration_s/3600:.0f}H-{stamp}"
    start_ts = now_iso()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (SOAK_DIR / "run_meta.json").write_text(json.dumps({
        "run_id": run_id, "start_ts": start_ts, "target_hours": duration_s / 3600,
        "low_water": LOW_WATER, "high_water": HIGH_WATER,
        "policy": "continue-through-degradation-when-safe; auto-downgrade verdict; never manual-promote",
    }, indent=2), encoding="utf-8")

    print(f"[soak] run_id={run_id} start={start_ts} — duration {duration_s/3600:.2f}h, "
          f"queue [{LOW_WATER},{HIGH_WATER}], dashboard http://127.0.0.1:{DASH_PORT}/soak_dashboard.html",
          flush=True)

    # seed the queue before the daemon starts so cycle 1 has work
    seeded = 0
    try:
        seeded = gen.refill(LOW_WATER, HIGH_WATER)
    except Exception as e:
        print(f"[soak] initial seed failed: {e}", flush=True)

    daemon = council_daemon_proc()
    state = SoakState(time.monotonic(), run_id, daemon.pid)  # run_id is the snapshot run_id
    state.gen_added_total = seeded
    print(f"[soak] executive loop pid={daemon.pid}", flush=True)

    threads = [threading.Thread(target=feeder, args=(state,), daemon=True),
               threading.Thread(target=monitor, args=(state,), daemon=True),
               threading.Thread(target=dashboard_server, daemon=True)]
    for t in threads:
        t.start()

    end = time.monotonic() + duration_s
    while not _stop.is_set() and not _hard_stop.is_set() and time.monotonic() < end:
        _stop.wait(2)
        if daemon.poll() is not None:  # executive loop died -> restart (recovery event)
            _alert(state, "loop_restart", "WARN", f"executive loop exited ({daemon.returncode}); restarting")
            daemon = council_daemon_proc()
            state.daemon_pid = daemon.pid
            _clear_alert(state, "loop_restart")

    _stop.set()
    if _hard_stop.is_set():
        print("[soak] HARD STOP — integrity/terminal-state anomaly detected; evidence preserved "
              f"in {SOAK_DIR/'soak_incident.json'} (NOT masked)", flush=True)
    print("[soak] stopping executive loop…", flush=True)
    try:
        daemon.terminate(); daemon.wait(timeout=10)
    except Exception:
        daemon.kill()
    time.sleep(1)
    sample(state)  # final sample

    # final report + per-run archive (preserve evidence) + comparison vs the validation run
    try:
        from scripts.soak.report import generate_report, compare_runs
        path = generate_report(SOAK_DIR)
        print(f"[soak] FINAL REPORT: {path}", flush=True)
        archive = RUNS_DIR / run_id
        archive.mkdir(parents=True, exist_ok=True)
        for f in ("soak_missions.jsonl", "soak_metrics.jsonl", "soak_alerts.jsonl",
                  "soak_snapshot.json", "run_meta.json", "soak_incident.json",
                  "FINAL_OPERATIONAL_READINESS_REPORT.md"):
            src = SOAK_DIR / f
            if src.exists():
                shutil.copy2(src, archive / f)
        print(f"[soak] archived run -> {archive}", flush=True)
        if PREV_VALIDATION_RUN.exists():
            cmp_path = compare_runs(PREV_VALIDATION_RUN, SOAK_DIR)
            shutil.copy2(cmp_path, archive / cmp_path.name)
            print(f"[soak] COMPARISON: {cmp_path}", flush=True)
    except Exception as e:
        print(f"[soak] report/archive failed: {e}", flush=True)
    print("[soak] done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
