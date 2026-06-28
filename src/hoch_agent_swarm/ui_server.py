"""
ui_server.py — Hoch Agent Swarm Dashboard

A lightweight Flask server that serves the dashboard UI and exposes
JSON API endpoints reading directly from the local artifact filesystem.

Usage: uv run python src/hoch_agent_swarm/ui_server.py
       (or via the 'swarm_ui' entry point after pyproject.toml is updated)
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve project root (works whether invoked from src/ or project root)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
PROJECT_ROOT = _HERE.parent.parent  # src/hoch_agent_swarm -> src -> project root
if not (PROJECT_ROOT / "pyproject.toml").exists():
    PROJECT_ROOT = Path.cwd()

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
CREW_RUNS_DIR = ARTIFACTS_DIR / "crew_runs"
RC_DIR = ARTIFACTS_DIR / "release_candidates"
CANONICAL_ARTIFACTS = [
    "research/asset_map.md",
    "reports/execution_plan.md",
    "reports/release_packet.md",
    "security_reviews/security_audit_report.md",
    "antigravity/antigravity_execution_plan.md",
]

# ---------------------------------------------------------------------------
# Optional Flask import — install if missing
# ---------------------------------------------------------------------------
try:
    from flask import Flask, jsonify, send_file, abort
    from flask.wrappers import Response
except ImportError:
    print("Flask not found. Installing via uv...")
    subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
    from flask import Flask, jsonify, send_file, abort
    from flask.wrappers import Response  # type: ignore

app = Flask(__name__, static_folder=None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _ts_to_display(ts: str) -> str:
    """Convert ISO timestamp to readable local string."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        local = dt.astimezone()
        return local.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


def _run_duration(started: str, completed: str) -> str:
    try:
        s = datetime.fromisoformat(started.replace("Z", "+00:00"))
        e = datetime.fromisoformat(completed.replace("Z", "+00:00"))
        secs = int((e - s).total_seconds())
        return f"{secs}s"
    except Exception:
        return "—"


def _all_crew_runs() -> list[dict]:
    runs = []
    if not CREW_RUNS_DIR.exists():
        return runs
    for ts_dir in sorted(CREW_RUNS_DIR.iterdir(), reverse=True):
        if not ts_dir.is_dir():
            continue
        rr_path = ts_dir / "run_report.json"
        gp_path = ts_dir / "quality_gate_report.json"
        rr = _load_json(rr_path) if rr_path.exists() else None
        gp = _load_json(gp_path) if gp_path.exists() else None
        runs.append({
            "ts_dir": ts_dir.name,
            "run_report": rr,
            "gate_report": gp,
        })
    return runs


def _all_rcs() -> list[dict]:
    rcs = []
    if not RC_DIR.exists():
        return rcs
    for ts_dir in sorted(RC_DIR.iterdir(), reverse=True):
        if not ts_dir.is_dir():
            continue
        rc_path = ts_dir / "release_candidate.json"
        rc = _load_json(rc_path) if rc_path.exists() else None
        if rc:
            rcs.append({"ts_dir": ts_dir.name, "rc": rc})
    return rcs


def _git_log(n: int = 10) -> list[dict]:
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%h|%s|%ai"],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=5,
        )
        lines = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                sha, msg, date = parts
                lines.append({"sha": sha, "message": msg, "date": date[:19]})
        return lines
    except Exception:
        return []


def _canonical_status() -> list[dict]:
    out = []
    for rel in CANONICAL_ARTIFACTS:
        p = ARTIFACTS_DIR / rel
        entry: dict[str, Any] = {"path": rel, "exists": p.exists()}
        if p.exists():
            size = p.stat().st_size
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            entry["size_bytes"] = size
            entry["sha256_prefix"] = h[:16]
            try:
                content = p.read_text()
                entry["preview"] = content[:300].replace("\n", " ")
            except Exception:
                entry["preview"] = ""
        out.append(entry)
    return out


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route("/api/runs")
def api_runs():
    runs = _all_crew_runs()
    result = []
    for r in runs:
        rr = r["run_report"] or {}
        gp = r["gate_report"] or {}
        result.append({
            "ts_dir": r["ts_dir"],
            "run_id": rr.get("run_id", "—"),
            "status": rr.get("status", "—"),
            "started_at": _ts_to_display(rr.get("started_at", "")),
            "completed_at": _ts_to_display(rr.get("completed_at", "")),
            "duration": _run_duration(rr.get("started_at", ""), rr.get("completed_at", "")),
            "crewai_version": rr.get("crewai_version", "—"),
            "artifact_count": len(rr.get("canonical_artifacts", [])),
            "gate_verdict": gp.get("verdict", "—") if gp else "—",
            "has_gate_report": bool(gp),
        })
    return jsonify(result)


@app.route("/api/runs/<ts_dir>")
def api_run_detail(ts_dir: str):
    run_dir = CREW_RUNS_DIR / ts_dir
    if not run_dir.exists():
        abort(404)
    rr = _load_json(run_dir / "run_report.json")
    gp = _load_json(run_dir / "quality_gate_report.json")
    return jsonify({"run_report": rr, "gate_report": gp, "ts_dir": ts_dir})


@app.route("/api/rcs")
def api_rcs():
    rcs = _all_rcs()
    result = []
    for entry in rcs:
        rc = entry["rc"]
        result.append({
            "ts_dir": entry["ts_dir"],
            "rc_id": rc.get("rc_id", "—"),
            "verdict": rc.get("verdict", "—"),
            "timestamp_utc": _ts_to_display(rc.get("timestamp_utc", "")),
            "commit_short": rc.get("git", {}).get("commit_short", "—"),
            "commit_message": rc.get("git", {}).get("commit_message", "—"),
            "branch": rc.get("git", {}).get("branch", "—"),
            "crewai_version": rc.get("crewai_version", "—"),
            "mcp_version": rc.get("mcp_version", "—"),
            "gate_verdict": rc.get("gate_verdict", "—"),
            "artifact_count": len(rc.get("artifacts", {})),
        })
    return jsonify(result)


@app.route("/api/rcs/<ts_dir>")
def api_rc_detail(ts_dir: str):
    rc_path = RC_DIR / ts_dir / "release_candidate.json"
    if not rc_path.exists():
        abort(404)
    return jsonify(_load_json(rc_path))


@app.route("/api/artifacts")
def api_artifacts():
    return jsonify(_canonical_status())


@app.route("/api/artifact/<path:rel_path>")
def api_artifact_content(rel_path: str):
    # Only serve from inside artifacts/ for safety
    p = ARTIFACTS_DIR / rel_path
    try:
        p.resolve().relative_to(ARTIFACTS_DIR.resolve())
    except ValueError:
        abort(403)
    if not p.exists() or not p.suffix == ".md":
        abort(404)
    return jsonify({"path": rel_path, "content": p.read_text()})


@app.route("/api/git_log")
def api_git_log():
    return jsonify(_git_log(15))


@app.route("/api/summary")
def api_summary():
    runs = _all_crew_runs()
    rcs = _all_rcs()
    pass_runs = sum(1 for r in runs if (r["run_report"] or {}).get("status") == "PASS")
    latest_rr = (runs[0]["run_report"] or {}) if runs else {}
    latest_rc = rcs[0]["rc"] if rcs else {}
    return jsonify({
        "total_runs": len(runs),
        "pass_runs": pass_runs,
        "fail_runs": len(runs) - pass_runs,
        "total_rcs": len(rcs),
        "latest_run_status": latest_rr.get("status", "—"),
        "latest_run_time": _ts_to_display(latest_rr.get("completed_at", "")),
        "latest_rc_id": latest_rc.get("rc_id", "—")[:8] if latest_rc else "—",
        "latest_rc_verdict": latest_rc.get("verdict", "—"),
        "latest_rc_commit": latest_rc.get("git", {}).get("commit_short", "—"),
    })


# ---------------------------------------------------------------------------
# Serve the single-page dashboard
# ---------------------------------------------------------------------------

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Hoch Agent Swarm — Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --bg:        #090c14;
      --bg2:       #0d1220;
      --bg3:       #121829;
      --glass:     rgba(255,255,255,0.04);
      --glass-b:   rgba(255,255,255,0.08);
      --border:    rgba(255,255,255,0.08);
      --accent:    #6366f1;
      --accent2:   #8b5cf6;
      --green:     #22d3a5;
      --red:       #f43f5e;
      --yellow:    #fbbf24;
      --muted:     rgba(255,255,255,0.35);
      --text:      rgba(255,255,255,0.88);
      --radius:    14px;
      --radius-sm: 8px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      overflow-x: hidden;
    }

    /* Animated gradient background */
    body::before {
      content: '';
      position: fixed;
      inset: 0;
      background:
        radial-gradient(ellipse 80% 60% at 10% 0%, rgba(99,102,241,0.12) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 90% 100%, rgba(139,92,246,0.10) 0%, transparent 60%),
        radial-gradient(ellipse 40% 40% at 50% 50%, rgba(34,211,165,0.04) 0%, transparent 70%);
      pointer-events: none;
      z-index: 0;
    }

    /* ---- Layout ---- */
    .layout { display: flex; min-height: 100vh; position: relative; z-index: 1; }

    /* ---- Sidebar ---- */
    .sidebar {
      width: 220px;
      flex-shrink: 0;
      background: rgba(9,12,20,0.8);
      border-right: 1px solid var(--border);
      backdrop-filter: blur(20px);
      padding: 28px 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
    }
    .sidebar-logo {
      display: flex; align-items: center; gap: 10px;
      padding: 0 8px 24px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 12px;
    }
    .sidebar-logo .orb {
      width: 32px; height: 32px; border-radius: 10px;
      background: linear-gradient(135deg, var(--accent), var(--accent2));
      display: flex; align-items: center; justify-content: center;
      font-size: 15px;
      box-shadow: 0 0 20px rgba(99,102,241,0.4);
    }
    .sidebar-logo .name { font-size: 13px; font-weight: 600; line-height: 1.3; }
    .sidebar-logo .sub { font-size: 10px; color: var(--muted); margin-top: 1px; }

    .nav-item {
      display: flex; align-items: center; gap: 10px;
      padding: 9px 12px; border-radius: var(--radius-sm);
      font-size: 13px; font-weight: 500;
      cursor: pointer; transition: all 0.18s;
      color: var(--muted);
      border: none; background: none; width: 100%; text-align: left;
    }
    .nav-item:hover  { background: var(--glass); color: var(--text); }
    .nav-item.active { background: rgba(99,102,241,0.15); color: var(--accent); }
    .nav-item .icon { font-size: 16px; width: 20px; text-align: center; }

    .nav-section-label {
      font-size: 10px; font-weight: 600; letter-spacing: 0.08em;
      color: var(--muted); text-transform: uppercase;
      padding: 14px 12px 4px;
    }

    /* ---- Main ---- */
    .main {
      flex: 1;
      padding: 32px 36px;
      overflow-y: auto;
      min-width: 0;
    }

    .page { display: none; }
    .page.active { display: block; }

    /* ---- Page header ---- */
    .page-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 28px;
    }
    .page-title { font-size: 22px; font-weight: 700; }
    .page-sub { font-size: 13px; color: var(--muted); margin-top: 3px; }
    .refresh-btn {
      padding: 8px 16px; border-radius: var(--radius-sm);
      background: var(--glass-b); border: 1px solid var(--border);
      color: var(--text); font-size: 12px; font-weight: 500;
      cursor: pointer; transition: all 0.2s;
      font-family: inherit;
    }
    .refresh-btn:hover { background: rgba(99,102,241,0.2); border-color: var(--accent); }

    /* ---- Stat cards ---- */
    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .stat-card {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      backdrop-filter: blur(12px);
      transition: border-color 0.2s, transform 0.2s;
    }
    .stat-card:hover { border-color: rgba(99,102,241,0.3); transform: translateY(-2px); }
    .stat-label { font-size: 11px; color: var(--muted); font-weight: 500; letter-spacing: 0.05em; text-transform: uppercase; }
    .stat-value { font-size: 28px; font-weight: 700; margin-top: 6px; }
    .stat-value.pass  { color: var(--green); }
    .stat-value.fail  { color: var(--red); }
    .stat-value.warn  { color: var(--yellow); }
    .stat-value.accent { color: var(--accent); }
    .stat-hint { font-size: 11px; color: var(--muted); margin-top: 4px; }

    /* ---- Table ---- */
    .card {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      backdrop-filter: blur(12px);
      overflow: hidden;
      margin-bottom: 24px;
    }
    .card-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      font-size: 14px; font-weight: 600;
      display: flex; align-items: center; gap: 8px;
    }
    table { width: 100%; border-collapse: collapse; }
    th {
      text-align: left; padding: 11px 16px;
      font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
      color: var(--muted); text-transform: uppercase;
      border-bottom: 1px solid var(--border);
    }
    td {
      padding: 12px 16px; font-size: 13px;
      border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: rgba(255,255,255,0.02); }
    .mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }

    /* ---- Badges ---- */
    .badge {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 3px 9px; border-radius: 20px;
      font-size: 11px; font-weight: 600; letter-spacing: 0.03em;
    }
    .badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; display: block; }
    .badge.pass   { background: rgba(34,211,165,0.12); color: var(--green); }
    .badge.pass::before { background: var(--green); box-shadow: 0 0 6px var(--green); }
    .badge.fail   { background: rgba(244,63,94,0.12); color: var(--red); }
    .badge.fail::before { background: var(--red); }
    .badge.warn   { background: rgba(251,191,36,0.12); color: var(--yellow); }
    .badge.warn::before { background: var(--yellow); }
    .badge.muted  { background: rgba(255,255,255,0.06); color: var(--muted); }
    .badge.muted::before { background: var(--muted); }

    /* ---- Row click ---- */
    .clickable { cursor: pointer; }
    .clickable:hover td { background: rgba(99,102,241,0.06) !important; }

    /* ---- Detail panel ---- */
    .detail-overlay {
      display: none;
      position: fixed; inset: 0; z-index: 100;
      background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);
    }
    .detail-overlay.open { display: flex; align-items: center; justify-content: center; }
    .detail-panel {
      background: var(--bg2);
      border: 1px solid var(--border);
      border-radius: 18px;
      width: min(860px, 95vw);
      max-height: 85vh;
      overflow-y: auto;
      padding: 28px 32px;
      position: relative;
      animation: slideUp 0.22s ease;
    }
    @keyframes slideUp {
      from { opacity: 0; transform: translateY(20px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .detail-close {
      position: absolute; top: 18px; right: 18px;
      width: 32px; height: 32px; border-radius: 8px;
      background: var(--glass-b); border: 1px solid var(--border);
      color: var(--text); font-size: 18px; line-height: 1;
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      transition: background 0.2s;
    }
    .detail-close:hover { background: rgba(244,63,94,0.2); }
    .detail-title { font-size: 16px; font-weight: 700; margin-bottom: 20px; }
    .kv-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
    .kv-item { background: var(--glass); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px 14px; }
    .kv-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
    .kv-value { font-size: 13px; font-weight: 500; }
    .section-title { font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin: 18px 0 10px; }
    .artifact-row {
      display: flex; align-items: center; justify-content: space-between;
      background: var(--glass); border: 1px solid var(--border);
      border-radius: var(--radius-sm); padding: 10px 14px; margin-bottom: 6px;
      cursor: pointer; transition: border-color 0.18s;
    }
    .artifact-row:hover { border-color: rgba(99,102,241,0.4); }
    .artifact-name { font-size: 13px; font-weight: 500; }
    .artifact-meta { font-size: 11px; color: var(--muted); margin-top: 2px; }

    /* ---- Artifact viewer ---- */
    .artifact-content {
      background: var(--bg3);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 20px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 420px;
      overflow-y: auto;
      color: rgba(255,255,255,0.75);
    }

    /* ---- Git log ---- */
    .git-entry {
      display: flex; align-items: flex-start; gap: 12px;
      padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .git-entry:last-child { border-bottom: none; }
    .git-sha {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px; color: var(--accent);
      background: rgba(99,102,241,0.1); padding: 2px 7px; border-radius: 5px;
      flex-shrink: 0;
    }
    .git-msg { font-size: 13px; }
    .git-date { font-size: 11px; color: var(--muted); margin-top: 2px; }

    /* ---- Artifact page grid ---- */
    .artifact-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;
    }
    .artifact-card {
      background: var(--glass); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 18px 20px;
      cursor: pointer; transition: all 0.2s;
    }
    .artifact-card:hover { border-color: rgba(99,102,241,0.4); transform: translateY(-2px); }
    .artifact-card-name { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
    .artifact-card-path { font-size: 11px; color: var(--muted); font-family: 'JetBrains Mono', monospace; margin-bottom: 10px; }
    .artifact-card-preview { font-size: 11px; color: rgba(255,255,255,0.5); line-height: 1.5; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }

    /* ---- Empty state ---- */
    .empty {
      text-align: center; padding: 60px 20px; color: var(--muted);
    }
    .empty .icon { font-size: 40px; margin-bottom: 12px; }
    .empty p { font-size: 14px; }

    /* ---- Scrollbar ---- */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.22); }

    /* ---- Loading spinner ---- */
    .spinner {
      width: 20px; height: 20px; border-radius: 50%;
      border: 2px solid rgba(99,102,241,0.2);
      border-top-color: var(--accent);
      animation: spin 0.7s linear infinite;
      margin: 40px auto;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="layout">

  <!-- Sidebar -->
  <nav class="sidebar">
    <div class="sidebar-logo">
      <div class="orb">⚡</div>
      <div>
        <div class="name">Hoch Swarm</div>
        <div class="sub">Agent Dashboard</div>
      </div>
    </div>

    <div class="nav-section-label">Overview</div>
    <button class="nav-item active" id="nav-overview" onclick="showPage('overview')">
      <span class="icon">📊</span> Overview
    </button>

    <div class="nav-section-label">Execution</div>
    <button class="nav-item" id="nav-runs" onclick="showPage('runs')">
      <span class="icon">🚀</span> Crew Runs
    </button>
    <button class="nav-item" id="nav-rcs" onclick="showPage('rcs')">
      <span class="icon">📦</span> Release Candidates
    </button>

    <div class="nav-section-label">Artifacts</div>
    <button class="nav-item" id="nav-artifacts" onclick="showPage('artifacts')">
      <span class="icon">📄</span> Canonical Artifacts
    </button>

    <div class="nav-section-label">Repository</div>
    <button class="nav-item" id="nav-git" onclick="showPage('git')">
      <span class="icon">🔀</span> Git Log
    </button>
  </nav>

  <!-- Main -->
  <main class="main">

    <!-- ===== OVERVIEW ===== -->
    <div class="page active" id="page-overview">
      <div class="page-header">
        <div>
          <div class="page-title">Overview</div>
          <div class="page-sub">Live system health and latest run status</div>
        </div>
        <button class="refresh-btn" onclick="loadOverview()">↻ Refresh</button>
      </div>
      <div class="stat-grid" id="stat-grid"><div class="spinner"></div></div>
      <div class="card">
        <div class="card-header">⚡ Latest Run — Canonical Artifacts</div>
        <div id="overview-artifacts"><div class="spinner"></div></div>
      </div>
      <div class="card" style="margin-top:24px">
        <div class="card-header">👥 C-Suite Swarm Leadership Team</div>
        <div style="padding:20px;display:grid;grid-template-columns:repeat(auto-fill, minmax(260px, 1fr));gap:16px" id="csuite-roster">
          <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius);padding:16px;backdrop-filter:blur(12px)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
              <span style="font-size:20px">👑</span>
              <div>
                <div style="font-size:13px;font-weight:600">Chief Executive Officer</div>
                <div style="font-size:11px;color:var(--accent);font-family:'JetBrains Mono',monospace">ceo</div>
              </div>
            </div>
            <div style="font-size:11px;color:var(--muted);line-height:1.4">Leads the company, drives strategy and growth, represents the company, and oversees overall platform integration.</div>
          </div>
          <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius);padding:16px;backdrop-filter:blur(12px)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
              <span style="font-size:20px">⚖️</span>
              <div>
                <div style="font-size:13px;font-weight:600">Chief Financial Officer</div>
                <div style="font-size:11px;color:var(--accent);font-family:'JetBrains Mono',monospace">cfo</div>
              </div>
            </div>
            <div style="font-size:11px;color:var(--muted);line-height:1.4">Manages platform risk, tracks execution performance, ensures stability, and enforces security compliance.</div>
          </div>
          <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius);padding:16px;backdrop-filter:blur(12px)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
              <span style="font-size:20px">⚙️</span>
              <div>
                <div style="font-size:13px;font-weight:600">Chief Operating Officer</div>
                <div style="font-size:11px;color:var(--accent);font-family:'JetBrains Mono',monospace">coo</div>
              </div>
            </div>
            <div style="font-size:11px;color:var(--muted);line-height:1.4">Oversees daily operations, coordinates process execution, and designs multi-agent task structures.</div>
          </div>
          <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius);padding:16px;backdrop-filter:blur(12px)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
              <span style="font-size:20px">🔌</span>
              <div>
                <div style="font-size:13px;font-weight:600">Chief Information Officer</div>
                <div style="font-size:11px;color:var(--accent);font-family:'JetBrains Mono',monospace">cio</div>
              </div>
            </div>
            <div style="font-size:11px;color:var(--muted);line-height:1.4">Defines tech strategy, audits compute resources, and dynamically assembles compliant agent configurations.</div>
          </div>
          <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius);padding:16px;backdrop-filter:blur(12px)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
              <span style="font-size:20px">📢</span>
              <div>
                <div style="font-size:13px;font-weight:600">Chief Marketing Officer</div>
                <div style="font-size:11px;color:var(--accent);font-family:'JetBrains Mono',monospace">cmo</div>
              </div>
            </div>
            <div style="font-size:11px;color:var(--muted);line-height:1.4">Manages brand positioning, sets voice/tone, and synthesizes individual task outputs into release candidate packets.</div>
          </div>
          <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius);padding:16px;backdrop-filter:blur(12px)">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
              <span style="font-size:20px">📈</span>
              <div>
                <div style="font-size:13px;font-weight:600">Chief Revenue Officer</div>
                <div style="font-size:11px;color:var(--accent);font-family:'JetBrains Mono',monospace">cro</div>
              </div>
            </div>
            <div style="font-size:11px;color:var(--muted);line-height:1.4">Optimizes sales and execution pipeline performance, sets targets, and allocates resources to high-yield opportunities.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== CREW RUNS ===== -->
    <div class="page" id="page-runs">
      <div class="page-header">
        <div>
          <div class="page-title">Crew Runs</div>
          <div class="page-sub">All local run_report.json records</div>
        </div>
        <button class="refresh-btn" onclick="loadRuns()">↻ Refresh</button>
      </div>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Status</th>
              <th>Gate</th>
              <th>Duration</th>
              <th>CrewAI</th>
              <th>Artifacts</th>
            </tr>
          </thead>
          <tbody id="runs-tbody"><tr><td colspan="6"><div class="spinner"></div></td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- ===== RELEASE CANDIDATES ===== -->
    <div class="page" id="page-rcs">
      <div class="page-header">
        <div>
          <div class="page-title">Release Candidates</div>
          <div class="page-sub">Packaged release_candidate.json records</div>
        </div>
        <button class="refresh-btn" onclick="loadRCs()">↻ Refresh</button>
      </div>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>RC ID</th>
              <th>Verdict</th>
              <th>Commit</th>
              <th>Gate</th>
              <th>CrewAI</th>
            </tr>
          </thead>
          <tbody id="rcs-tbody"><tr><td colspan="6"><div class="spinner"></div></td></tr></tbody>
        </table>
      </div>
    </div>

    <!-- ===== ARTIFACTS ===== -->
    <div class="page" id="page-artifacts">
      <div class="page-header">
        <div>
          <div class="page-title">Canonical Artifacts</div>
          <div class="page-sub">Click any artifact to view its current content</div>
        </div>
        <button class="refresh-btn" onclick="loadArtifacts()">↻ Refresh</button>
      </div>
      <div class="artifact-grid" id="artifact-grid"><div class="spinner"></div></div>
    </div>

    <!-- ===== GIT LOG ===== -->
    <div class="page" id="page-git">
      <div class="page-header">
        <div>
          <div class="page-title">Git Log</div>
          <div class="page-sub">Recent commits on master</div>
        </div>
        <button class="refresh-btn" onclick="loadGit()">↻ Refresh</button>
      </div>
      <div class="card">
        <div class="card-header">🔀 Recent Commits</div>
        <div style="padding: 16px 20px;" id="git-log-container"><div class="spinner"></div></div>
      </div>
    </div>

  </main>
</div>

<!-- ===== Detail Overlay ===== -->
<div class="detail-overlay" id="detail-overlay" onclick="closeDetail(event)">
  <div class="detail-panel" id="detail-panel">
    <button class="detail-close" onclick="closeDetail()">✕</button>
    <div id="detail-content"></div>
  </div>
</div>

<script>
// ---- Navigation ----
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');
  const loaders = { overview: loadOverview, runs: loadRuns, rcs: loadRCs, artifacts: loadArtifacts, git: loadGit };
  if (loaders[name]) loaders[name]();
}

// ---- Helpers ----
function badge(verdict) {
  const v = (verdict || '').toUpperCase();
  const cls = v === 'PASS' ? 'pass' : v === 'FAIL' ? 'fail' : 'muted';
  return `<span class="badge ${cls}">${verdict || '—'}</span>`;
}

function fmt(val) { return val || '—'; }

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

// ---- Overview ----
async function loadOverview() {
  const grid = document.getElementById('stat-grid');
  const artDiv = document.getElementById('overview-artifacts');
  grid.innerHTML = '<div class="spinner"></div>';
  artDiv.innerHTML = '<div class="spinner"></div>';
  try {
    const [summary, artifacts] = await Promise.all([fetchJSON('/api/summary'), fetchJSON('/api/artifacts')]);
    grid.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Total Runs</div>
        <div class="stat-value accent">${summary.total_runs}</div>
        <div class="stat-hint">${summary.pass_runs} passed · ${summary.fail_runs} failed</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Latest Run</div>
        <div class="stat-value ${summary.latest_run_status === 'PASS' ? 'pass' : 'fail'}">${summary.latest_run_status}</div>
        <div class="stat-hint">${summary.latest_run_time}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Release Candidates</div>
        <div class="stat-value accent">${summary.total_rcs}</div>
        <div class="stat-hint">Latest: ${summary.latest_rc_commit}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Latest RC</div>
        <div class="stat-value ${summary.latest_rc_verdict === 'PASS' ? 'pass' : 'fail'}">${summary.latest_rc_verdict}</div>
        <div class="stat-hint">ID: ${summary.latest_rc_id}…</div>
      </div>
    `;
    const rows = artifacts.map(a => {
      const statusBadge = a.exists ? badge('PASS') : badge('FAIL');
      return `
        <div class="artifact-row" onclick="viewArtifact('${a.path}', '${a.path.split('/').pop()}')">
          <div>
            <div class="artifact-name">${a.path.split('/').pop()}</div>
            <div class="artifact-meta mono">${a.path}</div>
          </div>
          <div style="display:flex;gap:10px;align-items:center">
            <span style="font-size:11px;color:var(--muted)">${a.size_bytes ? (a.size_bytes/1024).toFixed(1)+'kb' : ''}</span>
            ${statusBadge}
          </div>
        </div>`;
    }).join('');
    artDiv.innerHTML = `<div style="padding:16px 20px">${rows}</div>`;
  } catch(e) {
    grid.innerHTML = `<div style="color:var(--red);padding:20px">Error: ${e.message}</div>`;
  }
}

// ---- Runs ----
async function loadRuns() {
  const tbody = document.getElementById('runs-tbody');
  tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div></td></tr>';
  try {
    const runs = await fetchJSON('/api/runs');
    if (!runs.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty"><div class="icon">🚀</div><p>No crew runs found</p></div></td></tr>';
      return;
    }
    tbody.innerHTML = runs.map(r => `
      <tr class="clickable" onclick="showRunDetail('${r.ts_dir}')">
        <td class="mono">${r.ts_dir}</td>
        <td>${badge(r.status)}</td>
        <td>${badge(r.gate_verdict)}</td>
        <td>${r.duration}</td>
        <td class="mono">${r.crewai_version}</td>
        <td>${r.artifact_count}</td>
      </tr>`).join('');
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="6" style="color:var(--red)">Error: ${e.message}</td></tr>`;
  }
}

async function showRunDetail(tsDir) {
  const content = document.getElementById('detail-content');
  content.innerHTML = '<div class="spinner"></div>';
  document.getElementById('detail-overlay').classList.add('open');
  try {
    const d = await fetchJSON('/api/runs/' + tsDir);
    const rr = d.run_report || {};
    const gp = d.gate_report || {};
    const artifacts = (rr.canonical_artifacts || []).map(a => `
      <div class="artifact-row" onclick="viewArtifact('${a.path.replace(/^.*artifacts\//, 'artifacts/')}', '${a.path.split('/').pop()}')">
        <div>
          <div class="artifact-name">${a.path.split('/').pop()}</div>
          <div class="artifact-meta mono">${(a.sha256||'').slice(0,16)}… · ${((a.size_bytes||0)/1024).toFixed(1)}kb</div>
        </div>
        ${badge(a.validation_status || 'VALID')}
      </div>`).join('');
    const gateSteps = (gp.steps || []).map(s =>
      `<div style="display:flex;gap:10px;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04)">
        ${badge(s.passed ? 'PASS' : 'FAIL')}
        <span style="font-size:13px">${s.name}</span>
        <span style="font-size:12px;color:var(--muted);margin-left:auto">${s.detail||''}</span>
      </div>`).join('');
    const tasks = ((rr.metrics || {}).tasks || []).map(t => `
      <div style="background:var(--glass);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px;margin-bottom:8px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px">${escapeHtml(t.task_name).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
          <span class="badge ${t.status === 'success' ? 'pass' : 'fail'}">${t.status}</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:8px;font-size:11px;color:var(--muted)">
          <div><strong>Agent:</strong> ${escapeHtml(t.agent_role)} (<span class="mono">${escapeHtml(t.agent_key)}</span>)</div>
          <div><strong>Model:</strong> <span class="mono">${escapeHtml(t.model)}</span></div>
          <div><strong>Class:</strong> <span class="mono">${escapeHtml(t.task_class)}</span></div>
          <div><strong>Tokens:</strong> ${t.tokens}</div>
          <div><strong>Artifact:</strong> <span class="mono">${escapeHtml(t.artifact_result)}</span></div>
          <div><strong>Quality:</strong> ${badge(t.artifact_quality)}</div>
        </div>
      </div>
    `).join('');
    content.innerHTML = `
      <div class="detail-title">🚀 Run — ${tsDir}</div>
      <div class="kv-grid">
        <div class="kv-item"><div class="kv-label">Status</div><div class="kv-value">${badge(rr.status)}</div></div>
        <div class="kv-item"><div class="kv-label">Run ID</div><div class="kv-value mono" style="font-size:11px">${rr.run_id||'—'}</div></div>
        <div class="kv-item"><div class="kv-label">Started</div><div class="kv-value">${(rr.started_at||'').slice(0,19).replace('T',' ')}</div></div>
        <div class="kv-item"><div class="kv-label">Completed</div><div class="kv-value">${(rr.completed_at||'').slice(0,19).replace('T',' ')}</div></div>
        <div class="kv-item"><div class="kv-label">CrewAI</div><div class="kv-value">${rr.crewai_version||'—'}</div></div>
        <div class="kv-item"><div class="kv-label">Gate Verdict</div><div class="kv-value">${badge(gp.verdict||'—')}</div></div>
      </div>
      ${tasks ? `<div class="section-title">Swarm Execution & Tasks Breakdown</div>${tasks}` : ''}
      ${artifacts ? `<div class="section-title">Canonical Artifacts</div>${artifacts}` : ''}
      ${gateSteps ? `<div class="section-title">Quality Gate Steps</div>${gateSteps}` : ''}
    `;
  } catch(e) {
    content.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
}

// ---- RCs ----
async function loadRCs() {
  const tbody = document.getElementById('rcs-tbody');
  tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div></td></tr>';
  try {
    const rcs = await fetchJSON('/api/rcs');
    if (!rcs.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty"><div class="icon">📦</div><p>No release candidates found</p></div></td></tr>';
      return;
    }
    tbody.innerHTML = rcs.map(r => `
      <tr class="clickable" onclick="showRCDetail('${r.ts_dir}')">
        <td class="mono">${r.ts_dir}</td>
        <td class="mono" style="font-size:11px">${r.rc_id.slice(0,8)}…</td>
        <td>${badge(r.verdict)}</td>
        <td class="mono">${r.commit_short}</td>
        <td>${badge(r.gate_verdict)}</td>
        <td class="mono">${r.crewai_version}</td>
      </tr>`).join('');
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="6" style="color:var(--red)">Error: ${e.message}</td></tr>`;
  }
}

async function showRCDetail(tsDir) {
  const content = document.getElementById('detail-content');
  content.innerHTML = '<div class="spinner"></div>';
  document.getElementById('detail-overlay').classList.add('open');
  try {
    const rc = await fetchJSON('/api/rcs/' + tsDir);
    const artifacts = Object.entries(rc.artifacts || {}).map(([name, a]) => `
      <div class="artifact-row" onclick="viewArtifact('${a.path}', '${name}')">
        <div>
          <div class="artifact-name">${name}</div>
          <div class="artifact-meta mono">${(a.sha256||'').slice(0,16)}… · ${((a.size_bytes||0)/1024).toFixed(1)}kb</div>
        </div>
        ${badge(a.present ? 'PASS' : 'FAIL')}
      </div>`).join('');
    content.innerHTML = `
      <div class="detail-title">📦 Release Candidate — ${tsDir}</div>
      <div class="kv-grid">
        <div class="kv-item"><div class="kv-label">RC ID</div><div class="kv-value mono" style="font-size:11px">${rc.rc_id||'—'}</div></div>
        <div class="kv-item"><div class="kv-label">Verdict</div><div class="kv-value">${badge(rc.verdict)}</div></div>
        <div class="kv-item"><div class="kv-label">Commit</div><div class="kv-value mono">${(rc.git||{}).commit_short||'—'}</div></div>
        <div class="kv-item"><div class="kv-label">Branch</div><div class="kv-value">${(rc.git||{}).branch||'—'}</div></div>
        <div class="kv-item"><div class="kv-label">CrewAI</div><div class="kv-value">${rc.crewai_version||'—'}</div></div>
        <div class="kv-item"><div class="kv-label">Gate Verdict</div><div class="kv-value">${badge(rc.gate_verdict||'—')}</div></div>
      </div>
      <div class="kv-item" style="margin-bottom:16px">
        <div class="kv-label">Commit Message</div>
        <div class="kv-value" style="margin-top:4px">${(rc.git||{}).commit_message||'—'}</div>
      </div>
      <div class="section-title">Artifacts</div>
      ${artifacts}
    `;
  } catch(e) {
    content.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
}

// ---- Artifacts ----
async function loadArtifacts() {
  const grid = document.getElementById('artifact-grid');
  grid.innerHTML = '<div class="spinner"></div>';
  try {
    const arts = await fetchJSON('/api/artifacts');
    grid.innerHTML = arts.map(a => {
      const name = a.path.split('/').pop().replace('.md','');
      return `
        <div class="artifact-card" onclick="viewArtifact('${a.path}', '${name}')">
          <div class="artifact-card-name">${name.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
          <div class="artifact-card-path">${a.path}</div>
          ${a.exists ? `
            <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
              ${badge('VALID')}
              <span style="font-size:11px;color:var(--muted)">${((a.size_bytes||0)/1024).toFixed(1)}kb</span>
              <span class="mono" style="font-size:10px;color:var(--muted)">${a.sha256_prefix}…</span>
            </div>
            <div class="artifact-card-preview">${a.preview||''}</div>
          ` : `${badge('MISSING')}`}
        </div>`;
    }).join('');
  } catch(e) {
    grid.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
}

async function viewArtifact(relPath, name) {
  // Normalize path — strip leading project root or 'artifacts/'
  const artPath = relPath.replace(/^.*?artifacts\//, 'artifacts/');
  const content = document.getElementById('detail-content');
  content.innerHTML = '<div class="spinner"></div>';
  document.getElementById('detail-overlay').classList.add('open');
  try {
    const d = await fetchJSON('/api/artifact/' + artPath);
    content.innerHTML = `
      <div class="detail-title">📄 ${name || artPath.split('/').pop()}</div>
      <div class="mono" style="font-size:11px;color:var(--muted);margin-bottom:16px">${artPath}</div>
      <div class="artifact-content">${escapeHtml(d.content)}</div>
    `;
  } catch(e) {
    content.innerHTML = `<div style="color:var(--red)">Error loading artifact: ${e.message}</div>`;
  }
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ---- Git Log ----
async function loadGit() {
  const c = document.getElementById('git-log-container');
  c.innerHTML = '<div class="spinner"></div>';
  try {
    const commits = await fetchJSON('/api/git_log');
    if (!commits.length) {
      c.innerHTML = '<div class="empty"><p>No git history found</p></div>';
      return;
    }
    c.innerHTML = commits.map(commit => `
      <div class="git-entry">
        <span class="git-sha">${commit.sha}</span>
        <div>
          <div class="git-msg">${escapeHtml(commit.message)}</div>
          <div class="git-date">${commit.date}</div>
        </div>
      </div>`).join('');
  } catch(e) {
    c.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
}

// ---- Detail overlay close ----
function closeDetail(event) {
  if (!event || event.target === document.getElementById('detail-overlay')) {
    document.getElementById('detail-overlay').classList.remove('open');
  }
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(null); });

// ---- Init ----
loadOverview();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return DASHBOARD_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    port = int(os.environ.get("SWARM_UI_PORT", "7788"))
    print(f"\n  🚀  Hoch Agent Swarm Dashboard")
    print(f"  →   http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
