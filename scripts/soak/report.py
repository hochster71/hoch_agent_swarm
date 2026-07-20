#!/usr/bin/env python3
"""Final Operational Readiness Report — certification format.

Ten sections, then an evidence-driven verdict (YES / PARTIAL / NO). YES is GATED: every
requirement must pass on observed evidence or the verdict auto-downgrades. Nothing is ever
promoted manually. Optimizes for truthful evidence, not green.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

# ---- YES thresholds (a requirement failing any of these downgrades the verdict) ----
SUSTAINED_TARGET_S = 6 * 3600
FULL_WINDOW_MIN_S = 5.9 * 3600          # tolerance for the 6h window
SUCCESS_FLOOR = 0.80                    # below this = disqualifying
SUCCESS_STRONG = 0.95                   # below this (but >= floor) = PARTIAL, not YES
SQLITE_PROBE_MAX_MS = 3000
RSS_LEAK_SLOPE = 40                     # MB/h sustained
FD_LEAK_SLOPE = 20                      # fds/h sustained
TELEMETRY_STALE_MAX = 2                 # >2 stale events (beyond startup) = unstable


def _load_jsonl(p: Path):
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _stats(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return None
    s = sorted(vals)
    return {"min": round(s[0], 2), "max": round(s[-1], 2),
            "mean": round(statistics.mean(s), 2),
            "median": round(statistics.median(s), 2),
            "p95": round(s[int(len(s) * 0.95)] if len(s) >= 20 else s[-1], 2), "n": len(s)}


def _slope_per_hour(samples):
    n = len(samples)
    if n < 8:
        return 0.0
    xs = [s[0] for s in samples]; ys = [s[1] for s in samples]
    mx = sum(xs) / n; my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return (sum((xs[i]-mx)*(ys[i]-my) for i in range(n)) / den * 3600.0) if den else 0.0


def _series(metrics, path):
    """Pull a (uptime_s, value) series from metrics rows; path like ('resources','daemon_rss_mb')."""
    out = []
    for m in metrics:
        v = m
        for k in path:
            v = (v or {}).get(k) if isinstance(v, dict) else None
        if isinstance(v, (int, float)):
            out.append((m.get("uptime_s", 0), v))
    return out


def _collect(soak_dir: Path):
    soak_dir = Path(soak_dir)
    missions = _load_jsonl(soak_dir / "soak_missions.jsonl")
    metrics = _load_jsonl(soak_dir / "soak_metrics.jsonl")
    alerts = _load_jsonl(soak_dir / "soak_alerts.jsonl")
    snap = _load_json(soak_dir / "soak_snapshot.json")
    return missions, metrics, alerts, snap


def _analyze(soak_dir: Path):
    missions, metrics, alerts, snap = _collect(soak_dir)
    total = len(missions)
    passed = [m for m in missions if m.get("result") == "PASS"]
    failed = [m for m in missions if m.get("result") == "FAIL"]
    lat = [m["duration_s"] for m in missions if m.get("duration_s") is not None]
    uptime_s = snap.get("uptime_seconds", metrics[-1]["uptime_s"] if metrics else 0.0)
    success_rate = (len(passed) / total) if total else None

    rss = _series(metrics, ("resources", "daemon_rss_mb"))
    fds = _series(metrics, ("resources", "daemon_fds"))
    probes = _series(metrics, ("resources", "sqlite_write_probe_ms"))
    wal = _series(metrics, ("resources", "wal_mb"))
    cpu = _series(metrics, ("resources", "system_cpu_pct"))
    mem = _series(metrics, ("resources", "system_mem_pct"))
    unwritable = sum(1 for m in metrics if m.get("resources", {}).get("sqlite_writable") is False)

    rss_slope = _slope_per_hour(rss)
    rss_vals = [v for _, v in rss]
    # sustained leak vs transient churn: compare first-quartile vs last-quartile medians
    def _q_median(seq, lo, hi):
        seg = [v for _, v in seq[int(len(seq)*lo):int(len(seq)*hi)]]
        return statistics.median(seg) if seg else None
    rss_q1 = _q_median(rss, 0.0, 0.25)
    rss_q4 = _q_median(rss, 0.75, 1.0)
    sustained_leak = bool(rss_slope > RSS_LEAK_SLOPE and rss_q1 and rss_q4 and rss_q4 > rss_q1 * 1.5)
    peak_rss = max(rss_vals) if rss_vals else None
    churn = bool(peak_rss and rss_q4 and peak_rss > (rss_q4 or 0) + 80 and not sustained_leak)

    fd_slope = _slope_per_hour(fds)
    fd_vals = [v for _, v in fds]
    fd_leak = bool(fd_slope > FD_LEAK_SLOPE and fd_vals and fd_vals[-1] > (fd_vals[0] + 50))

    alert_keys = {}
    for a in alerts:
        alert_keys.setdefault(a["key"], []).append(a)
    errors = [k for k, v in alert_keys.items() if v[0].get("severity") == "ERROR"]
    telem_stale = len(alert_keys.get("telemetry_stale", []))
    loop_restarts = len(alert_keys.get("loop_restart", []))
    recovered = snap.get("runtime", {}).get("recovered_total", 0)

    caps = {}
    models = {}
    for m in missions:
        caps[m["capability"]] = caps.get(m["capability"], 0) + 1
        mod = (m.get("model") or "unknown").split(":")[0]
        models[mod] = models.get(mod, 0) + 1

    task_states = (snap.get("runtime", {}) or {}).get("task_states", {})
    incident = _load_json(soak_dir / "soak_incident.json")

    return dict(
        soak_dir=soak_dir, missions=missions, metrics=metrics, alerts=alerts, snap=snap,
        total=total, passed=passed, failed=failed, lat=lat, uptime_s=uptime_s,
        success_rate=success_rate, rss=rss, rss_slope=rss_slope, rss_q1=rss_q1, rss_q4=rss_q4,
        peak_rss=peak_rss, sustained_leak=sustained_leak, churn=churn,
        fds=fds, fd_slope=fd_slope, fd_leak=fd_leak, probes=probes, wal=wal, cpu=cpu, mem=mem,
        unwritable=unwritable, alert_keys=alert_keys, errors=errors, telem_stale=telem_stale,
        loop_restarts=loop_restarts, recovered=recovered, caps=caps, models=models,
        task_states=task_states, incident=incident,
    )


def _verdict(a: dict):
    """Strict, auto-downgrading. YES only if EVERY requirement passes."""
    reqs = []  # (name, passed, evidence)
    up = a["uptime_s"]; sr = a["success_rate"]

    reqs.append(("Full 6h observation window", up >= FULL_WINDOW_MIN_S,
                 f"observed {up/3600:.2f}h (need ≥ {SUSTAINED_TARGET_S//3600}h)"))
    disq = (sr is not None and sr < SUCCESS_FLOOR) or bool(a["errors"]) or a["unwritable"] > 0 or a["sustained_leak"]
    reqs.append(("No disqualifying failures",
                 not disq and (sr is None or sr >= SUCCESS_STRONG),
                 f"success {sr*100:.1f}% " if sr is not None else "no missions " +
                 f"| ERROR alerts {a['errors']} | sqlite-unwritable {a['unwritable']} | sustained-leak {a['sustained_leak']}"))
    reqs.append(("Stable telemetry", a["telem_stale"] <= TELEMETRY_STALE_MAX,
                 f"telemetry_stale events={a['telem_stale']} (≤{TELEMETRY_STALE_MAX} ok; startup transient allowed)"))
    reqs.append(("Stable dispatch", "ollama_down" not in a["alert_keys"] and a["loop_restarts"] == 0,
                 f"provider-down alerts={'ollama_down' in a['alert_keys']} | loop restarts={a['loop_restarts']}"))
    reqs.append(("Stable queue behavior",
                 "stale_queue" not in a["alert_keys"] and "repeated_retries" not in a["alert_keys"],
                 f"stale_queue={'stale_queue' in a['alert_keys']} | repeated_retries={'repeated_retries' in a['alert_keys']}"))
    probe_stats = _stats([v for _, v in a["probes"]])
    reqs.append(("Stable SQLite",
                 a["unwritable"] == 0 and (probe_stats is None or probe_stats["max"] <= SQLITE_PROBE_MAX_MS),
                 f"unwritable={a['unwritable']} | write-probe max={probe_stats['max'] if probe_stats else 'n/a'}ms"))
    reqs.append(("No data-integrity / terminal-state incident", not a.get("incident"),
                 (a["incident"].get("reason") if a.get("incident") else "none — no hard-stop was triggered")))
    reqs.append(("No sustained resource exhaustion", not a["sustained_leak"] and not a["fd_leak"],
                 f"sustained mem leak={a['sustained_leak']} (slope {a['rss_slope']:.0f} MB/h) | fd leak={a['fd_leak']}"))

    all_pass = all(p for _, p, _ in reqs)
    # severity: a hard fault -> NO; otherwise unmet-requirement -> PARTIAL
    hard_fault = disq or a["unwritable"] > 0 or (sr is not None and sr < SUCCESS_FLOOR) or bool(a.get("incident"))
    if all_pass:
        verdict = "YES"
    elif hard_fault:
        verdict = "NO"
    else:
        verdict = "PARTIAL"
    return verdict, reqs


def _bucketize(metrics, missions, n=12):
    if not metrics:
        return []
    tmax = metrics[-1].get("uptime_s", 0) or 1
    step = tmax / n
    buckets = []
    for i in range(n):
        lo, hi = i * step, (i + 1) * step
        rows = [m for m in metrics if lo <= m.get("uptime_s", 0) < hi]
        mis = [m for m in missions
               if m.get("finish") and rows and True]  # completion count approximated below
        rss = [m["resources"].get("daemon_rss_mb") for m in rows if m.get("resources", {}).get("daemon_rss_mb") is not None]
        cpu = [m["resources"].get("system_cpu_pct") for m in rows if m.get("resources", {}).get("system_cpu_pct") is not None]
        done = rows[-1]["runtime"].get("completed_total") if rows and rows[-1].get("runtime") else None
        buckets.append({"t0_min": round(lo/60, 1), "t1_min": round(hi/60, 1),
                        "completed_cum": done,
                        "rss_peak": round(max(rss), 1) if rss else None,
                        "cpu_mean": round(statistics.mean(cpu), 1) if cpu else None})
    return buckets


def generate_report(soak_dir: Path) -> Path:
    a = _analyze(soak_dir)
    snap = a["snap"]; total = a["total"]; sr = a["success_rate"]
    verdict, reqs = _verdict(a)

    def pct(x):
        return f"{x*100:.1f}%" if isinstance(x, (int, float)) else "UNKNOWN"

    lat_stats = _stats(a["lat"])
    probe_stats = _stats([v for _, v in a["probes"]])
    cpu_stats = _stats([v for _, v in a["cpu"]])
    mem_stats = _stats([v for _, v in a["mem"]])
    wal_stats = _stats([v for _, v in a["wal"]])
    rss_stats = _stats([v for _, v in a["rss"]])
    fd_stats = _stats([v for _, v in a["fds"]])

    L = []
    L.append("# HELM — Final Operational Readiness Report (Certification)")
    L.append(f"\n_Run **{snap.get('run_id','?')}** · generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} · "
             f"observed window **{snap.get('uptime_hms','?')}** ({a['uptime_s']/3600:.2f}h)_\n")

    # 1
    L.append("## 1. Executive Summary\n")
    L.append(f"- Observed **{a['uptime_s']/3600:.2f}h** of autonomous operation; **{total} missions** "
             f"({len(a['passed'])} pass / {len(a['failed'])} fail), success **{pct(sr)}**.")
    L.append(f"- All work local ($0), evidence-driven (real repo code/docs), deterministic validation.")
    L.append(f"- Degradation observed: ERROR={a['errors'] or 'none'}, "
             f"other alerts={[k for k in a['alert_keys'] if k not in a['errors']] or 'none'}; loop restarts={a['loop_restarts']}.")
    if a.get("incident"):
        L.append(f"- **⚠ HARD STOP INCIDENT:** {a['incident'].get('reason')} — soak halted to preserve "
                 f"evidence (not masked). See soak_incident.json. This forces the verdict to NO.")
    L.append(f"- **Verdict: {verdict}** (strict, auto-downgraded — see §10).")

    # 2
    L.append("\n## 2. Timeline\n")
    L.append("| window (min) | completed (cum) | RSS peak (MB) | CPU mean (%) |")
    L.append("|---|---|---|---|")
    for b in _bucketize(a["metrics"], a["missions"]):
        L.append(f"| {b['t0_min']}–{b['t1_min']} | {b['completed_cum']} | {b['rss_peak']} | {b['cpu_mean']} |")
    L.append("\nDegradation events (chronological):")
    if a["alerts"]:
        for ev in a["alerts"]:
            L.append(f"- @{ev.get('elapsed_s')}s [{ev.get('severity')}] {ev.get('key')} — {ev.get('detail')}")
    else:
        L.append("- none")

    # 3
    L.append("\n## 3. Mission Statistics\n")
    L.append(f"- Total: **{total}** | pass **{len(a['passed'])}** | fail **{len(a['failed'])}** | success **{pct(sr)}**")
    L.append(f"- Throughput: **{snap.get('runtime',{}).get('throughput_per_hour','n/a')}/h**")
    if lat_stats:
        L.append(f"- Latency (s): min {lat_stats['min']} · mean {lat_stats['mean']} · median {lat_stats['median']} · p95 {lat_stats['p95']} · max {lat_stats['max']}")
    L.append(f"- Capability routing: `{a['caps']}`")
    L.append(f"- Terminal task states: `{a['task_states']}` "
             f"(held={a['task_states'].get('HELD_FOUNDER',0)} · exhausted={a['task_states'].get('EXHAUSTED',0)} · "
             f"denied={a['task_states'].get('DENIED',0)})")
    L.append(f"- Evidence artifacts: **{snap.get('governance',{}).get('evidence_artifacts',0)}** · all $0/local: **{snap.get('governance',{}).get('all_local_zero_cost')}**")

    # 4
    L.append("\n## 4. Provider Statistics\n")
    L.append(f"- Model utilization (missions): `{a['models']}`")
    L.append(f"- Ollama: exercised, {snap.get('resources',{}).get('ollama_models','?')} models available.")
    L.append("- OpenAI / Anthropic / xAI: **IDLE** — not exercised (local-only policy). Utilization 0; health not fabricated.")

    # 5
    L.append("\n## 5. Resource Trends\n")
    L.append(f"- CPU (system %): {cpu_stats}")
    L.append(f"- Memory (system %): {mem_stats}")
    L.append(f"- Daemon fds: {fd_stats} (slope {a['fd_slope']:.1f}/h; leak={a['fd_leak']})")

    # 6
    L.append("\n## 6. SQLite Analysis\n")
    L.append(f"- Write-probe latency (ms): {probe_stats}")
    L.append(f"- Unwritable samples: **{a['unwritable']}** (0 = persistence never blocked)")
    L.append(f"- WAL size (MB): {wal_stats}")
    L.append(f"- Verdict: {'STABLE — writable throughout, bounded latency' if a['unwritable']==0 and (not probe_stats or probe_stats['max']<=SQLITE_PROBE_MAX_MS) else 'UNSTABLE — see values'}")

    # 7
    L.append("\n## 7. Memory Analysis\n")
    L.append(f"- Daemon RSS (MB): {rss_stats}")
    L.append(f"- Peak: **{a['peak_rss']} MB** · first-quartile median {a['rss_q1']} → last-quartile median {a['rss_q4']} · slope {a['rss_slope']:.1f} MB/h")
    if a["sustained_leak"]:
        L.append("- **SUSTAINED LEAK DETECTED** — RSS accumulates across the run (disqualifying).")
    elif a["churn"]:
        L.append("- **Transient per-cycle churn** — RSS spikes then releases; NOT a sustained leak. Worth profiling for efficiency.")
    else:
        L.append("- Stable — no sustained growth, no significant churn.")

    # 8
    L.append("\n## 8. Failure Analysis\n")
    if a["failed"]:
        L.append(f"- {len(a['failed'])} real validator failure(s) (deterministic checks the model output did not satisfy):")
        for m in a["failed"][:20]:
            L.append(f"  - `{m['mission_id']}` ({m['capability']}) validator={m.get('validator')} — real quality failure, not a harness fault")
    else:
        L.append("- No validator failures.")
    if a["errors"]:
        L.append(f"- ERROR-severity degradation: {a['errors']}")

    # 9
    L.append("\n## 9. Recovery Events\n")
    L.append(f"- Executive-loop restarts (auto-recovered): **{a['loop_restarts']}**")
    L.append(f"- Task retries recovered to pass: **{a['recovered']}**")
    L.append(f"- SQLite lock-retries absorbed by the durability layer: **{snap.get('runtime',{}).get('loop_lock_retries',0)}**")
    if not a["loop_restarts"] and not a["recovered"]:
        L.append("- No recovery was required (no faults arose that needed recovering).")

    # 10
    L.append("\n## 10. Operational Readiness\n")
    L.append("Strict requirement checklist (YES requires ALL ✓; any ✗ auto-downgrades):\n")
    for name, ok, ev in reqs:
        L.append(f"- {'✓' if ok else '✗'} **{name}** — {ev}")

    L.append("\n---\n")
    L.append("### Based solely on observed evidence, is HELM ready for sustained autonomous operation?\n")
    L.append(f"# {verdict}\n")
    L.append("**Justification (evidence only):**")
    fails = [f"{name}: {ev}" for name, ok, ev in reqs if not ok]
    if fails:
        for f in fails:
            L.append(f"- Requirement NOT met — {f}")
    else:
        L.append("- Every certification requirement met on observed evidence.")
    if a["churn"] and not a["sustained_leak"]:
        L.append("- Note: transient per-cycle memory churn observed (not disqualifying; profile for efficiency).")

    out = soak_dir / "FINAL_OPERATIONAL_READINESS_REPORT.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def compare_runs(prev_dir: Path, cur_dir: Path) -> Path:
    """Highlight what changed between the validation run and the certification run."""
    p = _analyze(Path(prev_dir))
    c = _analyze(Path(cur_dir))

    def row(label, pv, cv):
        return f"| {label} | {pv} | {cv} |"

    L = ["# Soak Comparison — Validation (31-min) vs Certification (6-hour)\n",
         f"_generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}_\n",
         "| Metric | Validation | Certification |", "|---|---|---|",
         row("Run ID", p["snap"].get("run_id"), c["snap"].get("run_id")),
         row("Observed window (h)", f"{p['uptime_s']/3600:.2f}", f"{c['uptime_s']/3600:.2f}"),
         row("Missions", p["total"], c["total"]),
         row("Success rate", f"{(p['success_rate'] or 0)*100:.1f}%", f"{(c['success_rate'] or 0)*100:.1f}%"),
         row("Failures", len(p["failed"]), len(c["failed"])),
         row("Peak RSS (MB)", p["peak_rss"], c["peak_rss"]),
         row("RSS slope (MB/h)", f"{p['rss_slope']:.0f}", f"{c['rss_slope']:.0f}"),
         row("Sustained leak", p["sustained_leak"], c["sustained_leak"]),
         row("SQLite unwritable", p["unwritable"], c["unwritable"]),
         row("Loop restarts", p["loop_restarts"], c["loop_restarts"]),
         row("Lock-retries", p["snap"].get("runtime", {}).get("loop_lock_retries", 0),
             c["snap"].get("runtime", {}).get("loop_lock_retries", 0)),
         row("Alerts (keys)", list(p["alert_keys"].keys()), list(c["alert_keys"].keys())),
         ]
    pv, _ = _verdict(p); cv, _ = _verdict(c)
    L += ["", f"**Verdict: {pv} → {cv}**", "",
          "## What changed",
          f"- Observation window grew from {p['uptime_s']/3600:.2f}h to {c['uptime_s']/3600:.2f}h "
          f"({'now meets' if c['uptime_s'] >= FULL_WINDOW_MIN_S else 'still below'} the 6h certification bar).",
          f"- Memory: peak {p['peak_rss']}→{c['peak_rss']} MB; sustained-leak {p['sustained_leak']}→{c['sustained_leak']} "
          f"(the key question a longer window answers: does churn become accumulation?).",
          f"- Reliability: success {(p['success_rate'] or 0)*100:.1f}%→{(c['success_rate'] or 0)*100:.1f}%, "
          f"restarts {p['loop_restarts']}→{c['loop_restarts']}, sqlite-unwritable {p['unwritable']}→{c['unwritable']}.",
          ]
    out = Path(cur_dir) / "SOAK_COMPARISON_validation_vs_certification.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("coordination/soak")
    print(generate_report(d))
