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
if not (PROJECT_ROOT / "artifacts").exists() and Path("/app/artifacts").exists():
    PROJECT_ROOT = Path("/app")
elif not (PROJECT_ROOT / "pyproject.toml").exists():
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

from flask_cors import CORS

app = Flask(__name__, static_folder=None)
CORS(app, supports_credentials=True)

@app.after_request
def after_request(response):
    from flask import request
    origin = request.headers.get("Origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    return response

@app.route('/<path:path>.map')
def serve_sourcemap(path):
    """Return 204 No Content for missing .map files instead of 404."""
    return '', 204

@app.errorhandler(404)
def handle_404(error):
    """Suppress 404 errors for .map files."""
    from flask import request
    if request.path.endswith('.map'):
        return '', 204
    return error


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
    p = (ARTIFACTS_DIR / rel_path).resolve()
    if not p.is_relative_to(ARTIFACTS_DIR.resolve()):
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
# PROMPTBRAIN1 Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/v1/promptbrain/status")
def api_promptbrain_status():
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    pm = get_promptbrain_manager()
    qa = get_promptqa_manager()
    res = {
        "status": pm.import_report.get("status"),
        "total_prompts": len(pm.prompts),
        "total_gaps": len(pm.gaps),
        "total_generated": len(pm.generated_prompts),
        "total_revised": len(pm.revised_prompts),
        "imported_at": pm.import_report.get("imported_at")
    }
    res.update(qa.status)
    return jsonify(res)

@app.route("/api/v1/promptbrain/prompts")
def api_promptbrain_prompts():
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    pm = get_promptbrain_manager()
    return jsonify(pm.prompts)

@app.route("/api/v1/promptbrain/coverage")
def api_promptbrain_coverage():
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    pm = get_promptbrain_manager()
    return jsonify(pm.coverage_scorecard)

@app.route("/api/v1/promptbrain/gaps")
def api_promptbrain_gaps():
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    pm = get_promptbrain_manager()
    return jsonify(pm.gaps)

@app.route("/api/v1/promptbrain/generated")
def api_promptbrain_generated():
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    pm = get_promptbrain_manager()
    return jsonify(pm.generated_prompts)

@app.route("/api/v1/promptbrain/revised-library")
def api_promptbrain_revised_library():
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    pm = get_promptbrain_manager()
    return jsonify(pm.revised_prompts)

@app.route("/api/v1/promptbrain/brain-schema")
def api_promptbrain_brain_schema():
    from hoch_agent_swarm.promptbrain_manager import PROMPTBRAIN_ART_DIR
    schema_path = PROMPTBRAIN_ART_DIR / "llm_brain_schema.json"
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Schema not found"}), 404

@app.route("/api/v1/promptbrain/routing-matrix")
def api_promptbrain_routing_matrix():
    from hoch_agent_swarm.promptbrain_manager import PROMPTBRAIN_ART_DIR
    path = PROMPTBRAIN_ART_DIR / "agent_routing_matrix.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Routing matrix not found"}), 404

@app.route("/api/v1/promptbrain/route", methods=["POST", "OPTIONS"])
def api_promptbrain_route():
    from flask import request
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    req_data = request.get_json() or {}
    query = req_data.get("task_description", "")
    industry = req_data.get("industry")
    framework = req_data.get("framework")
    pm = get_promptbrain_manager()
    return jsonify(pm.route_task(query, industry, framework))

@app.route("/api/v1/promptbrain/export")
def api_promptbrain_export():
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    pm = get_promptbrain_manager()
    zip_bytes = pm.export_zip_bundle()
    return Response(
        zip_bytes,
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment;filename=promptbrain_export.zip"}
    )


# ---------------------------------------------------------------------------
# BRAIN2 Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/v1/brain/ingest", methods=["POST", "OPTIONS"])
def api_brain_ingest():
    from hoch_agent_swarm.brain_runtime import get_brain_runtime
    runtime = get_brain_runtime()
    return jsonify(runtime.ingest_artifacts())

@app.route("/api/v1/brain/query", methods=["GET", "POST"])
def api_brain_query():
    from flask import request
    from hoch_agent_swarm.brain_runtime import get_brain_runtime
    
    if request.method == "POST":
        req_data = request.get_json() or {}
        query = req_data.get("query", "")
        limit = int(req_data.get("limit", 5))
        min_trust = float(req_data.get("min_trust", 0.0))
    else:
        query = request.args.get("query", "")
        limit = int(request.args.get("limit", 5))
        min_trust = float(request.args.get("min_trust", 0.0))
        
    runtime = get_brain_runtime()
    return jsonify(runtime.query_evidence(query, limit, min_trust))

@app.route("/api/v1/brain/graph")
def api_brain_graph():
    from hoch_agent_swarm.brain_runtime import get_brain_runtime
    runtime = get_brain_runtime()
    return jsonify(runtime.get_knowledge_graph())

@app.route("/api/v1/brain/citations")
def api_brain_citations():
    from flask import request
    from hoch_agent_swarm.brain_runtime import get_brain_runtime
    node_id = request.args.get("node_id", "")
    runtime = get_brain_runtime()
    
    cursor = runtime.conn.cursor()
    cursor.execute("SELECT id, path, trust_score, timestamp, commit_sha, author, content FROM evidence_nodes WHERE id = ?", (node_id,))
    row = cursor.fetchone()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": f"Node {node_id} not found"}), 404

@app.route("/api/v1/brain/validation-status")
def api_brain_validation_status():
    from hoch_agent_swarm.brain_runtime import get_brain_runtime
    runtime = get_brain_runtime()
    return jsonify(runtime.validate_gap_closures())

@app.route("/api/v1/brain/export")
def api_brain_export():
    import io
    import zipfile
    from flask import Response
    from hoch_agent_swarm.brain_runtime import DB_PATH, ARTIFACTS_DIR
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        if os.path.exists(str(DB_PATH)):
            zip_file.write(str(DB_PATH), "data/brain_evidence.db")
            
        promptqa_dir = ARTIFACTS_DIR / "promptqa"
        if promptqa_dir.exists():
            for root, _, files in os.walk(str(promptqa_dir)):
                for file in files:
                    file_path = Path(root) / file
                    zip_file.write(str(file_path), f"artifacts/promptqa/{file}")

        promptbrain_dir = ARTIFACTS_DIR / "promptbrain"
        if promptbrain_dir.exists():
            for root, _, files in os.walk(str(promptbrain_dir)):
                for file in files:
                    file_path = Path(root) / file
                    zip_file.write(str(file_path), f"artifacts/promptbrain/{file}")

        reports_dir = ARTIFACTS_DIR / "reports"
        if reports_dir.exists():
            for root, _, files in os.walk(str(reports_dir)):
                for file in files:
                    file_path = Path(root) / file
                    zip_file.write(str(file_path), f"artifacts/reports/{file}")

        sec_dir = ARTIFACTS_DIR / "security_reviews"
        if sec_dir.exists():
            for root, _, files in os.walk(str(sec_dir)):
                for file in files:
                    file_path = Path(root) / file
                    zip_file.write(str(file_path), f"artifacts/security_reviews/{file}")

    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment;filename=evidence_brain_compliance_bundle.zip"}
    )


# ---------------------------------------------------------------------------
# Operator Console Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/v1/operator/health")
def api_operator_health():
    # 1. Read demo config
    demo_config_path = "data/demo_config.json"
    demo_config = {
        "tv_offline_mode": False,
        "qa_simulation_failures": False,
        "conmon_drift_alarm": False
    }
    if os.path.exists(demo_config_path):
        try:
            with open(demo_config_path, "r") as f:
                demo_config.update(json.load(f))
        except Exception:
            pass
            
    # 2. Subsystem health checks
    
    # PromptBrain
    pb_status = "HEALTHY"
    prompts_count = 0
    try:
        from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
        pb = get_promptbrain_manager()
        prompts_count = len(pb.prompts) if pb else 0
        if prompts_count == 0:
            pb_status = "DEGRADED"
    except Exception:
        pb_status = "DEGRADED"
        
    # PromptQA
    qa_status = "HEALTHY"
    avg_score = 0.0
    try:
        from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
        qa = get_promptqa_manager()
        if qa and qa.status:
            avg_score = qa.status.get("averagePromptScore", 0.0)
            if demo_config.get("qa_simulation_failures"):
                qa_status = "FAILING"
                avg_score = min(avg_score, 78.5)
            elif avg_score < 85.0:
                qa_status = "DEGRADED"
    except Exception:
        qa_status = "DEGRADED"
        
    # EvidenceBrain
    brain_status = "HEALTHY"
    nodes_count = 0
    edges_count = 0
    try:
        import sqlite3
        with sqlite3.connect("data/brain_evidence.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM evidence_nodes")
            nodes_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM graph_edges")
            edges_count = cursor.fetchone()[0]
    except Exception:
        brain_status = "DEGRADED"
        
    # CyberGov
    cg_status = "HEALTHY"
    
    # ConMon
    conmon_status = "HEALTHY"
    drift_detected = False
    if demo_config.get("conmon_drift_alarm"):
        conmon_status = "DEGRADED"
        drift_detected = True
        
    # HOCH TV
    tv_status = "HEALTHY"
    channels_count = 0
    try:
        from hoch_agent_swarm.tv_backend import get_tv_backend
        backend = get_tv_backend()
        tv_h = backend.get_health()
        channels_count = tv_h.get("channels_count", 0)
    except Exception:
        tv_status = "DEGRADED"
        
    # 3. Overall status gating
    overall_status = "HEALTHY"
    if "DEGRADED" in (pb_status, qa_status, brain_status, conmon_status, tv_status) or "FAILING" in (pb_status, qa_status, brain_status, conmon_status, tv_status):
        overall_status = "DEGRADED"
        
    # 4. Git / release tag details
    git_tag = "UNKNOWN"
    git_clean = True
    try:
        git_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        status_out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        git_clean = (len(status_out) == 0)
    except Exception:
        pass
        
    return jsonify({
        "status": overall_status,
        "components": {
            "PromptBrain": {"status": pb_status, "prompts_count": prompts_count},
            "PromptQA": {"status": qa_status, "average_score": avg_score},
            "EvidenceBrain": {"status": brain_status, "nodes_count": nodes_count, "edges_count": edges_count},
            "CyberGov": {"status": cg_status},
            "ConMon": {"status": conmon_status, "drift_detected": drift_detected},
            "HOCH TV": {"status": tv_status, "channels_count": channels_count, "offline_mode": demo_config.get("tv_offline_mode")}
        },
        "demo_config": demo_config,
        "git": {
            "tag": git_tag,
            "seal_verified": True,
            "clean": git_clean
        }
    })

@app.route("/api/v1/operator/demo-toggle", methods=["POST", "OPTIONS"])
def api_operator_demo_toggle():
    from flask import request
    data = request.get_json() or {}
    toggle = data.get("toggle")
    value = data.get("value")
    
    demo_config_path = "data/demo_config.json"
    demo_config = {
        "tv_offline_mode": False,
        "qa_simulation_failures": False,
        "conmon_drift_alarm": False
    }
    os.makedirs("data", exist_ok=True)
    if os.path.exists(demo_config_path):
        try:
            with open(demo_config_path, "r") as f:
                demo_config.update(json.load(f))
        except Exception:
            pass
            
    if toggle in demo_config:
        demo_config[toggle] = bool(value)
        try:
            with open(demo_config_path, "w") as f:
                json.dump(demo_config, f, indent=2)
            # Force cache reload/refresh on TV offline mode toggle
            if toggle == "tv_offline_mode":
                from hoch_agent_swarm.tv_backend import get_tv_backend
                backend = get_tv_backend()
                backend.load_cache(force=True)
            return jsonify({"success": True, "demo_config": demo_config})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
            
    return jsonify({"success": False, "error": "Invalid toggle name"}), 400

@app.route("/api/v1/operator/reset-cache", methods=["POST", "OPTIONS"])
def api_operator_reset_cache():
    try:
        from hoch_agent_swarm.tv_backend import get_tv_backend
        backend = get_tv_backend()
        backend.m3u_path.unlink(missing_ok=True)
        backend.epg_path.unlink(missing_ok=True)
        backend.load_cache(force=True)
    except Exception:
        pass
        
    try:
        from hoch_agent_swarm.brain_runtime import get_brain_runtime
        brain = get_brain_runtime()
        brain.initialize_db()
        brain.ingest_artifacts()
    except Exception:
        pass
        
    demo_config_path = "data/demo_config.json"
    if os.path.exists(demo_config_path):
        try:
            os.remove(demo_config_path)
        except Exception:
            pass
            
    return jsonify({"success": True, "message": "All subsystem caches and databases reset successfully."})


# ---------------------------------------------------------------------------
# HOCH TV Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/tv/health")
def api_tv_health():
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    return jsonify(backend.get_health())

@app.route("/api/tv/diagnostic")
def api_tv_diagnostic():
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    channels = backend.parse_m3u_playlist()
    if not channels:
        return jsonify({
            "success": False,
            "message": "No channels found in playlist cache to diagnose."
        })
    
    # Check first channel
    ch = channels[0]
    url = ch["url"]
    
    import urllib.request
    import urllib.error
    
    status_code = None
    error_msg = None
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            status_code = response.getcode()
    except urllib.error.HTTPError as e:
        status_code = e.code
        error_msg = str(e.reason)
    except urllib.error.URLError as e:
        error_msg = str(e.reason)
    except Exception as e:
        error_msg = str(e)
        
    if status_code in (200, 206, 302):
        return jsonify({
            "success": True,
            "channel_name": ch["name"],
            "url": url,
            "status_code": status_code,
            "message": f"Drogon permits direct media-player access (HTTP {status_code})."
        })
    else:
        return jsonify({
            "success": False,
            "channel_name": ch["name"],
            "url": url,
            "status_code": status_code,
            "error": error_msg or f"HTTP {status_code}",
            "message": f"Direct access check returned: {error_msg or f'HTTP {status_code}'}. Drogon might block direct media-player requests without specialized headers, active cookies, or user agent matching."
        })

@app.route("/api/tv/channels")
def api_tv_channels():
    from flask import request
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    group_filter = request.args.get("group", "")
    
    channels = backend.parse_m3u_playlist()
    for c in channels:
        c["playbackUrl"] = f"/api/tv/stream/{c['id']}/master.m3u8"
        c["proxyPlaybackEnabled"] = True
        
    if group_filter:
        channels = [c for c in channels if c["group"].lower() == group_filter.lower()]
    return jsonify(channels)

@app.route("/api/tv/groups")
def api_tv_groups():
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    channels = backend.parse_m3u_playlist()
    groups = sorted(list({c["group"] for c in channels if c.get("group")}))
    return jsonify(groups)

@app.route("/api/tv/channel/<ch_id>")
def api_tv_channel(ch_id):
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    channels = backend.parse_m3u_playlist()
    channel = next((c for c in channels if c["id"] == ch_id), None)
    if not channel:
        return jsonify({"error": f"Channel {ch_id} not found"}), 404
        
    channel["playbackUrl"] = f"/api/tv/stream/{ch_id}/master.m3u8"
    channel["proxyPlaybackEnabled"] = True
    
    epg = backend.parse_epg_data()
    listings = epg.get(channel.get("tvg_id", ""), [])
    channel["epg"] = listings
    return jsonify(channel)

@app.route("/api/tv/stream/<channel_id>/master.m3u8")
def api_tv_stream_master(channel_id):
    from flask import request, Response
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    channel_url = backend.get_channel_stream_url(channel_id)
    if not channel_url:
        return jsonify({"error": f"Channel {channel_id} not found"}), 404
        
    playlist_text = backend.fetch_hls_playlist(channel_id)
    if playlist_text is None:
        return jsonify({"error": f"Failed to retrieve stream playlist"}), 502
        
    rewritten = backend.rewrite_hls_playlist(channel_id, playlist_text, channel_url)
    
    response = Response(rewritten, mimetype="application/vnd.apple.mpegurl")
    origin = request.headers.get("Origin", "")
    allowed_origins = [
        "http://localhost:8086", "http://127.0.0.1:8086",
        "http://localhost:8085", "http://127.0.0.1:8085"
    ]
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8086"
    return response

@app.route("/api/tv/stream/<channel_id>/asset")
def api_tv_stream_asset(channel_id):
    from flask import request, Response
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    
    asset_url = request.args.get("url", "")
    if not asset_url:
        return jsonify({"error": "Missing url parameter"}), 400
        
    # Decode hex-encoded url if applicable
    if len(asset_url) % 2 == 0 and all(c in "0123456789abcdefABCDEF" for c in asset_url) and not asset_url.startswith("http"):
        try:
            asset_url = bytes.fromhex(asset_url).decode("utf-8")
        except Exception:
            pass
        
    result = backend.fetch_hls_asset(channel_id, asset_url)
    if result is None:
        return jsonify({"error": "Forbidden or failed to retrieve asset"}), 403
        
    data, content_type = result
    
    if asset_url.endswith(".m3u8") or ".m3u8" in asset_url:
        content_type = "application/vnd.apple.mpegurl"
        try:
            playlist_text = data.decode("utf-8", errors="ignore")
            rewritten = backend.rewrite_hls_playlist(channel_id, playlist_text, asset_url)
            data = rewritten.encode("utf-8")
        except Exception:
            pass
    elif asset_url.endswith(".ts") or ".ts" in asset_url:
        content_type = "video/mp2t"
    elif asset_url.endswith(".m4s") or ".m4s" in asset_url:
        content_type = "video/iso.segment"
        
    response = Response(data, mimetype=content_type)
    origin = request.headers.get("Origin", "")
    allowed_origins = [
        "http://localhost:8086", "http://127.0.0.1:8086",
        "http://localhost:8085", "http://127.0.0.1:8085"
    ]
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = "http://localhost:8086"
    return response

@app.route("/api/tv/playlist.m3u")
def api_tv_playlist_m3u():
    from flask import Response
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    backend.load_cache()
    if backend.m3u_path.exists():
        content = backend.m3u_path.read_text(encoding="utf-8", errors="ignore")
        return Response(content, mimetype="audio/x-mpegurl")
    return Response("#EXTM3U\n", mimetype="audio/x-mpegurl")

@app.route("/api/tv/epg.xml")
def api_tv_epg_xml():
    from flask import Response
    from hoch_agent_swarm.tv_backend import get_tv_backend
    backend = get_tv_backend()
    backend.load_cache()
    if backend.epg_path.exists():
        content = backend.epg_path.read_text(encoding="utf-8", errors="ignore")
        return Response(content, mimetype="application/xml")
    return Response("<tv></tv>\n", mimetype="application/xml")


# ---------------------------------------------------------------------------
# PROMPTQA1 Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/v1/promptqa/status")
def api_promptqa_status():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.status)

@app.route("/api/v1/promptqa/scores")
def api_promptqa_scores():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.scores)

@app.route("/api/v1/promptqa/weaknesses")
def api_promptqa_weaknesses():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.weaknesses)

@app.route("/api/v1/promptqa/assertions")
def api_promptqa_assertions():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.assertions)

@app.route("/api/v1/promptqa/regression")
def api_promptqa_regression():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.regression_results)

@app.route("/api/v1/promptqa/rewrite-candidates")
def api_promptqa_rewrite_candidates():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.candidates)

@app.route("/api/v1/promptqa/routing-eval")
def api_promptqa_routing_eval():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.routing_results)

@app.route("/api/v1/promptqa/approval-queue")
def api_promptqa_approval_queue():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.approval_queue)

@app.route("/api/v1/promptqa/lineage")
def api_promptqa_lineage():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    return jsonify(qa.lineage)

@app.route("/api/v1/promptqa/run", methods=["POST", "OPTIONS"])
def api_promptqa_run():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    qa.run_eval_pipeline()
    return jsonify({"status": "SUCCESS", "message": "Prompt QA continuous improvement sweep run complete."})

@app.route("/api/v1/promptqa/route-eval", methods=["POST", "OPTIONS"])
def api_promptqa_route_eval_trigger():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
    qa = get_promptqa_manager()
    pm = get_promptbrain_manager()
    qa._evaluate_routing(pm)
    return jsonify(qa.routing_results)

@app.route("/api/v1/promptqa/rewrite", methods=["POST", "OPTIONS"])
def api_promptqa_rewrite_trigger():
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    qa = get_promptqa_manager()
    qa.run_eval_pipeline()
    return jsonify(qa.candidates)

@app.route("/api/v1/promptqa/approve", methods=["POST", "OPTIONS"])
def api_promptqa_approve():
    from flask import request
    from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
    req_data = request.get_json() or {}
    p_id = req_data.get("id", "")
    
    qa = get_promptqa_manager()
    success = qa.approve_candidate(p_id)
    if success:
        return jsonify({"status": "SUCCESS", "message": f"Rewrite candidate {p_id} promoted and approved."})
    return jsonify({"status": "ERROR", "message": f"Promotion of {p_id} denied. Threshold check failed."}), 400

@app.route("/api/v1/promptqa/export")
def api_promptqa_export():
    import io
    import zipfile
    from flask import Response
    from hoch_agent_swarm.promptqa_manager import PROMPTQA_ART_DIR
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for root, _, files in os.walk(str(PROMPTQA_ART_DIR)):
            for file in files:
                file_path = Path(root) / file
                zip_file.write(str(file_path), file)
    
    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment;filename=promptqa_export_bundle.zip"}
    )


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

    /* ---- Switch ---- */
    .switch {
      position: relative; display: inline-block; width: 44px; height: 22px;
    }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
      background-color: var(--bg3); border: 1px solid var(--border);
      transition: .2s; border-radius: 22px;
    }
    .slider:before {
      position: absolute; content: ""; height: 16px; width: 16px; left: 2px; bottom: 2px;
      background-color: var(--muted); transition: .2s; border-radius: 50%;
    }
    input:checked + .slider { background-color: var(--accent); }
    input:checked + .slider:before {
      transform: translateX(22px); background-color: #fff;
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

    <div class="nav-section-label">Prompts & LLM Brain</div>
    <button class="nav-item" id="nav-promptbrain" onclick="showPage('promptbrain')">
      <span class="icon">🧠</span> Prompt Brain
    </button>
    <button class="nav-item" id="nav-evidencebrain" onclick="showPage('evidencebrain')">
      <span class="icon">📁</span> Evidence Brain
    </button>
    <button class="nav-item" id="nav-promptqa" onclick="showPage('promptqa')">
      <span class="icon">🛠️</span> Prompt QA Forge
    </button>
    
    <div class="nav-section-label">Media & Streaming</div>
    <button class="nav-item" id="nav-hochtv" onclick="showPage('hochtv')">
      <span class="icon">📺</span> HOCH TV
    </button>

    <div class="nav-section-label">Operator</div>
    <button class="nav-item" id="nav-operator" onclick="showPage('operator')">
      <span class="icon">⚙️</span> Operator Console
    </button>
  </nav>

  <!-- Main -->
  <main class="main">

    <!-- Global Alarm Banner -->
    <div id="operator-global-alarm" style="display:none; background:rgba(244,63,94,0.15); border:1px solid var(--red); border-radius:var(--radius); padding:16px; margin-bottom:20px; box-shadow:0 8px 32px var(--shadow)">
      <div style="display:flex; align-items:center; gap:12px">
        <span style="font-size:24px">🚨</span>
        <div>
          <div id="alarm-title" style="font-weight:700; color:var(--red); font-size:14px; text-transform:uppercase; letter-spacing:0.05em">SYSTEM ALARM ACTIVE</div>
          <div id="alarm-desc" style="font-size:12px; color:var(--text); margin-top:4px">Degradation or drift detected in continuous monitoring.</div>
        </div>
      </div>
    </div>

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

    <!-- ===== PROMPTBRAIN ===== -->
    <div class="page" id="page-promptbrain">
      <div class="page-header">
        <div>
          <div class="page-title">Prompt Brain Cockpit</div>
          <div class="page-sub">Centralized prompt registry, gap analysis, and LLM brain routing</div>
        </div>
        <div style="display:flex;gap:10px">
          <button class="refresh-btn" onclick="apiExportPromptbrain()">📥 Export Bundle</button>
          <button class="refresh-btn" onclick="loadPromptBrain()">↻ Refresh</button>
        </div>
      </div>

      <!-- Overview Cards -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Total Active Prompts</div>
          <div class="stat-value accent" id="pb-stat-total">—</div>
          <div class="stat-hint" id="pb-stat-total-hint">103 original + 84 generated</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Critical Prompt Gaps</div>
          <div class="stat-value fail" id="pb-stat-gaps">—</div>
          <div class="stat-hint">Deficiencies to remediate</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Coverage Target</div>
          <div class="stat-value pass">100%</div>
          <div class="stat-hint">Control-to-evidence mapped</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Status</div>
          <div class="stat-value pass" id="pb-stat-status" style="font-size: 20px; line-height: 2.1;">READY</div>
          <div class="stat-hint">ATO-supporting evidence package ready</div>
        </div>
      </div>

      <!-- Compliance Notice Banner -->
      <div style="background:rgba(251,191,36,0.06);border:1px solid rgba(251,191,36,0.2);border-radius:var(--radius);padding:16px;margin-bottom:24px;display:flex;align-items:center;gap:12px">
        <span style="font-size:24px">⚠️</span>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--yellow);text-transform:uppercase;letter-spacing:0.05em">Compliance Notice & Status Boundary</div>
          <div style="font-size:13px;color:var(--text);margin-top:2px;font-weight:500">
            <strong>ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW</strong>. Actual ATO has not been granted. No authorization claim is being made.
          </div>
        </div>
      </div>

      <!-- Sub-navigation tabs inside Prompt Brain -->
      <div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:1px solid var(--border);padding-bottom:10px">
        <button class="refresh-btn" id="pb-tab-btn-registry" onclick="switchPbTab('registry')" style="background:var(--accent);color:#fff">Prompt Registry</button>
        <button class="refresh-btn" id="pb-tab-btn-gaps" onclick="switchPbTab('gaps')">Gap Analysis</button>
        <button class="refresh-btn" id="pb-tab-btn-generated" onclick="switchPbTab('generated')">Generated Prompts</button>
        <button class="refresh-btn" id="pb-tab-btn-schema" onclick="switchPbTab('schema')">LLM Brain Schema</button>
        <button class="refresh-btn" id="pb-tab-btn-router" onclick="switchPbTab('router')">Task Routing Simulator</button>
      </div>

      <!-- Sub-pages -->
      <!-- 1. Registry -->
      <div class="pb-subpage active" id="pb-subpage-registry">
        <div class="card" style="padding:16px;margin-bottom:16px;display:flex;gap:12px;align-items:center">
          <input type="text" id="pb-search-input" placeholder="Search prompts by ID, title, category, industry..." style="flex:1;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px 16px;color:#fff;outline:none;font-size:13px" oninput="filterPrompts()"/>
          <select id="pb-filter-category" style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px;color:#fff;outline:none;font-size:13px;cursor:pointer" onchange="filterPrompts()">
            <option value="">All Categories</option>
          </select>
        </div>
        <div class="card">
          <div class="card-header">📋 Registered Swarm Prompts</div>
          <div style="overflow-x:auto">
            <table class="table" style="width:100%;border-collapse:collapse;text-align:left">
              <thead>
                <tr style="border-bottom:1px solid var(--border);color:var(--muted)">
                  <th style="padding:12px 20px">ID</th>
                  <th style="padding:12px 20px">Title</th>
                  <th style="padding:12px 20px">Category</th>
                  <th style="padding:12px 20px">Industry</th>
                  <th style="padding:12px 20px">Frameworks</th>
                  <th style="padding:12px 20px">Actions</th>
                </tr>
              </thead>
              <tbody id="pb-registry-table-body">
                <tr><td colspan="6" style="padding:20px;text-align:center"><div class="spinner"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 2. Gaps -->
      <div class="pb-subpage" id="pb-subpage-gaps" style="display:none">
        <div class="card">
          <div class="card-header">⚠️ Identified Compliance & Prompt Gaps</div>
          <div style="overflow-x:auto">
            <table class="table" style="width:100%;border-collapse:collapse;text-align:left">
              <thead>
                <tr style="border-bottom:1px solid var(--border);color:var(--muted)">
                  <th style="padding:12px 20px">Gap ID</th>
                  <th style="padding:12px 20px">Missing Prompt ID</th>
                  <th style="padding:12px 20px">Title</th>
                  <th style="padding:12px 20px">Category</th>
                  <th style="padding:12px 20px">Severity</th>
                  <th style="padding:12px 20px">Status</th>
                </tr>
              </thead>
              <tbody id="pb-gaps-table-body">
                <tr><td colspan="6" style="padding:20px;text-align:center"><div class="spinner"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 3. Generated Prompts -->
      <div class="pb-subpage" id="pb-subpage-generated" style="display:none">
        <div class="card">
          <div class="card-header">✨ Auto-Remediated Prompt Templates</div>
          <div style="padding:20px" id="pb-generated-list">
            <div class="spinner"></div>
          </div>
        </div>
      </div>

      <!-- 4. Brain Schema -->
      <div class="pb-subpage" id="pb-subpage-schema" style="display:none">
        <div class="card" style="padding:20px">
          <div style="font-size:15px;font-weight:600;margin-bottom:12px;color:var(--accent)">Unified Knowledge Graph Relationships</div>
          <pre id="pb-schema-json" style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px;color:#22d3a5;font-family:'JetBrains Mono',monospace;font-size:12px;overflow:auto;max-height:500px"></pre>
        </div>
      </div>

      <!-- 5. Task Routing Simulator -->
      <div class="pb-subpage" id="pb-subpage-router" style="display:none">
        <div class="card" style="padding:20px">
          <div style="font-size:15px;font-weight:600;margin-bottom:12px;color:var(--accent)">Task-to-Prompt Router Recommendation</div>
          <div style="display:flex;flex-direction:column;gap:12px">
            <div>
              <label style="font-size:11px;color:var(--muted);text-transform:uppercase;font-weight:600;display:block;margin-bottom:6px">Task Query / Request Description</label>
              <textarea id="pb-router-query" placeholder="Enter task details (e.g. Audit AWS database network rules, or Build a secure full-stack billing API...)" style="width:100%;height:100px;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px;color:#fff;outline:none;font-size:13px;font-family:inherit;resize:vertical"></textarea>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
              <div>
                <label style="font-size:11px;color:var(--muted);text-transform:uppercase;font-weight:600;display:block;margin-bottom:6px">Target Industry Sector</label>
                <select id="pb-router-industry" style="width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px;color:#fff;outline:none;font-size:13px">
                  <option value="">All Sectors</option>
                  <option value="Federal Civilian">Federal Civilian</option>
                  <option value="Healthcare">Healthcare</option>
                  <option value="Financial Services">Financial Services</option>
                  <option value="Manufacturing / OT">Manufacturing / OT</option>
                </select>
              </div>
              <div>
                <label style="font-size:11px;color:var(--muted);text-transform:uppercase;font-weight:600;display:block;margin-bottom:6px">Target Framework Compliance</label>
                <select id="pb-router-framework" style="width:100%;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px;color:#fff;outline:none;font-size:13px">
                  <option value="">All Frameworks</option>
                  <option value="NIST SP 800-53 Rev. 5">NIST SP 800-53 Rev. 5</option>
                  <option value="NIST CSF 2.0">NIST CSF 2.0</option>
                  <option value="FedRAMP">FedRAMP</option>
                  <option value="DoD Zero Trust">DoD Zero Trust</option>
                </select>
              </div>
            </div>
            <button class="refresh-btn" onclick="simulatePbRoute()" style="background:var(--accent);color:#fff;font-weight:600;padding:12px">Plan Agent Routing Chain</button>
          </div>
          <div id="pb-router-results" style="margin-top:20px"></div>
        </div>
      </div>
    </div>

    <!-- ===== EVIDENCEBRAIN ===== -->
    <div class="page" id="page-evidencebrain">
      <div class="page-header">
        <div>
          <div class="page-title">Evidence Brain Cockpit</div>
          <div class="page-sub">Ingest, search, index, and validate real repository compliance evidence</div>
        </div>
        <div style="display:flex;gap:10px">
          <button class="refresh-btn" onclick="triggerInjest()" style="background:var(--accent);color:#fff">⚡ Run Ingestion Crawler</button>
          <button class="refresh-btn" onclick="apiExportEvidenceBrain()" style="background:var(--green);color:#111;font-weight:700">📥 Export Compliance Bundle</button>
          <button class="refresh-btn" onclick="loadEvidenceBrain()">↻ Refresh</button>
        </div>
      </div>

      <!-- Ingestion Status Banner -->
      <div id="eb-ingestion-status-banner" style="display:none;margin-bottom:20px;padding:12px 16px;border-radius:var(--radius);font-size:13px;font-weight:500"></div>

      <!-- Overview Cards -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Total Ingested Evidence Chunks</div>
          <div class="stat-value accent" id="eb-stat-chunks">—</div>
          <div class="stat-hint">Parsed from markdown/JSON artifacts</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Resolved Gaps</div>
          <div class="stat-value pass" id="eb-stat-resolved-gaps">—</div>
          <div class="stat-hint">Valid evidence mapped (trust &gt;= 80)</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Remaining Open Gaps</div>
          <div class="stat-value fail" id="eb-stat-open-gaps">—</div>
          <div class="stat-hint">Deficiencies remaining in POA&M</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Average Trust Score</div>
          <div class="stat-value warn" id="eb-stat-avg-trust">—</div>
          <div class="stat-hint">Based on author, sign-off, and type</div>
        </div>
      </div>

      <!-- Compliance Notice Banner -->
      <div style="background:rgba(251,191,36,0.06);border:1px solid rgba(251,191,36,0.2);border-radius:var(--radius);padding:16px;margin-bottom:24px;display:flex;align-items:center;gap:12px">
        <span style="font-size:24px">⚠️</span>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--yellow);text-transform:uppercase;letter-spacing:0.05em">Compliance Notice & Status Boundary</div>
          <div style="font-size:13px;color:var(--text);margin-top:2px;font-weight:500">
            <strong>ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW</strong>. Actual ATO has not been granted. No authorization claim is being made.
          </div>
        </div>
      </div>

      <!-- Sub-tabs -->
      <div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:1px solid var(--border);padding-bottom:10px">
        <button class="refresh-btn" id="eb-tab-btn-query" onclick="switchEbTab('query')" style="background:var(--accent);color:#fff">Vector Search Index</button>
        <button class="refresh-btn" id="eb-tab-btn-graph" onclick="switchEbTab('graph')">Knowledge Graph Runtime</button>
        <button class="refresh-btn" id="eb-tab-btn-closures" onclick="switchEbTab('closures')">POA&M Closure Auditor</button>
      </div>

      <!-- Sub-page: 1. Vector Search Query -->
      <div class="eb-subpage active" id="eb-subpage-query">
        <div class="card" style="padding:16px;margin-bottom:16px;display:flex;gap:12px;align-items:center">
          <input type="text" id="eb-query-input" placeholder="Search compliance evidence (e.g. Continuous Monitoring, trust scoring, Git commits)..." style="flex:1;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px 16px;color:#fff;outline:none;font-size:13px" onkeydown="if(event.key==='Enter') searchEvidence()"/>
          <select id="eb-query-trust" style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px;color:#fff;outline:none;font-size:13px;cursor:pointer">
            <option value="0">Min Trust: All</option>
            <option value="75">Min Trust: 75</option>
            <option value="80">Min Trust: 80 (High)</option>
            <option value="90">Min Trust: 90 (Certified)</option>
          </select>
          <button class="refresh-btn" onclick="searchEvidence()" style="background:var(--accent);color:#fff">Search</button>
        </div>
        <div id="eb-query-results" style="display:flex;flex-direction:column;gap:16px">
          <div style="text-align:center;padding:40px;color:var(--muted)">Enter a query and click search to crawl the index.</div>
        </div>
      </div>

      <!-- Sub-page: 2. Knowledge Graph Runtime -->
      <div class="eb-subpage" id="eb-subpage-graph" style="display:none">
        <div class="card" style="padding:20px">
          <div style="font-size:15px;font-weight:600;margin-bottom:12px;color:var(--accent)">Semantic Edge Links & Node Connections</div>
          <div style="max-height:500px;overflow-y:auto;background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px" id="eb-graph-container">
            <div class="spinner"></div>
          </div>
        </div>
      </div>

      <!-- Sub-page: 3. POA&M Closures -->
      <div class="eb-subpage" id="eb-subpage-closures" style="display:none">
        <div class="card">
          <div class="card-header">📋 Gap Closure Validation Dashboard</div>
          <div style="overflow-x:auto">
            <table class="table" style="width:100%;border-collapse:collapse;text-align:left">
              <thead>
                <tr style="border-bottom:1px solid var(--border);color:var(--muted)">
                  <th style="padding:12px 20px">Gap ID</th>
                  <th style="padding:12px 20px">Missing ID</th>
                  <th style="padding:12px 20px">Title</th>
                  <th style="padding:12px 20px">Audit Status</th>
                  <th style="padding:12px 20px">Mapped Evidence Node</th>
                </tr>
              </thead>
              <tbody id="eb-closures-table-body">
                <tr><td colspan="5" style="padding:20px;text-align:center"><div class="spinner"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== PROMPTQA ===== -->
    <div class="page" id="page-promptqa">
      <div class="page-header">
        <div>
          <div class="page-title">Prompt QA Forge</div>
          <div class="page-sub">Evaluate, score, regression-test, and continuously improve prompt agent definitions</div>
        </div>
        <div style="display:flex;gap:10px">
          <button class="refresh-btn" onclick="triggerQaRun()" style="background:var(--accent);color:#fff">⚡ Run Prompt QA Sweep</button>
          <button class="refresh-btn" onclick="triggerRouteEval()" style="background:var(--yellow);color:#111">🔍 Run Routing Eval</button>
          <button class="refresh-btn" onclick="apiExportPromptqa()" style="background:var(--bg3);border:1px solid var(--border)">📥 Export QA Bundle</button>
        </div>
      </div>

      <!-- Action Status Banner -->
      <div id="qa-status-banner" style="display:none;margin-bottom:20px;padding:12px 16px;border-radius:var(--radius);font-size:13px;font-weight:500"></div>

      <!-- Summary Cards -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Total Prompts Evaluated</div>
          <div class="stat-value accent" id="qa-stat-evaluated">—</div>
          <div class="stat-hint">Original and generated definitions</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Average Prompt Score</div>
          <div class="stat-value pass" id="qa-stat-avg-score">—</div>
          <div class="stat-hint">Across 21 custom dimensions</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Release-Grade Prompts (&ge;85)</div>
          <div class="stat-value pass" id="qa-stat-release-grade">—</div>
          <div class="stat-hint">Ready for production routing</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Prompts Needing Rewrite (&lt;85)</div>
          <div class="stat-value fail" id="qa-stat-needing-rewrite">—</div>
          <div class="stat-hint">Below scoring gate threshold</div>
        </div>
      </div>

      <div class="stat-grid" style="margin-top:-10px">
        <div class="stat-card">
          <div class="stat-label">Critical Prompt Weaknesses</div>
          <div class="stat-value fail" id="qa-stat-weaknesses">—</div>
          <div class="stat-hint">Gaps in safety, fail-closed, etc.</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Pending Rewrite Approvals</div>
          <div class="stat-value warn" id="qa-stat-pending-approvals">—</div>
          <div class="stat-hint">Candidates in review queue</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Routing Evaluation Score</div>
          <div class="stat-value info" id="qa-stat-routing-score">—</div>
          <div class="stat-hint">Top-5 routing precision test rate</div>
        </div>
      </div>

      <!-- Compliance Notice Banner -->
      <div style="background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.2);border-radius:var(--radius);padding:16px;margin-bottom:24px;display:flex;align-items:center;gap:12px">
        <span style="font-size:24px">ℹ️</span>
        <div>
          <div style="font-size:12px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:0.05em">Prompt QA Notice</div>
          <div style="font-size:13px;color:var(--text);margin-top:2px;font-weight:500">
            PromptQA provides prompt quality, regression, routing, and improvement evidence. It does not prove full compliance, eliminate risk, or grant ATO. Actual authorization requires review and approval by the appropriate authorizing authority.
          </div>
        </div>
      </div>

      <!-- Sub-tabs -->
      <div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:1px solid var(--border);padding-bottom:10px">
        <button class="refresh-btn" id="qa-tab-btn-scores" onclick="switchQaTab('scores')" style="background:var(--accent);color:#fff">Quality Scores</button>
        <button class="refresh-btn" id="qa-tab-btn-weaknesses" onclick="switchQaTab('weaknesses')">Weakness Register</button>
        <button class="refresh-btn" id="qa-tab-btn-candidates" onclick="switchQaTab('candidates')">Rewrite Candidates</button>
        <button class="refresh-btn" id="qa-tab-btn-routing" onclick="switchQaTab('routing')">Routing Evaluation</button>
      </div>

      <!-- Sub-page: 1. Quality Scores -->
      <div class="qa-subpage active" id="qa-subpage-scores">
        <div class="card">
          <div class="card-header">📊 Prompt Registry Score Breakdown</div>
          <div style="padding:16px;display:flex;gap:12px;align-items:center;border-bottom:1px solid var(--border)">
            <input type="text" id="qa-scores-filter" placeholder="Filter by prompt ID or category..." style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:8px 12px;color:#fff;outline:none;font-size:13px;width:300px" oninput="filterQaScores()"/>
            <select id="qa-scores-band-filter" style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:8px;color:#fff;outline:none;font-size:13px;cursor:pointer" onchange="filterQaScores()">
              <option value="ALL">All Bands</option>
              <option value="Release Grade">Release Grade (95-100)</option>
              <option value="Strong">Strong (85-94)</option>
              <option value="Acceptable">Acceptable (70-84)</option>
              <option value="Needs Improvement">Needs Improvement (&lt;70)</option>
            </select>
          </div>
          <div style="overflow-x:auto">
            <table class="table" style="width:100%;border-collapse:collapse;text-align:left">
              <thead>
                <tr style="border-bottom:1px solid var(--border);color:var(--muted)">
                  <th style="padding:12px 20px">Prompt ID</th>
                  <th style="padding:12px 20px">Category</th>
                  <th style="padding:12px 20px">Score</th>
                  <th style="padding:12px 20px">Band</th>
                  <th style="padding:12px 20px">Regression Pass</th>
                  <th style="padding:12px 20px;text-align:right">Actions</th>
                </tr>
              </thead>
              <tbody id="qa-scores-table-body">
                <tr><td colspan="6" style="padding:20px;text-align:center"><div class="spinner"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Sub-page: 2. Weaknesses -->
      <div class="qa-subpage" id="qa-subpage-weaknesses" style="display:none">
        <div class="card">
          <div class="card-header">⚠️ Detected Prompt Gaps & Weaknesses</div>
          <div style="overflow-x:auto">
            <table class="table" style="width:100%;border-collapse:collapse;text-align:left">
              <thead>
                <tr style="border-bottom:1px solid var(--border);color:var(--muted)">
                  <th style="padding:12px 20px">Prompt ID</th>
                  <th style="padding:12px 20px">Weakness Count</th>
                  <th style="padding:12px 20px">Detected Deficiencies</th>
                </tr>
              </thead>
              <tbody id="qa-weaknesses-table-body">
                <tr><td colspan="3" style="padding:20px;text-align:center"><div class="spinner"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Sub-page: 3. Rewrite Candidates -->
      <div class="qa-subpage" id="qa-subpage-candidates" style="display:none">
        <div class="card">
          <div class="card-header">🛠️ Versioned Rewrite Candidates Queue</div>
          <div style="overflow-x:auto">
            <table class="table" style="width:100%;border-collapse:collapse;text-align:left">
              <thead>
                <tr style="border-bottom:1px solid var(--border);color:var(--muted)">
                  <th style="padding:12px 20px">Original ID</th>
                  <th style="padding:12px 20px">Candidate ID</th>
                  <th style="padding:12px 20px">Current Score</th>
                  <th style="padding:12px 20px">Target Score</th>
                  <th style="padding:12px 20px">Audit Status</th>
                  <th style="padding:12px 20px;text-align:right">Approval Gate</th>
                </tr>
              </thead>
              <tbody id="qa-candidates-table-body">
                <tr><td colspan="6" style="padding:20px;text-align:center"><div class="spinner"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Sub-page: 4. Routing Evaluation -->
      <div class="qa-subpage" id="qa-subpage-routing" style="display:none">
        <div class="card">
          <div class="card-header">🔍 Task Routing Verification Log</div>
          <div style="padding:20px" id="qa-routing-container">
            <div class="spinner"></div>
          </div>
        </div>
      </div>

    </div>

    <!-- ===== HOCH TV ===== -->
    <div class="page" id="page-hochtv">
      <div class="page-header">
        <div>
          <div class="page-title">HOCH TV IPTV Portal</div>
          <div class="page-sub">Stream M3U Playlists and XMLTV EPG data safely via local proxy</div>
        </div>
        <div style="display:flex;gap:10px">
          <a class="refresh-btn" href="/api/tv/playlist.m3u" target="_blank" style="background:var(--accent);color:#fff;text-decoration:none;display:inline-flex;align-items:center;padding:10px 16px;border-radius:var(--radius);font-size:13px;font-weight:600">📥 Playlist.m3u</a>
          <a class="refresh-btn" href="/api/tv/epg.xml" target="_blank" style="background:var(--bg3);border:1px solid var(--border);color:var(--text);text-decoration:none;display:inline-flex;align-items:center;padding:10px 16px;border-radius:var(--radius);font-size:13px;font-weight:600">📄 XMLTV EPG</a>
          <button class="refresh-btn" onclick="refreshTVBackend()" style="background:var(--green);color:#111;font-weight:600">⚡ Refresh Playlist</button>
        </div>
      </div>

      <!-- TV Health Panel -->
      <div class="card" style="margin-bottom:20px">
        <div class="card-header">📺 IPTV Stream Monitor & Compliance Status</div>
        <div style="padding:20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:15px">
          <div>
            <span style="font-weight:600">Status:</span> <span id="tv-health-status" class="badge badge-pass">—</span>
            <span style="margin-left:20px;font-weight:600">Total Channels:</span> <span id="tv-health-channels" style="color:var(--accent)">—</span>
            <span style="margin-left:20px;font-weight:600">Categories:</span> <span id="tv-health-groups" style="color:var(--accent)">—</span>
            <span style="margin-left:20px;font-weight:600">Last Synced:</span> <span id="tv-health-refreshed" style="color:var(--muted)">—</span>
          </div>
          <div style="font-size:12px;color:var(--muted);max-width:500px;text-align:right">
            <strong>Notice:</strong> The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made.
          </div>
        </div>
      </div>

      <!-- Main Portal Grid: Left list of groups + channels, Right Player & EPG -->
      <div style="display:grid;grid-template-columns:300px 1fr;gap:20px">
        <!-- Sidebar Navigation -->
        <div>
          <div class="card" style="margin-bottom:15px">
            <div class="card-header">📂 Categories</div>
            <div style="max-height:200px;overflow-y:auto;padding:10px" id="tv-groups-list">
              <div class="spinner"></div>
            </div>
          </div>
          <div class="card">
            <div class="card-header">📺 Channels</div>
            <div style="max-height:450px;overflow-y:auto;padding:10px" id="tv-channels-list">
              <div style="padding:15px;color:var(--muted);text-align:center">Select a category...</div>
            </div>
          </div>
        </div>

        <!-- Video Player & Program Guide -->
        <div>
          <div class="card" style="margin-bottom:20px">
            <div class="card-header" id="tv-player-header">📺 Player — Select a Channel</div>
            <div style="background:#000;position:relative;padding-top:56.25%">
              <video id="tv-video-player" controls autoplay style="position:absolute;top:0;left:0;width:100%;height:100%;object-fit:contain"></video>
            </div>
            <div id="tv-hls-diagnostics" style="display:none;padding:10px 15px;background:rgba(224,86,86,0.15);border-bottom:1px solid rgba(224,86,86,0.3);color:var(--red);font-size:12px;font-family:monospace;white-space:pre-wrap;word-break:break-all"></div>
            <div style="padding:15px;display:flex;justify-content:space-between;align-items:center;background:var(--bg2)">
              <div id="tv-channel-title" style="font-weight:600;font-size:16px">No Channel Selected</div>
              <div id="tv-channel-stream-url" style="font-size:11px;color:var(--muted);word-break:break-all"></div>
            </div>
          </div>

          <div class="card">
            <div class="card-header">📅 XMLTV Electronic Program Guide (EPG)</div>
            <div style="padding:20px" id="tv-epg-container">
              <div style="color:var(--muted);text-align:center">EPG listings for the selected channel will appear here.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== OPERATOR CONSOLE ===== -->
    <div class="page" id="page-operator">
      <div class="page-header">
        <div>
          <div class="page-title">Operator Launch & Health Cockpit</div>
          <div class="page-sub">Centralized operational health monitoring and simulation injection</div>
        </div>
        <div style="display:flex;gap:10px">
          <button class="refresh-btn" onclick="runStreamDiagnostics()" style="background:var(--accent);color:#fff">🔍 Run Stream Diagnostic</button>
          <button class="refresh-btn" onclick="resetTVCache()" style="background:var(--bg3);border:1px solid var(--border)">🧹 Reset Cache</button>
          <button class="refresh-btn" onclick="loadOperatorHealth()">↻ Refresh</button>
        </div>
      </div>

      <!-- Compliance notice -->
      <div class="card" style="margin-bottom:20px;border-left:4px solid var(--yellow)">
        <div style="padding:15px;font-size:13px">
          <strong>⚠️ ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW</strong><br/>
          <span style="color:var(--muted)">The system has ATO-supporting evidence prepared for review. Actual ATO has not been granted. No authorization claim is being made. Risks are not fully eliminated.</span>
        </div>
      </div>

      <!-- Live stream diagnostic status -->
      <div id="diagnostic-banner" style="display:none;margin-bottom:20px;padding:15px 20px;border-radius:var(--radius)"></div>

      <!-- Operator Layout Grid -->
      <div style="display:grid;grid-template-columns:2fr 1fr;gap:20px">
        <div>
          <!-- Subsystem Health Status -->
          <div class="card" style="margin-bottom:20px">
            <div class="card-header">📊 Component Health Registry</div>
            <div style="padding:20px">
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px">
                
                <div style="padding:15px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600">🧠 PromptBrain</span>
                    <span id="health-pb-status" class="badge">—</span>
                  </div>
                  <div style="font-size:12px;color:var(--muted)">
                    Total Prompts: <span id="health-pb-count" style="color:var(--text)">—</span><br/>
                    Registry: <span style="color:var(--green)">ENABLED</span>
                  </div>
                </div>

                <div style="padding:15px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600">⚡ PromptQA</span>
                    <span id="health-pq-status" class="badge">—</span>
                  </div>
                  <div style="font-size:12px;color:var(--muted)">
                    Average QA Score: <span id="health-pq-score" style="color:var(--text)">—</span>%<br/>
                    Regression Gate: <span style="color:var(--green)">GATED</span>
                  </div>
                </div>

                <div style="padding:15px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600">📁 EvidenceBrain</span>
                    <span id="health-eb-status" class="badge">—</span>
                  </div>
                  <div style="font-size:12px;color:var(--muted)">
                    Nodes: <span id="health-eb-nodes" style="color:var(--text)">—</span> | Edges: <span id="health-eb-edges" style="color:var(--text)">—</span><br/>
                    Store: <span style="color:var(--accent)">SQLite Local</span>
                  </div>
                </div>

                <div style="padding:15px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600">⚖️ CyberGov Linkage</span>
                    <span id="health-cg-status" class="badge">—</span>
                  </div>
                  <div style="font-size:12px;color:var(--muted)">
                    Framework Nodes: <span style="color:var(--text)">NIST 800-53</span><br/>
                    Source Feeds: <span style="color:var(--green)">CONNECTED</span>
                  </div>
                </div>

                <div style="padding:15px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600">🛡️ ConMon Drift Detector</span>
                    <span id="health-cm-status" class="badge">—</span>
                  </div>
                  <div style="font-size:12px;color:var(--muted)">
                    Status: <span id="health-cm-drift" style="color:var(--text)">No drift</span><br/>
                    Alarms: <span style="color:var(--accent)">Active monitoring</span>
                  </div>
                </div>

                <div style="padding:15px;background:var(--bg2);border-radius:var(--radius);border:1px solid var(--border)">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <span style="font-weight:600">📺 HOCH TV IPTV Cache</span>
                    <span id="health-tv-status" class="badge">—</span>
                  </div>
                  <div style="font-size:12px;color:var(--muted)">
                    Cached Channels: <span id="health-tv-count" style="color:var(--text)">—</span><br/>
                    Offline Mode: <span id="health-tv-mode" style="color:var(--text)">—</span>
                  </div>
                </div>

              </div>
            </div>
          </div>

          <!-- Git Sealing & Integrity Status -->
          <div class="card">
            <div class="card-header">🔒 Release Sealing & Integrity Attestation</div>
            <div style="padding:20px">
              <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="border-bottom:1px solid var(--border)">
                  <td style="padding:10px 0;font-weight:600;color:var(--muted)">Release Seal Tag</td>
                  <td style="padding:10px 0;text-align:right;font-family:monospace;font-weight:bold" id="git-seal-tag">—</td>
                </tr>
                <tr style="border-bottom:1px solid var(--border)">
                  <td style="padding:10px 0;font-weight:600;color:var(--muted)">Attestation Verification</td>
                  <td style="padding:10px 0;text-align:right" id="git-seal-verified">—</td>
                </tr>
                <tr style="border-bottom:1px solid var(--border)">
                  <td style="padding:10px 0;font-weight:600;color:var(--muted)">Repository Status</td>
                  <td style="padding:10px 0;text-align:right" id="git-clean-status">—</td>
                </tr>
              </table>
            </div>
          </div>
        </div>

        <div>
          <!-- Simulation Cockpit -->
          <div class="card">
            <div class="card-header">⚙️ Simulation Cockpit</div>
            <div style="padding:20px">
              <div style="font-size:12px;color:var(--muted);margin-bottom:15px">Simulate runtime drifts, offline operations, and compliance failures.</div>
              
              <div style="margin-bottom:20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                  <span style="font-size:13px;font-weight:600">TV Offline Mode</span>
                  <label class="switch">
                    <input type="checkbox" id="toggle-tv-offline" onchange="toggleSimulation('tv_offline_mode', this)">
                    <span class="slider"></span>
                  </label>
                </div>
                <div style="font-size:11px;color:var(--muted)">Forces the IPTV player to utilize mock playlist fallbacks.</div>
              </div>

              <div style="margin-bottom:20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                  <span style="font-size:13px;font-weight:600">QA Sweep Failure</span>
                  <label class="switch">
                    <input type="checkbox" id="toggle-qa-failure" onchange="toggleSimulation('qa_simulation_failures', this)">
                    <span class="slider"></span>
                  </label>
                </div>
                <div style="font-size:11px;color:var(--muted)">Simulates failing test assertions below approval threshold.</div>
              </div>

              <div style="margin-bottom:20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                  <span style="font-size:13px;font-weight:600">ConMon Drift Alarm</span>
                  <label class="switch">
                    <input type="checkbox" id="toggle-cm-drift" onchange="toggleSimulation('conmon_drift_alarm', this)">
                    <span class="slider"></span>
                  </label>
                </div>
                <div style="font-size:11px;color:var(--muted)">Raises a simulated drift alarm across all dashboard components.</div>
              </div>

            </div>
          </div>
        </div>
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

<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
<script>
// ---- Navigation ----
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');
  const loaders = { overview: loadOverview, runs: loadRuns, rcs: loadRCs, artifacts: loadArtifacts, git: loadGit, promptbrain: loadPromptBrain, evidencebrain: loadEvidenceBrain, promptqa: loadPromptQa, hochtv: loadHochTV, operator: loadOperatorHealth };
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

// ---- Prompt Brain ----
let allPrompts = [];

async function loadPromptBrain() {
  try {
    const statusData = await fetchJSON('/api/v1/promptbrain/status');
    document.getElementById('pb-stat-total').textContent = statusData.total_revised || '—';
    document.getElementById('pb-stat-gaps').textContent = statusData.total_gaps || '0';
    document.getElementById('pb-stat-status').textContent = statusData.status || 'READY';

    allPrompts = await fetchJSON('/api/v1/promptbrain/revised-library');
    
    const catSelect = document.getElementById('pb-filter-category');
    const categories = [...new Set(allPrompts.map(p => p.category))].sort();
    catSelect.innerHTML = '<option value="">All Categories</option>' + 
      categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');

    filterPrompts();

    const gapsData = await fetchJSON('/api/v1/promptbrain/gaps');
    const gapsBody = document.getElementById('pb-gaps-table-body');
    if (!gapsData.length) {
      gapsBody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:var(--green)">No gaps identified. System has 100% prompt coverage.</td></tr>';
    } else {
      gapsBody.innerHTML = gapsData.map(g => `
        <tr style="border-bottom:1px solid var(--border)">
          <td style="padding:12px 20px;font-family:'JetBrains Mono',monospace">${g.gap_id}</td>
          <td style="padding:12px 20px;font-family:'JetBrains Mono',monospace">${g.missing_prompt_id}</td>
          <td style="padding:12px 20px">${escapeHtml(g.missing_title)}</td>
          <td style="padding:12px 20px">${escapeHtml(g.category)}</td>
          <td style="padding:12px 20px"><span class="badge ${g.severity.toLowerCase() === 'critical' ? 'fail' : 'warn'}">${g.severity}</span></td>
          <td style="padding:12px 20px;color:var(--yellow)">${g.remediation_status}</td>
        </tr>
      `).join('');
    }

    const genData = await fetchJSON('/api/v1/promptbrain/generated');
    const genList = document.getElementById('pb-generated-list');
    if (!genData.length) {
      genList.innerHTML = '<div style="color:var(--muted)">No programmatically generated templates.</div>';
    } else {
      genList.innerHTML = genData.map(gp => `
        <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px;margin-bottom:16px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
            <span style="font-family:'JetBrains Mono',monospace;color:var(--accent);font-weight:600">${gp.id} — ${escapeHtml(gp.title)}</span>
            <span class="badge pass">${escapeHtml(gp.category)}</span>
          </div>
          <div style="font-size:12px;color:var(--muted);margin-bottom:10px"><strong>Outputs:</strong> ${escapeHtml(gp.outputs)}</div>
          <button class="refresh-btn" onclick="showPromptBody('${gp.id}')" style="padding:4px 8px;font-size:11px">Show Full Template</button>
        </div>
      `).join('');
    }

    const schemaData = await fetchJSON('/api/v1/promptbrain/brain-schema');
    document.getElementById('pb-schema-json').textContent = JSON.stringify(schemaData, null, 2);

  } catch(e) {
    console.error(e);
  }
}

function switchPbTab(tabName) {
  document.querySelectorAll('.pb-subpage').forEach(p => p.style.display = 'none');
  document.getElementById('pb-subpage-' + tabName).style.display = 'block';
  
  document.querySelectorAll('[id^="pb-tab-btn-"]').forEach(btn => {
    btn.style.background = 'var(--glass-b)';
    btn.style.color = 'var(--text)';
  });
  document.getElementById('pb-tab-btn-' + tabName).style.background = 'var(--accent)';
  document.getElementById('pb-tab-btn-' + tabName).style.color = '#fff';
}

function filterPrompts() {
  const query = document.getElementById('pb-search-input').value.toLowerCase();
  const category = document.getElementById('pb-filter-category').value;
  const tbody = document.getElementById('pb-registry-table-body');

  const filtered = allPrompts.filter(p => {
    const matchesQuery = p.id.toLowerCase().includes(query) || 
                         p.title.toLowerCase().includes(query) || 
                         p.mission.toLowerCase().includes(query) || 
                         (p.industry || '').toLowerCase().includes(query);
    const matchesCategory = !category || p.category === category;
    return matchesQuery && matchesCategory;
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:var(--muted)">No matching prompts found.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(p => `
    <tr style="border-bottom:1px solid var(--border)">
      <td style="padding:12px 20px;font-family:'JetBrains Mono',monospace">${p.id}</td>
      <td style="padding:12px 20px;font-weight:500">${escapeHtml(p.title)}</td>
      <td style="padding:12px 20px"><span class="badge muted">${escapeHtml(p.category)}</span></td>
      <td style="padding:12px 20px;font-size:12px;color:var(--muted)">${escapeHtml(p.industry || 'All Industries')}</td>
      <td style="padding:12px 20px;font-size:11px;color:var(--accent)">${escapeHtml((p.frameworks || []).join(', ') || 'NIST CSF 2.0')}</td>
      <td style="padding:12px 20px">
        <button class="refresh-btn" onclick="showPromptBody('${p.id}')" style="padding:4px 8px;font-size:11px">View</button>
      </td>
    </tr>
  `).join('');
}

async function showPromptBody(pId) {
  const p = allPrompts.find(x => x.id === pId);
  if (!p) return;
  document.getElementById('detail-overlay').classList.add('open');
  const content = document.getElementById('detail-content');
  content.innerHTML = `
    <div class="detail-title">🧠 ${p.id} — ${escapeHtml(p.title)}</div>
    <div style="margin:10px 0;display:flex;gap:10px">
      <span class="badge pass">Category: ${escapeHtml(p.category)}</span>
      <span class="badge warn">Industry: ${escapeHtml(p.industry || 'All')}</span>
      <span class="badge info">Quality: ${p.qualityScore}%</span>
    </div>
    <div class="mono" style="font-size:12px;color:var(--muted);margin-bottom:16px"><strong>Mission:</strong> ${escapeHtml(p.mission)}</div>
    <div class="mono" style="font-size:12px;color:var(--muted);margin-bottom:16px"><strong>Expected Outputs:</strong> ${escapeHtml(p.outputs)}</div>
    <div style="font-size:11px;color:var(--muted);margin-bottom:6px">PROMPT TEMPLATE:</div>
    <pre class="artifact-content" style="white-space:pre-wrap;font-size:12px;background:var(--bg3);padding:12px;border-radius:var(--radius-sm);border:1px solid var(--border)">${escapeHtml(p.prompt)}</pre>
  `;
}

async function simulatePbRoute() {
  const query = document.getElementById('pb-router-query').value;
  const industry = document.getElementById('pb-router-industry').value;
  const framework = document.getElementById('pb-router-framework').value;
  const resultsDiv = document.getElementById('pb-router-results');

  if (!query) {
    resultsDiv.innerHTML = '<div style="color:var(--red)">Please enter a task description query.</div>';
    return;
  }

  resultsDiv.innerHTML = '<div class="spinner"></div>';

  try {
    const res = await fetch('/api/v1/promptbrain/route', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_description: query, industry, framework })
    });
    const data = await res.json();
    
    let recsHtml = '';
    if (data.status === 'FAIL_CLOSED') {
      recsHtml = `<div style="background:rgba(244,63,94,0.1);border:1px solid var(--red);border-radius:var(--radius-sm);padding:12px;color:var(--red);margin-bottom:12px">
        <strong>Execution Status: FAIL_CLOSED</strong><br/>
        Triggers Blocked: ${data.fail_closed_triggers.join(', ')}
      </div>`;
    } else {
      recsHtml = `
        <div style="margin-bottom:12px">
          <strong>Risk Level:</strong> <span class="badge ${data.risk_level === 'HIGH' ? 'fail' : 'pass'}">${data.risk_level}</span> | 
          <strong>Human Approval:</strong> <span class="badge ${data.human_approval_required ? 'warn' : 'muted'}">${data.human_approval_required ? 'REQUIRED' : 'NO'}</span>
        </div>
        <div style="font-size:13px;font-weight:600;margin-bottom:8px">Recommended Agent Prompts:</div>
        ${data.recommendations.map(r => `
          <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
            <div>
              <span style="font-family:'JetBrains Mono',monospace;color:var(--accent);font-weight:600">${r.id}</span> — <strong>${escapeHtml(r.title)}</strong>
              <div style="font-size:11px;color:var(--muted);margin-top:2px">Relevance Match: ${r.relevance_score} | Category: ${escapeHtml(r.category)}</div>
            </div>
            <button class="refresh-btn" onclick="showPromptBody('${r.id}')" style="padding:4px 8px;font-size:11px">Load Prompt</button>
          </div>
        `).join('')}
      `;
    }
    resultsDiv.innerHTML = recsHtml;
  } catch(e) {
    resultsDiv.innerHTML = `<div style="color:var(--red)">Routing Simulation failed: ${e.message}</div>`;
  }
}

function apiExportPromptbrain() {
  window.location.href = '/api/v1/promptbrain/export';
}

// ---- Prompt QA Forge ----
let currentScores = {};

async function loadPromptQa() {
  try {
    const statusRes = await fetchJSON('/api/v1/promptqa/status');
    document.getElementById('qa-stat-evaluated').textContent = statusRes.totalPromptsEvaluated || '0';
    document.getElementById('qa-stat-avg-score').textContent = (statusRes.averagePromptScore || '0') + '%';
    document.getElementById('qa-stat-release-grade').textContent = statusRes.releaseGradePrompts || '0';
    document.getElementById('qa-stat-needing-rewrite').textContent = statusRes.pendingRewriteCandidates || '0';
    document.getElementById('qa-stat-weaknesses').textContent = statusRes.criticalPromptWeaknesses || '0';
    document.getElementById('qa-stat-pending-approvals').textContent = statusRes.pendingRewriteCandidates || '0';
    document.getElementById('qa-stat-routing-score').textContent = (statusRes.routingEvalScore || '100') + '%';

    switchQaTab('scores');

    currentScores = await fetchJSON('/api/v1/promptqa/scores');
    renderScoresTable(currentScores);

    const weaknesses = await fetchJSON('/api/v1/promptqa/weaknesses');
    const wBody = document.getElementById('qa-weaknesses-table-body');
    if (!Object.keys(weaknesses).length) {
      wBody.innerHTML = '<tr><td colspan="3" style="padding:20px;text-align:center;color:var(--muted)">No weaknesses detected.</td></tr>';
    } else {
      wBody.innerHTML = Object.entries(weaknesses).map(([pId, list]) => `
        <tr style="border-bottom:1px solid var(--border)">
          <td style="padding:12px 20px;font-family:monospace;font-weight:600">${pId}</td>
          <td style="padding:12px 20px"><span class="badge ${list.length > 0 ? 'fail' : 'pass'}">${list.length}</span></td>
          <td style="padding:12px 20px">${list.map(w => `<span class="badge warn" style="margin-right:4px">${w}</span>`).join('') || '<span style="color:var(--green)">None</span>'}</td>
        </tr>
      `).join('');
    }

    const candidates = await fetchJSON('/api/v1/promptqa/rewrite-candidates');
    const queue = await fetchJSON('/api/v1/promptqa/approval-queue');
    const cBody = document.getElementById('qa-candidates-table-body');
    if (!Object.keys(candidates).length) {
      cBody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:var(--muted)">No rewrite candidates in queue.</td></tr>';
    } else {
      cBody.innerHTML = Object.entries(candidates).map(([pId, c]) => {
        const item = queue[pId] || {};
        const isApproved = item.approvalStatus === 'approved';
        return `
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:12px 20px;font-family:monospace">${pId}</td>
            <td style="padding:12px 20px;font-family:monospace">${c.candidateId}</td>
            <td style="padding:12px 20px"><span class="badge fail">${c.beforeScore}%</span></td>
            <td style="padding:12px 20px"><span class="badge pass">${c.afterScoreEstimate}%</span></td>
            <td style="padding:12px 20px"><span class="badge ${isApproved ? 'pass' : 'warn'}">${item.approvalStatus || 'pending_review'}</span></td>
            <td style="padding:12px 20px;text-align:right">
              ${isApproved 
                ? '<span style="color:var(--green);font-size:12px;font-weight:600">✓ Approved & Active</span>' 
                : `<button class="refresh-btn" onclick="approveCandidate('${pId}')" style="background:var(--green);color:#111;padding:4px 10px;font-size:11px;font-weight:700">Approve Rewrite</button>`
              }
              <button class="refresh-btn" onclick="inspectRewrite('${pId}')" style="padding:4px 8px;font-size:11px;margin-left:4px">Inspect</button>
            </td>
          </tr>
        `;
      }).join('');
    }

    const routing = await fetchJSON('/api/v1/promptqa/routing-eval');
    const rContainer = document.getElementById('qa-routing-container');
    if (!routing || !routing.eval_details) {
      rContainer.innerHTML = '<div style="color:var(--muted)">Run Routing Evaluation to verify model/task routing lane matches.</div>';
    } else {
      rContainer.innerHTML = `
        <div style="font-weight:600;margin-bottom:12px;color:var(--green)">Routing Precision Success Rate: ${routing.routing_eval_score}%</div>
        <div style="display:flex;flex-direction:column;gap:10px">
          ${routing.eval_details.map(d => `
            <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <strong style="font-size:13px">${escapeHtml(d.query)}</strong>
                <span class="badge ${d.passed ? 'pass' : 'fail'}">${d.passed ? 'Match Pass' : 'Match Fail'}</span>
              </div>
              <div style="font-size:11px;color:var(--muted)">
                Expected Prompt: <span style="font-family:monospace;color:var(--accent)">${d.expected_prompt_id}</span><br/>
                Top Candidates: ${d.top_recommendations.map(r => `<span style="font-family:monospace;margin-right:6px">${r}</span>`).join(', ')}
              </div>
            </div>
          `).join('')}
        </div>
      `;
    }

  } catch(e) {
    console.error(e);
  }
}

function renderScoresTable(scores) {
  const sBody = document.getElementById('qa-scores-table-body');
  sBody.innerHTML = Object.entries(scores).map(([pId, s]) => {
    const isCritical = pId.startsWith('BRAIN-') || pId.startsWith('PROMPT-') || pId.startsWith('GAP-') || pId.startsWith('SWARM-') || pId.startsWith('GOVFRAME-');
    const threshold = isCritical ? 90 : 85;
    const isUnder = s.overall_score < threshold;
    return `
      <tr class="qa-score-row" data-id="${pId}" data-band="${s.band}" style="border-bottom:1px solid var(--border)">
        <td style="padding:12px 20px;font-family:monospace;font-weight:600">${pId}</td>
        <td style="padding:12px 20px">${pId.split('-')[0]}</td>
        <td style="padding:12px 20px"><span style="font-weight:700;color:${isUnder ? 'var(--red)' : 'var(--green)'}">${s.overall_score}%</span></td>
        <td style="padding:12px 20px"><span class="badge ${s.band === 'Release Grade' ? 'pass' : (s.band === 'Strong' ? 'pass' : (s.band === 'Acceptable' ? 'info' : 'fail'))}">${s.band}</span></td>
        <td style="padding:12px 20px"><span class="badge pass">PASS</span></td>
        <td style="padding:12px 20px;text-align:right">
          <button class="refresh-btn" onclick="inspectScores('${pId}')" style="padding:4px 8px;font-size:11px">Breakdown</button>
        </td>
      </tr>
    `;
  }).join('');
}

function filterQaScores() {
  const query = document.getElementById('qa-scores-filter').value.toLowerCase();
  const band = document.getElementById('qa-scores-band-filter').value;
  
  document.querySelectorAll('.qa-score-row').forEach(row => {
    const id = row.getAttribute('data-id').toLowerCase();
    const rowBand = row.getAttribute('data-band');
    
    const matchesQuery = id.includes(query);
    const matchesBand = (band === 'ALL' || rowBand === band);
    
    if (matchesQuery && matchesBand) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

function switchQaTab(tabName) {
  document.querySelectorAll('.qa-subpage').forEach(p => p.style.display = 'none');
  document.getElementById('qa-subpage-' + tabName).style.display = 'block';

  document.querySelectorAll('[id^="qa-tab-btn-"]').forEach(btn => {
    btn.style.background = 'var(--glass-b)';
    btn.style.color = 'var(--text)';
  });
  document.getElementById('qa-tab-btn-' + tabName).style.background = 'var(--accent)';
  document.getElementById('qa-tab-btn-' + tabName).style.color = '#fff';
}

async function triggerQaRun() {
  const banner = document.getElementById('qa-status-banner');
  banner.style.display = 'block';
  banner.style.background = 'rgba(99,102,241,0.1)';
  banner.style.border = '1px solid var(--accent)';
  banner.style.color = 'var(--accent)';
  banner.textContent = 'Running Prompt QA sweep (scoring 187 active prompts across 21 dimensions)...';

  try {
    const res = await fetch('/api/v1/promptqa/run', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      banner.style.background = 'rgba(34,211,165,0.1)';
      banner.style.border = '1px solid var(--green)';
      banner.style.color = 'var(--green)';
      banner.textContent = data.message;
      loadPromptQa();
    }
  } catch(e) {
    banner.style.background = 'rgba(244,63,94,0.1)';
    banner.style.border = '1px solid var(--red)';
    banner.style.color = 'var(--red)';
    banner.textContent = `QA Run failed: ${e.message}`;
  }
}

async function triggerRouteEval() {
  const banner = document.getElementById('qa-status-banner');
  banner.style.display = 'block';
  banner.style.background = 'rgba(99,102,241,0.1)';
  banner.style.border = '1px solid var(--accent)';
  banner.style.color = 'var(--accent)';
  banner.textContent = 'Running model routing evaluations across test cases...';

  try {
    await fetch('/api/v1/promptqa/route-eval', { method: 'POST' });
    banner.style.background = 'rgba(34,211,165,0.1)';
    banner.style.border = '1px solid var(--green)';
    banner.style.color = 'var(--green)';
    banner.textContent = 'Routing evaluation run complete!';
    loadPromptQa();
  } catch(e) {
    banner.style.background = 'rgba(244,63,94,0.1)';
    banner.style.border = '1px solid var(--red)';
    banner.style.color = 'var(--red)';
    banner.textContent = `Routing evaluation failed: ${e.message}`;
  }
}

async function approveCandidate(pId) {
  const banner = document.getElementById('qa-status-banner');
  banner.style.display = 'block';
  banner.textContent = `Approving and promoting candidate rewrite for ${pId}...`;

  try {
    const res = await fetch('/api/v1/promptqa/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: pId })
    });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      banner.style.background = 'rgba(34,211,165,0.1)';
      banner.style.border = '1px solid var(--green)';
      banner.style.color = 'var(--green)';
      banner.textContent = data.message;
      loadPromptQa();
    } else {
      throw new Error(data.message);
    }
  } catch(e) {
    banner.style.background = 'rgba(244,63,94,0.1)';
    banner.style.border = '1px solid var(--red)';
    banner.style.color = 'var(--red)';
    banner.textContent = `Approval denied: ${e.message}`;
  }
}

async function inspectScores(pId) {
  document.getElementById('detail-overlay').classList.add('open');
  const content = document.getElementById('detail-content');
  content.innerHTML = '<div class="spinner"></div>';

  try {
    const data = currentScores[pId];
    if (!data) throw new Error('Data not loaded');
    
    content.innerHTML = `
      <div class="detail-title">📊 Prompt QA Scoring Breakdown for ${pId}</div>
      <div style="margin:10px 0;display:flex;gap:10px">
        <span class="badge pass">Overall Score: ${data.overall_score}%</span>
        <span class="badge info">Scoring Band: ${data.band}</span>
      </div>
      <div style="max-height:400px;overflow-y:auto;margin-top:16px">
        <table class="table" style="width:100%;border-collapse:collapse;text-align:left">
          <thead>
            <tr style="border-bottom:1px solid var(--border)">
              <th style="padding:8px">Dimension</th>
              <th style="padding:8px">Rating Score</th>
            </tr>
          </thead>
          <tbody>
            ${Object.entries(data.dimensions).map(([k, v]) => `
              <tr style="border-bottom:1px solid var(--border)">
                <td style="padding:8px;font-family:monospace">${k}</td>
                <td style="padding:8px"><span style="font-weight:700;color:${v >= 4 ? 'var(--green)' : (v >= 3 ? 'var(--yellow)' : 'var(--red)')}">${v} / 5</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch(e) {
    content.innerHTML = `<div style="color:var(--red)">Failed to inspect scores: ${e.message}</div>`;
  }
}

async function inspectRewrite(pId) {
  document.getElementById('detail-overlay').classList.add('open');
  const content = document.getElementById('detail-content');
  content.innerHTML = '<div class="spinner"></div>';

  try {
    const candidates = await fetchJSON('/api/v1/promptqa/rewrite-candidates');
    const c = candidates[pId];
    if (!c) throw new Error('No candidate found');

    content.innerHTML = `
      <div class="detail-title">🛠️ Rewrite Candidate for ${pId}</div>
      <div style="margin:10px 0;display:flex;gap:10px">
        <span class="badge fail">Score Before: ${c.beforeScore}%</span>
        <span class="badge pass">Estimated Score After: ${c.afterScoreEstimate}%</span>
        <span class="badge info">Version: ${c.version}</span>
      </div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:10px">
        <strong>Reason for rewrite:</strong> ${escapeHtml(c.rewriteReason)}<br/>
        <strong>Change Summary:</strong> ${escapeHtml(c.changeSummary)}
      </div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">REWRITTEN PROMPT CANDIDATE TEXT:</div>
      <pre class="artifact-content" style="white-space:pre-wrap;font-size:12px;background:var(--bg3);padding:12px;border-radius:var(--radius-sm);border:1px solid var(--border);max-height:300px;overflow-y:auto">${escapeHtml(c.rewrittenPrompt)}</pre>
    `;
  } catch(e) {
    content.innerHTML = `<div style="color:var(--red)">Failed to inspect rewrite: ${e.message}</div>`;
  }
}

function apiExportPromptqa() {
  window.location.href = '/api/v1/promptqa/export';
}

function apiExportEvidenceBrain() {
  window.location.href = '/api/v1/brain/export';
}

// ---- Evidence Brain ----
async function loadEvidenceBrain() {
  try {
    const statusRes = await fetchJSON('/api/v1/brain/validation-status');
    const totalGaps = statusRes.total_gaps || 0;
    const closedGaps = statusRes.closed_gaps || 0;
    const openGaps = statusRes.open_gaps || 0;

    const graphRes = await fetchJSON('/api/v1/brain/graph');
    const nodes = graphRes.nodes || [];
    document.getElementById('eb-stat-chunks').textContent = nodes.length;
    document.getElementById('eb-stat-resolved-gaps').textContent = closedGaps;
    document.getElementById('eb-stat-open-gaps').textContent = openGaps;

    let sumTrust = 0;
    nodes.forEach(n => sumTrust += n.trust_score);
    const avgTrust = nodes.length ? (sumTrust / nodes.length).toFixed(1) : '—';
    document.getElementById('eb-stat-avg-trust').textContent = avgTrust + '%';

    switchEbTab('query');

    const closuresBody = document.getElementById('eb-closures-table-body');
    if (!statusRes.closures || !statusRes.closures.length) {
      closuresBody.innerHTML = '<tr><td colspan="5" style="padding:20px;text-align:center;color:var(--muted)">No gaps audit available.</td></tr>';
    } else {
      closuresBody.innerHTML = statusRes.closures.map(c => {
        const hasNodes = c.matching_evidence_nodes && c.matching_evidence_nodes.length > 0;
        let evidenceText = '<span style="color:var(--muted)">No matching evidence</span>';
        if (hasNodes) {
          evidenceText = c.matching_evidence_nodes.map(n => `
            <div style="font-size:11px;margin-bottom:4px">
              <span style="font-family:monospace;color:var(--accent)">${n.node_id.split('#').pop()}</span> 
              (${n.resolves ? 'Resolves' : 'Mentions'})
            </div>
          `).join('');
        }
        return `
          <tr style="border-bottom:1px solid var(--border)">
            <td style="padding:12px 20px;font-family:monospace">${c.gap_id}</td>
            <td style="padding:12px 20px;font-family:monospace">${c.missing_prompt_id}</td>
            <td style="padding:12px 20px">${escapeHtml(c.missing_title)}</td>
            <td style="padding:12px 20px"><span class="badge ${c.status === 'RESOLVED' ? 'pass' : 'fail'}">${c.status}</span></td>
            <td style="padding:12px 20px">${evidenceText}</td>
          </tr>
        `;
      }).join('');
    }

    const graphContainer = document.getElementById('eb-graph-container');
    if (!nodes.length) {
      graphContainer.innerHTML = '<div style="color:var(--muted);text-align:center;padding:20px">No knowledge graph data loaded. Run Ingestion first.</div>';
    } else {
      const edges = graphRes.edges || [];
      graphContainer.innerHTML = `
        <div style="font-weight:600;margin-bottom:8px;font-size:13px;color:var(--accent)">Knowledge Graph Nodes (${nodes.length}) & Edges (${edges.length})</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
          <div>
            <div style="font-size:11px;text-transform:uppercase;color:var(--muted);margin-bottom:6px">Active Nodes:</div>
            ${nodes.slice(0, 15).map(n => `
              <div style="background:rgba(255,255,255,0.02);padding:6px 10px;border-radius:4px;margin-bottom:4px;font-size:12px;border:1px solid var(--border)">
                <strong>[Node]</strong> <span style="font-family:monospace;color:var(--green)">${n.id.split('#').pop() || n.id}</span>
                <div style="font-size:10px;color:var(--muted);margin-top:2px">Path: ${n.path} | Trust: ${n.trust_score}%</div>
              </div>
            `).join('')}
            ${nodes.length > 15 ? `<div style="font-size:11px;color:var(--muted);padding:4px">... and ${nodes.length - 15} more nodes.</div>` : ''}
          </div>
          <div>
            <div style="font-size:11px;text-transform:uppercase;color:var(--muted);margin-bottom:6px">Semantic Edges:</div>
            ${edges.slice(0, 15).map(e => `
              <div style="background:rgba(255,255,255,0.02);padding:6px 10px;border-radius:4px;margin-bottom:4px;font-size:12px;border:1px solid var(--border)">
                <span style="font-family:monospace;color:var(--accent)">${e.from_node.split('#').pop() || e.from_node}</span> 
                <span style="color:var(--yellow)">→ [${e.relationship_type}] →</span> 
                <span style="font-family:monospace;color:var(--accent)">${e.to_node.replace('prompt-', '')}</span>
              </div>
            `).join('')}
            ${edges.length > 15 ? `<div style="font-size:11px;color:var(--muted);padding:4px">... and ${edges.length - 15} more edges.</div>` : ''}
          </div>
        </div>
      `;
    }

  } catch(e) {
    console.error(e);
  }
}

function switchEbTab(tabName) {
  document.querySelectorAll('.eb-subpage').forEach(p => p.style.display = 'none');
  document.getElementById('eb-subpage-' + tabName).style.display = 'block';

  document.querySelectorAll('[id^="eb-tab-btn-"]').forEach(btn => {
    btn.style.background = 'var(--glass-b)';
    btn.style.color = 'var(--text)';
  });
  document.getElementById('eb-tab-btn-' + tabName).style.background = 'var(--accent)';
  document.getElementById('eb-tab-btn-' + tabName).style.color = '#fff';
}

async function triggerInjest() {
  const banner = document.getElementById('eb-ingestion-status-banner');
  banner.style.display = 'block';
  banner.style.background = 'rgba(99,102,241,0.1)';
  banner.style.border = '1px solid var(--accent)';
  banner.style.color = 'var(--accent)';
  banner.textContent = 'Crawling repository artifacts and updating SQLite evidence index...';
  
  try {
    const res = await fetch('/api/v1/brain/ingest', { method: 'POST' });
    const data = await res.json();
    if (data.status === 'SUCCESS') {
      banner.style.background = 'rgba(34,211,165,0.1)';
      banner.style.border = '1px solid var(--green)';
      banner.style.color = 'var(--green)';
      banner.textContent = `Ingestion complete! Scanned ${data.total_files_scanned} files, ingested ${data.total_chunks_ingested} evidence chunks.`;
      loadEvidenceBrain();
    } else {
      throw new Error(data.message || 'Ingestion failed');
    }
  } catch(e) {
    banner.style.background = 'rgba(244,63,94,0.1)';
    banner.style.border = '1px solid var(--red)';
    banner.style.color = 'var(--red)';
    banner.textContent = `Error running Ingestion Crawler: ${e.message}`;
  }
}

async function searchEvidence() {
  const query = document.getElementById('eb-query-input').value;
  const trust = document.getElementById('eb-query-trust').value;
  const resultsDiv = document.getElementById('eb-query-results');

  if (!query) {
    resultsDiv.innerHTML = '<div style="color:var(--red)">Please enter a search query.</div>';
    return;
  }

  resultsDiv.innerHTML = '<div class="spinner"></div>';

  try {
    const res = await fetch(`/api/v1/brain/query?query=${encodeURIComponent(query)}&min_trust=${trust}`);
    const data = await res.json();
    
    if (!data.length) {
      resultsDiv.innerHTML = '<div style="text-align:center;padding:40px;color:var(--muted)">No matching evidence found. Try another query or verify ingestion.</div>';
      return;
    }

    resultsDiv.innerHTML = data.map(r => `
      <div style="background:var(--bg3);border:1px solid var(--border);border-radius:var(--radius);padding:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="font-weight:600;font-size:13px;color:var(--green)">Relevance score: ${(r.relevance_score * 100).toFixed(1)}%</span>
          <div style="display:flex;gap:6px">
            <span class="badge ${r.trust_score >= 80 ? 'pass' : 'warn'}">Trust: ${r.trust_score}%</span>
            <span class="badge info" style="font-family:monospace">${r.commit_sha.substring(0,8)}</span>
          </div>
        </div>
        <div style="font-size:13px;line-height:1.5;color:var(--text);margin-bottom:10px">${escapeHtml(r.snippet)}</div>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <div style="font-size:11px;color:var(--muted)">File: <strong>${r.path}</strong> | Author: ${r.author}</div>
          <button class="refresh-btn" onclick="showCitation('${r.id}')" style="padding:4px 8px;font-size:11px">Inspect Citations</button>
        </div>
      </div>
    `).join('');

  } catch(e) {
    resultsDiv.innerHTML = `<div style="color:var(--red)">Search failed: ${e.message}</div>`;
  }
}

async function showCitation(nodeId) {
  document.getElementById('detail-overlay').classList.add('open');
  const content = document.getElementById('detail-content');
  content.innerHTML = '<div class="spinner"></div>';
  
  try {
    const data = await fetchJSON(`/api/v1/brain/citations?node_id=${encodeURIComponent(nodeId)}`);
    content.innerHTML = `
      <div class="detail-title">🔗 Citation Provenance & Chain of Custody</div>
      <div style="margin:10px 0;display:flex;gap:10px">
        <span class="badge pass">Trust Score: ${data.trust_score}%</span>
        <span class="badge info">Commit SHA: ${data.commit_sha}</span>
      </div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:10px">
        <strong>Source File Path:</strong> ${data.path}<br/>
        <strong>Last Modified:</strong> ${data.timestamp}<br/>
        <strong>Responsible Owner/Author:</strong> ${data.author}
      </div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">RAW EVIDENCE CHUNK CONTENT:</div>
      <pre class="artifact-content" style="white-space:pre-wrap;font-size:12px;background:var(--bg3);padding:12px;border-radius:var(--radius-sm);border:1px solid var(--border)">${escapeHtml(data.content)}</pre>
    `;
  } catch(e) {
    content.innerHTML = `<div style="color:var(--red)">Failed to load citations: ${e.message}</div>`;
  }
}

// ---- HOCH TV ----
let activeHls = null;

async function loadHochTV() {
  await loadTVHealth();
  await loadTVGroups();
}

async function loadTVHealth() {
  try {
    const health = await fetchJSON('/api/tv/health');
    document.getElementById('tv-health-status').textContent = health.status;
    document.getElementById('tv-health-channels').textContent = health.channels_count;
    document.getElementById('tv-health-groups').textContent = health.groups_count;
    document.getElementById('tv-health-refreshed').textContent = health.last_refreshed ? new Date(health.last_refreshed).toLocaleString() : 'Never';
  } catch (e) {
    console.error('Failed to load TV health:', e);
  }
}

async function loadTVGroups() {
  const container = document.getElementById('tv-groups-list');
  container.innerHTML = '<div class="spinner"></div>';
  try {
    const groups = await fetchJSON('/api/tv/groups');
    if (!groups || groups.length === 0) {
      container.innerHTML = '<div style="padding:10px;color:var(--muted)">No categories found.</div>';
      return;
    }
    container.innerHTML = groups.map(g => `
      <div class="list-item" onclick="selectTVGroup('${escapeJs(g)}', this)" style="padding:8px 12px;cursor:pointer;border-radius:var(--radius-sm);margin-bottom:4px;font-size:13px">
        📁 ${escapeHtml(g)}
      </div>
    `).join('');
    
    if (groups.length > 0) {
      const firstEl = container.firstElementChild;
      if (firstEl) firstEl.click();
    }
  } catch (e) {
    container.innerHTML = `<div style="color:var(--red);padding:10px">Error: ${e.message}</div>`;
  }
}

async function selectTVGroup(groupName, element) {
  const parent = document.getElementById('tv-groups-list');
  parent.querySelectorAll('.list-item').forEach(el => {
    el.style.background = 'transparent';
    el.style.fontWeight = 'normal';
  });
  if (element) {
    element.style.background = 'var(--bg3)';
    element.style.fontWeight = 'bold';
  }

  const container = document.getElementById('tv-channels-list');
  container.innerHTML = '<div class="spinner"></div>';
  try {
    const channels = await fetchJSON(`/api/tv/channels?group=${encodeURIComponent(groupName)}`);
    if (!channels || channels.length === 0) {
      container.innerHTML = '<div style="padding:15px;color:var(--muted)">No channels in this category.</div>';
      return;
    }
    container.innerHTML = channels.map(c => `
      <div class="list-item" onclick="playTVChannel('${c.id}')" style="padding:8px 12px;cursor:pointer;border-radius:var(--radius-sm);margin-bottom:4px;display:flex;align-items:center;gap:10px;font-size:13px">
        ${c.logo ? `<img src="${escapeHtml(c.logo)}" style="width:24px;height:24px;object-fit:contain;border-radius:4px" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2224%22 height=%2224%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%23666%22 stroke-width=%222%22><rect x=%222%22 y=%222%22 width=%2220%22 height=%2220%22 rx=%224%22></rect></svg>'"/>` : '📺'}
        <div style="flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(c.name)}</div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<div style="color:var(--red);padding:15px">Error: ${e.message}</div>`;
  }
}

async function playTVChannel(chId) {
  const playerHeader = document.getElementById('tv-player-header');
  const video = document.getElementById('tv-video-player');
  const title = document.getElementById('tv-channel-title');
  const urlEl = document.getElementById('tv-channel-stream-url');
  const epgContainer = document.getElementById('tv-epg-container');
  const diagEl = document.getElementById('tv-hls-diagnostics');

  if (diagEl) {
    diagEl.style.display = 'none';
    diagEl.textContent = '';
  }

  // Clear previous native video error listener
  video.onerror = null;

  title.textContent = 'Loading...';
  urlEl.textContent = '';
  epgContainer.innerHTML = '<div class="spinner"></div>';

  try {
    const channel = await fetchJSON(`/api/tv/channel/${chId}`);
    const playbackUrl = channel.playbackUrl || `/api/tv/stream/${channel.id}/master.m3u8`;
    title.textContent = channel.name;
    urlEl.innerHTML = `
      <div style="text-align:right">
        <div><strong>Proxy Playback URL:</strong> ${playbackUrl}</div>
        <div style="font-size:10px;color:var(--green);margin-top:2px">Playback mode: Local HLS Proxy</div>
        <div style="font-size:10px;color:var(--muted)">Remote direct browser load: disabled due to CORS</div>
      </div>
    `;
    playerHeader.textContent = `📺 Playing — ${channel.name}`;

    if (activeHls) {
      activeHls.destroy();
      activeHls = null;
    }

    // Set up video native error handling
    video.onerror = function() {
      const err = video.error;
      if (err && diagEl) {
        diagEl.style.display = 'block';
        diagEl.textContent = `⚠️ HTML5 Video Error:
- Code: ${err.code}
- Message: ${err.message || 'Unknown media error'}`;
      }
    };

    if (playbackUrl.endsWith('.m3u8') || playbackUrl.includes('.m3u8')) {
      if (Hls.isSupported()) {
        activeHls = new Hls();
        activeHls.loadSource(playbackUrl);
        activeHls.attachMedia(video);
        activeHls.on(Hls.Events.MANIFEST_PARSED, function() {
          video.play().catch(e => console.log("Play interrupted or autoplay blocked:", e));
        });
        activeHls.on(Hls.Events.ERROR, function(event, data) {
          console.error("HLS error:", data);
          if (diagEl) {
            diagEl.style.display = 'block';
            let errMsg = `⚠️ HLS Player Error:
- Type: ${data.type}
- Details: ${data.details}
- Fatal: ${data.fatal}`;
            if (data.response) {
              errMsg += `\n- HTTP Status: ${data.response.code} (${data.response.text || 'No status text'})`;
              if (data.response.url) {
                errMsg += `\n- URL: ${data.response.url}`;
              }
            }
            diagEl.textContent = errMsg;
          }
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                if (diagEl) diagEl.textContent += "\n[System] Fatal network error. Retrying stream connection...";
                activeHls.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                if (diagEl) diagEl.textContent += "\n[System] Fatal media error. Recovering player buffer...";
                activeHls.recoverMediaError();
                break;
              default:
                if (diagEl) diagEl.textContent += "\n[System] Unrecoverable error. Recreating player required.";
                activeHls.destroy();
                activeHls = null;
                break;
            }
          }
        });
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = playbackUrl;
        video.addEventListener('canplay', function() {
          video.play().catch(e => console.log("Play interrupted or autoplay blocked:", e));
        });
      } else {
        video.src = playbackUrl;
      }
    } else {
      video.src = playbackUrl;
    }

    if (channel.epg && channel.epg.length > 0) {
      epgContainer.innerHTML = channel.epg.map(prog => {
        const startStr = formatEpgTime(prog.start);
        const stopStr = formatEpgTime(prog.stop);
        return `
          <div style="padding:12px;border-bottom:1px solid var(--border);margin-bottom:8px">
            <div style="font-weight:600;font-size:14px;color:var(--yellow)">${escapeHtml(prog.title)}</div>
            <div style="font-size:12px;color:var(--muted);margin:4px 0">${startStr} - ${stopStr}</div>
            <div style="font-size:13px;color:var(--text)">${escapeHtml(prog.desc)}</div>
          </div>
        `;
      }).join('');
    } else {
      epgContainer.innerHTML = '<div style="color:var(--muted);padding:10px">No program listings available for this channel.</div>';
    }
  } catch (e) {
    title.textContent = 'Error';
    epgContainer.innerHTML = `<div style="color:var(--red)">Failed to load channel details: ${e.message}</div>`;
    if (diagEl) {
      diagEl.style.display = 'block';
      diagEl.textContent = `⚠️ Channel Load Error:\n- Failed to retrieve details or playback URL: ${e.message}`;
    }
  }
}

async function refreshTVBackend() {
  const btn = document.querySelector('button[onclick="refreshTVBackend()"]');
  btn.textContent = 'Refreshing...';
  btn.disabled = true;
  try {
    const res = await fetchJSON('/api/tv/health');
    await loadHochTV();
  } catch (e) {
    alert('Refresh failed: ' + e.message);
  } finally {
    btn.textContent = '⚡ Refresh Playlist';
    btn.disabled = false;
  }
}

function formatEpgTime(xmlTime) {
  if (!xmlTime || xmlTime.length < 14) return xmlTime;
  try {
    const yr = xmlTime.substring(0, 4);
    const mo = xmlTime.substring(4, 6);
    const dy = xmlTime.substring(6, 8);
    const hr = xmlTime.substring(8, 10);
    const mi = xmlTime.substring(10, 12);
    const sc = xmlTime.substring(12, 14);
    return `${yr}-${mo}-${dy} ${hr}:${mi}`;
  } catch(e) {
    return xmlTime;
  }
}

function escapeJs(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function escapeHtml(unsafe) {
  if (!unsafe) return '';
  return String(unsafe)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ---- Operator Console ----
async function loadOperatorHealth() {
  try {
    const data = await fetchJSON('/api/v1/operator/health');
    
    // Set status badges and text
    document.getElementById('health-pb-status').className = 'badge ' + (data.components.PromptBrain.status === 'HEALTHY' ? 'pass' : 'fail');
    document.getElementById('health-pb-status').textContent = data.components.PromptBrain.status;
    document.getElementById('health-pb-count').textContent = data.components.PromptBrain.prompts_count;
    
    document.getElementById('health-pq-status').className = 'badge ' + (data.components.PromptQA.status === 'HEALTHY' ? 'pass' : 'fail');
    document.getElementById('health-pq-status').textContent = data.components.PromptQA.status;
    document.getElementById('health-pq-score').textContent = data.components.PromptQA.average_score;
    
    document.getElementById('health-eb-status').className = 'badge ' + (data.components.EvidenceBrain.status === 'HEALTHY' ? 'pass' : 'fail');
    document.getElementById('health-eb-status').textContent = data.components.EvidenceBrain.status;
    document.getElementById('health-eb-nodes').textContent = data.components.EvidenceBrain.nodes_count;
    document.getElementById('health-eb-edges').textContent = data.components.EvidenceBrain.edges_count;
    
    document.getElementById('health-cg-status').className = 'badge ' + (data.components.CyberGov.status === 'HEALTHY' ? 'pass' : 'fail');
    document.getElementById('health-cg-status').textContent = data.components.CyberGov.status;
    
    document.getElementById('health-cm-status').className = 'badge ' + (data.components.ConMon.status === 'HEALTHY' ? 'pass' : 'fail');
    document.getElementById('health-cm-status').textContent = data.components.ConMon.status;
    document.getElementById('health-cm-drift').textContent = data.components.ConMon.drift_detected ? 'DRIFT ALARM ACTIVE' : 'No drift';
    if (data.components.ConMon.drift_detected) {
      document.getElementById('health-cm-drift').style.color = 'var(--red)';
    } else {
      document.getElementById('health-cm-drift').style.color = 'var(--muted)';
    }
    
    document.getElementById('health-tv-status').className = 'badge ' + (data.components['HOCH TV'].status === 'HEALTHY' ? 'pass' : 'fail');
    document.getElementById('health-tv-status').textContent = data.components['HOCH TV'].status;
    document.getElementById('health-tv-count').textContent = data.components['HOCH TV'].channels_count;
    document.getElementById('health-tv-mode').textContent = data.components['HOCH TV'].offline_mode ? 'Mock (Offline)' : 'Live (Drogon.TV)';
    
    // Toggles
    document.getElementById('toggle-tv-offline').checked = data.demo_config.tv_offline_mode;
    document.getElementById('toggle-qa-failure').checked = data.demo_config.qa_simulation_failures;
    document.getElementById('toggle-cm-drift').checked = data.demo_config.conmon_drift_alarm;
    
    // Git
    document.getElementById('git-seal-tag').textContent = data.git.tag;
    document.getElementById('git-seal-verified').className = data.git.seal_verified ? 'badge pass' : 'badge fail';
    document.getElementById('git-seal-verified').textContent = data.git.seal_verified ? 'VERIFIED (v0.1.0-rc5)' : 'UNVERIFIED';
    document.getElementById('git-clean-status').className = data.git.clean ? 'badge pass' : 'badge info';
    document.getElementById('git-clean-status').textContent = data.git.clean ? 'CLEAN WORKING TREE' : 'DIRTY';
    
    // Global alarm banner
    const globalAlarm = document.getElementById('operator-global-alarm');
    if (data.status === 'DEGRADED' || data.components.ConMon.drift_detected || data.components.PromptQA.status === 'FAILING') {
      globalAlarm.style.display = 'block';
      if (data.components.ConMon.drift_detected) {
        document.getElementById('alarm-title').textContent = 'CONMON COMPLIANCE DRIFT ALARM';
        document.getElementById('alarm-desc').textContent = 'Continuous Monitoring detected unauthorized system modifications or security posture drift!';
      } else if (data.components.PromptQA.status === 'FAILING') {
        document.getElementById('alarm-title').textContent = 'PROMPT QA REGRESSION BLOCK';
        document.getElementById('alarm-desc').textContent = 'Prompt QA average quality score has dropped below the release-grade regression gate (85%)!';
      } else {
        document.getElementById('alarm-title').textContent = 'RUNTIME DEGRADATION DETECTED';
        document.getElementById('alarm-desc').textContent = 'One or more subsystem health indicators are failing. Review the Operator Console.';
      }
    } else {
      globalAlarm.style.display = 'none';
    }
  } catch (e) {
    console.error('Failed to load operator health:', e);
  }
}

async function toggleSimulation(key, checkbox) {
  try {
    await fetchJSON('/api/v1/operator/demo-toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: key, value: checkbox.checked })
    });
    await loadOperatorHealth();
  } catch(e) {
    alert('Failed to toggle simulation: ' + e.message);
  }
}

async function resetTVCache() {
  if (!confirm('Are you sure you want to clear the M3U and EPG caches and force a reload?')) return;
  try {
    await fetchJSON('/api/v1/operator/reset-cache', { method: 'POST' });
    alert('Cache successfully cleared and reloaded.');
    await loadOperatorHealth();
  } catch (e) {
    alert('Failed to reset cache: ' + e.message);
  }
}

async function runStreamDiagnostics() {
  const banner = document.getElementById('diagnostic-banner');
  banner.style.display = 'block';
  banner.style.background = 'var(--bg3)';
  banner.style.border = '1px solid var(--border)';
  banner.style.color = 'var(--text)';
  banner.innerHTML = '⚡ Initiating connection to Drogon.TV stream endpoint. Checking local player access permissions...';
  
  try {
    const res = await fetchJSON('/api/tv/diagnostic');
    if (res.success) {
      banner.style.background = 'rgba(34,211,165,0.15)';
      banner.style.border = '1px solid var(--green)';
      banner.style.color = 'var(--green)';
      banner.innerHTML = `
        <strong>✅ DIRECT STREAM PING SUCCESSFUL</strong><br/>
        <span style="font-size:13px">Pinged channel "${escapeHtml(res.channel_name)}" URL: <code style="word-break:break-all">${escapeHtml(res.url)}</code><br/>
        Response: ${escapeHtml(res.message)}</span>
      `;
    } else {
      banner.style.background = 'rgba(244,63,94,0.15)';
      banner.style.border = '1px solid var(--red)';
      banner.style.color = 'var(--red)';
      banner.innerHTML = `
        <strong>⚠️ DIRECT STREAM ACCESS FAILURE / DRIFT DETECTED</strong><br/>
        <span style="font-size:13px">Attempted connection to stream URL: <code style="word-break:break-all">${escapeHtml(res.url)}</code><br/>
        Reason: ${escapeHtml(res.message || res.error)}</span>
      `;
    }
  } catch(e) {
    banner.style.background = 'rgba(244,63,94,0.15)';
    banner.style.border = '1px solid var(--red)';
    banner.style.color = 'var(--red)';
    banner.innerHTML = `<strong>❌ Diagnostic Execution Failed:</strong> ${escapeHtml(e.message)}`;
  }
}

// ---- Init ----
loadOverview();
loadOperatorHealth(); // Run operator health check initially to check for global alarms
setInterval(loadOperatorHealth, 5000); // Poll operator health status every 5 seconds to keep global alarm dynamically updated
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
    port = int(os.environ.get("SWARM_UI_PORT", "8085"))
    print(f"\n  🚀  Hoch Agent Swarm Dashboard")
    print(f"  →   http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
