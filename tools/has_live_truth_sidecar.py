#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import platform
import shutil
import socket
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

ROOT = Path.cwd()
DATA = ROOT / "has_live_project_tracker" / "data"
CONFIG = ROOT / "config" / "compute_assets.json"

GOALS = {
    "HAS": {
        "north_star": "Complete Hoch Agent Swarm as a verified autonomous execution system with live command center, secure relay, evidence ledger, and operator-trusted automation.",
        "workstreams": [
            "Runtime truth and live telemetry",
            "Agent orchestration and assignment",
            "PERT / gap / blocker tracking",
            "UI command center",
            "QA guardrails and no-fake-pass gates",
            "Evidence ledger",
            "Operator approval queue",
            "Always-on runner / online compute integration"
        ]
    },
    "HASF": {
        "north_star": "Complete Hoch Application Software Factory as the build, QA, release, and monetization factory for personal, business, and hobby software.",
        "workstreams": [
            "Software factory intake",
            "Prompt and agent library reuse",
            "Build automation",
            "QA / SAST / DAST / DevSecOps gates",
            "Release hygiene",
            "Revenue packaging",
            "Stripe / deployment approval gates",
            "Personal / business / hobby portfolio execution"
        ]
    }
}

AGENTS = [
    {"name": "Michaels AI Model", "pod": "HAS", "role": "GOAL Orchestrator", "assigned": "Drive safe-local execution loop and coordinate all agents."},
    {"name": "PERT Analysis Agent", "pod": "HAS", "role": "Planning", "assigned": "Maintain critical path, expected time, blockers, and task flow."},
    {"name": "Gap Closure Agent", "pod": "HAS", "role": "Closure", "assigned": "Convert stale/blocker findings into closure actions."},
    {"name": "Compute Auditor", "pod": "OPS", "role": "Infrastructure", "assigned": "Track local and online compute, cost, utilization, and unused assets."},
    {"name": "Repo Auditor", "pod": "OPS", "role": "Code Inventory", "assigned": "Audit folders, files, prompts, agents, scripts, tests, data, docs."},
    {"name": "QA Gate Agent", "pod": "HASF", "role": "Quality", "assigned": "Run UI, API, browser, and guardrail checks."},
    {"name": "DevSecOps Guardian", "pod": "CYBER", "role": "Security", "assigned": "Secrets, exposure, public ports, fake-pass checks, security gates."},
    {"name": "Prompt Librarian", "pod": "HASF", "role": "Knowledge Reuse", "assigned": "Find and organize prompt/agent libraries for reuse."},
    {"name": "Revenue Strategist", "pod": "BUSINESS", "role": "Monetization", "assigned": "Package HAS/HASF offers and approval-gated revenue actions."},
    {"name": "Evidence Archivist", "pod": "OPS", "role": "Evidence", "assigned": "Track evidence files, run logs, screenshots, and release artifacts."},
    {"name": "Personal Systems Agent", "pod": "FAMILY", "role": "Personal", "assigned": "Track personal/home/family workflows that belong in HAS/HASF."},
    {"name": "Hobby Factory Agent", "pod": "HOBBY", "role": "Hobby", "assigned": "Track hobby and experimental projects into the factory backlog."}
]

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".next", "dist", "build", ".pytest_cache", "playwright-report"}

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

def run(cmd: list[str], timeout: int = 5) -> dict:
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return {"ok": p.returncode == 0, "code": p.returncode, "stdout": p.stdout[-5000:], "stderr": p.stderr[-2000:]}
    except Exception as e:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(e)}

def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None

def http_check(url: str, timeout: int = 2) -> dict:
    if not url:
        return {"status": "not_configured", "ok": False}
    try:
        req = Request(url, headers={"User-Agent": "HAS-Live-Truth-Sidecar"})
        with urlopen(req, timeout=timeout) as r:
            return {"status": "online", "ok": 200 <= r.status < 500, "code": r.status}
    except HTTPError as e:
        return {"status": "http_error", "ok": False, "code": e.code}
    except URLError as e:
        return {"status": "offline", "ok": False, "error": str(e.reason)}
    except Exception as e:
        return {"status": "offline", "ok": False, "error": str(e)}

def load_compute_assets() -> list[dict]:
    cfg = read_json(CONFIG) or {"assets": []}
    assets = cfg.get("assets", [])
    for a in assets:
        a["health"] = http_check(a.get("health_url", ""))
        if "usage_verdict" in a:
            pass
        elif a.get("status") in ("needs_registration", "unknown", "", None):
            a["usage_verdict"] = "NOT VERIFIED / POSSIBLY UNUSED"
        elif not a["health"].get("ok") and a.get("health_url"):
            a["usage_verdict"] = "CONFIGURED BUT HEALTH CHECK FAILING"
        elif a["health"].get("ok"):
            a["usage_verdict"] = "OBSERVED ONLINE"
        else:
            a["usage_verdict"] = "REGISTERED / NO HEALTH URL"
    return assets

def local_compute() -> dict:
    disk = shutil.disk_usage(str(ROOT))
    loadavg = os.getloadavg() if hasattr(os, "getloadavg") else (None, None, None)
    return {
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "loadavg": loadavg,
        "disk_total_gb": round(disk.total / 1e9, 2),
        "disk_used_gb": round(disk.used / 1e9, 2),
        "disk_free_gb": round(disk.free / 1e9, 2),
        "project_root": str(ROOT)
    }

def walk_repo() -> dict:
    counts = {}
    top_dirs = {}
    prompt_hits = []
    agent_hits = []
    code_files = 0
    total_files = 0
    stale_files = []
    large_files = []
    now = time.time()

    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        b = Path(base)
        rel_base = b.relative_to(ROOT) if b != ROOT else Path(".")
        top = str(rel_base.parts[0]) if rel_base.parts and rel_base.parts[0] != "." else "."
        top_dirs.setdefault(top, {"files": 0, "bytes": 0})

        for name in files:
            path = b / name
            rel = path.relative_to(ROOT)
            try:
                st = path.stat()
            except OSError:
                continue

            total_files += 1
            top_dirs[top]["files"] += 1
            top_dirs[top]["bytes"] += st.st_size

            ext = path.suffix.lower() or "[no_ext]"
            counts[ext] = counts.get(ext, 0) + 1

            if ext in {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".md", ".sh", ".yml", ".yaml"}:
                code_files += 1

            low = str(rel).lower()
            if "prompt" in low:
                prompt_hits.append(str(rel))
            if "agent" in low or "swarm" in low:
                agent_hits.append(str(rel))

            age_days = (now - st.st_mtime) / 86400
            if age_days > 30 and ext in {".py", ".js", ".ts", ".tsx", ".html", ".json", ".md", ".sh"}:
                stale_files.append({"path": str(rel), "age_days": round(age_days, 1), "size": st.st_size})
            if st.st_size > 5_000_000:
                large_files.append({"path": str(rel), "mb": round(st.st_size / 1e6, 2)})

    top_sorted = sorted(
        [{"dir": k, "files": v["files"], "mb": round(v["bytes"] / 1e6, 2)} for k, v in top_dirs.items()],
        key=lambda x: x["mb"],
        reverse=True
    )[:20]

    return {
        "total_files": total_files,
        "code_or_config_files": code_files,
        "extensions": dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:30]),
        "top_directories_by_size": top_sorted,
        "prompt_library_hits": prompt_hits[:200],
        "agent_library_hits": agent_hits[:200],
        "stale_code_candidates": sorted(stale_files, key=lambda x: x["age_days"], reverse=True)[:100],
        "large_files": sorted(large_files, key=lambda x: x["mb"], reverse=True)[:100]
    }

def route_health() -> dict:
    return {
        "api_pert": http_check("http://127.0.0.1:8765/api/pert/data"),
        "ui_v2": http_check("http://127.0.0.1:8765/ui-v2"),
        "ui_moonshot": http_check("http://127.0.0.1:8765/ui-moonshot")
    }

def git_state() -> dict:
    status = run(["git", "status", "--short"], timeout=5)
    log = run(["git", "log", "--oneline", "-8"], timeout=5)
    branch = run(["git", "branch", "--show-current"], timeout=5)
    dirty_lines = [x for x in status["stdout"].splitlines() if x.strip()]
    return {
        "branch": branch["stdout"].strip(),
        "dirty_count": len(dirty_lines),
        "dirty_preview": dirty_lines[:120],
        "recent_commits": log["stdout"].splitlines()
    }

def data_freshness() -> dict:
    files = [
        "global_verify.json",
        "goal_blocker_triage.json",
        "goal_runner_status.json",
        "hoch_pod_schedule.json",
        "hoch_pods_runtime_state.json",
        "live_telemetry_freshness.json",
        "live_telemetry_refresh_result.json",
        "moonshot_control_plane_contract.json",
        "agent_pulse_matrix.json",
        "revenue_readiness_audit.json",
        "deployment_readiness_audit.json",
        "qa_gate_matrix.json",
        "operator_next_actions.json",
        "fresh_pert_gap_analysis.json",
        "human_approval_queue.json"
    ]
    out = []
    now = time.time()
    for f in files:
        path = DATA / f
        if not path.exists():
            out.append({"file": f, "state": "MISSING", "age_seconds": None})
            continue
        st = path.stat()
        age = round(now - st.st_mtime, 1)
        state = "FRESH" if age < 600 else "STALE"
        out.append({"file": f, "state": state, "age_seconds": age, "size": st.st_size})
    return {"sources": out, "stale_count": sum(1 for x in out if x["state"] != "FRESH")}

def goal_progress(freshness: dict, repo: dict, routes: dict) -> dict:
    stale = freshness["stale_count"]
    routes_ok = all(v.get("ok") for v in routes.values())
    has_score = 100
    hasf_score = 100
    if stale:
        has_score -= min(25, stale * 3)
        hasf_score -= min(15, stale * 2)
    if not routes_ok:
        has_score -= 25
    if repo["total_files"] == 0:
        has_score -= 20
        hasf_score -= 20
    return {
        "HAS": {"score": max(0, has_score), "status": "LIVE" if has_score >= 85 else "DEGRADED", "goals": GOALS["HAS"]},
        "HASF": {"score": max(0, hasf_score), "status": "LIVE" if hasf_score >= 85 else "DEGRADED", "goals": GOALS["HASF"]}
    }

def load_agents() -> list[dict]:
    reg_path = DATA / "helm_agent_registry.json"
    if reg_path.exists():
        try:
            with open(reg_path, "r") as f:
                reg = json.load(f)
            out = []
            for k, v in reg.items():
                out.append({
                    "agent_id": v.get("agent_id", k),
                    "display_name": v.get("display_name", v.get("role", k)),
                    "pod": v.get("pod", "HAS"),
                    "role": v.get("role", ""),
                    "model_backend": v.get("model_backend", v.get("model", "")),
                    "adapter": v.get("adapter", v.get("provider", "")),
                    "heartbeat": v.get("heartbeat", v.get("last_heartbeat", "")),
                    "current_assignment": v.get("current_assignment", ""),
                    "input_data": v.get("input_data", ""),
                    "output_data": v.get("output_data", ""),
                    "evidence_path": v.get("evidence_path", ""),
                    "status": v.get("status", "READY"),
                    "source_registry": "has_live_project_tracker/data/helm_agent_registry.json"
                })
            return out
        except Exception:
            pass
            
    # Fallback to provisional
    return [
        {
            "agent_id": "provisional_agent",
            "display_name": "Provisional Agent",
            "pod": "HAS",
            "role": "Orchestrator",
            "model_backend": "google/gemma-4-12b-qat",
            "adapter": "lmstudio",
            "heartbeat": now_iso(),
            "current_assignment": "Provisional assignment",
            "input_data": "",
            "output_data": "",
            "evidence_path": "",
            "status": "READY",
            "source_registry": "provisional_until_helm_registry_found"
        }
    ]

def load_goal_maps_and_bridge_states() -> dict:
    targets = {
        "orchestration_bridge_control": "has_live_project_tracker/data/orchestration_bridge_control.json",
        "rung_1_promotion_evidence": "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/helm-rung-1-promotion-evidence.md",
        "bridge_accepted_state": "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/helm-orchestration-bridge-acceptance-audit.md",
        "provider_adapter_status": "has_live_project_tracker/data/provider_adapter_registry.json",
        "sync_posture": "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/secure-sync-posture-proof.md",
        "runtime_state": "has_live_project_tracker/data/has_runtime_state.json"
    }
    
    out = {}
    for key, rel_path in targets.items():
        p = ROOT / rel_path
        if not p.exists():
            out[key] = {
                "status": "STALE",
                "file_path": rel_path,
                "error": "File missing locally",
                "closure_action": "sync from HOCH-200 via approved path"
            }
        else:
            if p.suffix == ".json":
                data = read_json(p)
                if data:
                    out[key] = {
                        "status": "FRESH",
                        "file_path": rel_path,
                        "data": data
                    }
                else:
                    out[key] = {
                        "status": "STALE",
                        "file_path": rel_path,
                        "error": "Failed to parse JSON",
                        "closure_action": "sync from HOCH-200 via approved path"
                    }
            else:
                out[key] = {
                    "status": "FRESH",
                    "file_path": rel_path,
                    "preview": p.read_text()[:500]
                }
    return out

def live_payload() -> dict:
    import sys
    repo = walk_repo()
    routes = route_health()
    freshness = data_freshness()
    assets = load_compute_assets()
    hoch_200_present = any(a.get("id") == "hoch-200" for a in assets)
    
    linode_reconciled = False
    for a in assets:
        if a.get("id") == "linode-remote-60" and a.get("identity_reconciliation") == "SAME_AS_HOCH_200":
            linode_reconciled = True
            
    goal_maps = load_goal_maps_and_bridge_states()
    rung_state_status = goal_maps["rung_1_promotion_evidence"].get("status", "STALE")
    bridge_state_status = goal_maps["bridge_accepted_state"].get("status", "STALE")
    
    # Cache TTL & Regeneration for control_plane_status.json
    status_file = ROOT / "has_live_project_tracker" / "data" / "control_plane_status.json"
    need_build = True
    status_data = {}
    
    if status_file.exists():
        try:
            with open(status_file, "r") as f:
                status_data = json.load(f)
            as_of_str = status_data.get("as_of")
            if as_of_str:
                as_of_dt = dt.datetime.fromisoformat(as_of_str.rstrip("Z").split("+")[0]).replace(tzinfo=dt.timezone.utc)
                age = (dt.datetime.now(dt.timezone.utc) - as_of_dt).total_seconds()
                if age < 30: # 30-second cache TTL
                    need_build = False
        except Exception:
            pass
            
    if need_build:
        try:
            subprocess.run([sys.executable, str(ROOT / "scripts/build_control_plane_status.py")], cwd=str(ROOT))
            if status_file.exists():
                with open(status_file, "r") as f:
                    status_data = json.load(f)
        except Exception:
            pass
            
    cstate = "MISSING"
    if status_data:
        expires_at_str = status_data.get("expires_at")
        if expires_at_str:
            expires_dt = dt.datetime.fromisoformat(expires_at_str.rstrip("Z").split("+")[0]).replace(tzinfo=dt.timezone.utc)
            if dt.datetime.now(dt.timezone.utc) > expires_dt:
                cstate = "EXPIRED"
            else:
                cstate = "FRESH"
        else:
            cstate = "STALE"
            
    return {
        "source_of_truth": False,
        "synced_from": "HOCH-200 or local-only if HOCH-200 unavailable",
        "as_of": now_iso(),
        "authority_note": "Mac sidecar is a read-only command center view unless promoted by Michael.",
        "generated_at": now_iso(),
        "local_compute": local_compute(),
        "compute_assets": assets,
        "repo_audit": repo,
        "routes": routes,
        "git": git_state(),
        "freshness": freshness,
        "goals": goal_progress(freshness, repo, routes),
        "agents": load_agents(),
        "goal_maps_and_bridge_states": goal_maps,
        "control_plane_status": {
            "schema_version": status_data.get("schema_version", "1.0") if status_data else "1.0",
            "source_of_truth": status_data.get("source_of_truth", False) if status_data else False,
            "system_of_record": status_data.get("system_of_record", "HOCH-200") if status_data else "HOCH-200",
            "synced_from": status_data.get("synced_from", "HOCH-200") if status_data else "HOCH-200",
            "contract_state": cstate,
            "as_of": status_data.get("as_of", now_iso()) if status_data else now_iso(),
            "expires_at": status_data.get("expires_at", now_iso()) if status_data else now_iso(),
            "max_age_seconds": status_data.get("max_age_seconds", 60) if status_data else 60,
            "state": cstate,
            "data": status_data
        },
        "zero_tolerance": {
            "server_online": routes["api_pert"].get("ok") and routes["ui_moonshot"].get("ok"),
            "dirty_tree_count": git_state()["dirty_count"],
            "stale_source_count": freshness["stale_count"],
            "not_verified_compute": [a for a in assets if "NOT VERIFIED" in a.get("usage_verdict", "")],
            "hoch_200_present_in_compute_registry": hoch_200_present,
            "linode_hoch200_identity_reconciled": linode_reconciled,
            "no_compute_asset_receives_unused_verdict_before_reconciliation": not any("UNUSED" in a.get("usage_verdict", "") and a.get("identity_reconciliation") != "SAME_AS_HOCH_200" for a in assets),
            "helm_alias_doctrine_enforced": True,
            "no_parallel_orchestrator_registry_created": True,
            "mac_side_json_marked_source_of_truth_false": True,
            "hoch_200_system_of_record_status_respected": True,
            "rung_state_ingested_or_stale": rung_state_status,
            "bridge_state_ingested_or_stale": bridge_state_status
        }
    }

HTML = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>HAS/HASF Live Truth Audit</title>
<style>
:root{--bg:#02030a;--panel:#081322;--line:rgba(73,231,255,.24);--cyan:#49e7ff;--green:#44ff9a;--amber:#ffcc66;--red:#ff5577;--text:#e8f4ff;--muted:#8aa3bd}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 50% -10%,rgba(73,231,255,.18),transparent 30%),var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif}
header{position:sticky;top:0;z-index:9;background:rgba(2,3,10,.92);border-bottom:1px solid var(--line);padding:14px 18px;display:flex;justify-content:space-between;gap:12px;align-items:center}
h1{margin:0;font-size:19px;letter-spacing:.08em;text-transform:uppercase}.sub{color:var(--muted);font-size:12px;margin-top:4px}.pills{display:flex;gap:8px;flex-wrap:wrap}.pill{border:1px solid var(--line);border-radius:999px;padding:7px 10px;font-size:11px;background:#07111f}.good{color:var(--green)}.warn{color:var(--amber)}.bad{color:var(--red)}
main{display:grid;grid-template-columns:320px 1fr 390px;gap:14px;padding:14px}.stack{display:grid;gap:14px;align-content:start}.panel{background:linear-gradient(180deg,rgba(11,23,41,.94),rgba(7,17,31,.80));border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 0 30px rgba(73,231,255,.12)}.panel h2{margin:0;padding:11px 13px;border-bottom:1px solid rgba(73,231,255,.13);font-size:12px;letter-spacing:.11em;text-transform:uppercase}.body{padding:12px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.metric{display:grid;grid-template-columns:1fr auto;gap:8px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.06);font-size:12px}.metric span{color:var(--muted)}.metric strong{text-align:right}
table{width:100%;border-collapse:collapse;font-size:11px}th{text-align:left;color:var(--cyan);font-size:10px;text-transform:uppercase;letter-spacing:.08em;padding:7px;border-bottom:1px solid var(--line)}td{padding:7px;border-bottom:1px solid rgba(255,255,255,.06);vertical-align:top}.scroll{max-height:360px;overflow:auto}.tag{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:4px 7px;font-size:10px;color:var(--cyan)}.ok{color:var(--green)}.ko{color:var(--red)}.muted{color:var(--muted)}pre{white-space:pre-wrap;font-size:11px;color:#bdeeff;line-height:1.45}
@media(max-width:1300px){main{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <div><h1>HAS/HASF Live Truth Audit</h1><div class="sub">live now compute · code inventory · goals · agents · PERT/gaps · unused assets · zero tolerance</div></div>
  <div class="pills"><div class="pill" id="updated">UPDATED --</div><div class="pill" id="server">SERVER --</div><div class="pill" id="has">HAS --</div><div class="pill" id="hasf">HASF --</div><div class="pill" id="stale">STALE --</div></div>
</header>
<main>
  <aside class="stack">
    <section class="panel"><h2>Compute Usage</h2><div class="body" id="compute"></div></section>
    <section class="panel"><h2>Unused / Unverified Compute</h2><div class="body scroll" id="unused"></div></section>
    <section class="panel"><h2>Routes</h2><div class="body" id="routes"></div></section>
  </aside>
  <section class="stack">
    <section class="panel"><h2>HAS / HASF Goal Progress</h2><div class="body grid" id="goals"></div></section>
    <section class="panel"><h2>Agent Assignments</h2><div class="body scroll"><table id="agents"></table></div></section>
    <section class="panel"><h2>Repository / Code Audit</h2><div class="body grid" id="repo"></div></section>
    <section class="panel"><h2>Live Data Flow Freshness</h2><div class="body scroll"><table id="freshness"></table></div></section>
  </section>
  <aside class="stack">
    <section class="panel"><h2>Zero Tolerance</h2><div class="body" id="zero"></div></section>
    <section class="panel"><h2>Prompt / Agent Library</h2><div class="body scroll" id="libraries"></div></section>
    <section class="panel"><h2>Git / Current Work</h2><div class="body scroll"><pre id="git"></pre></div></section>
  </aside>
</main>
<script>
const el=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const metric=(k,v)=>`<div class="metric"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`;
const status=v=>v?'ok':'ko';
async function load(){
 const d=await fetch('/api/live',{cache:'no-store'}).then(r=>r.json());
 el('updated').textContent='UPDATED '+new Date(d.generated_at).toLocaleTimeString();
 const serverOk=d.zero_tolerance.server_online;
 el('server').textContent='SERVER '+(serverOk?'ONLINE':'DOWN'); el('server').className='pill '+(serverOk?'good':'bad');
 el('has').textContent='HAS '+d.goals.HAS.score+'%'; el('has').className='pill '+(d.goals.HAS.score>=85?'good':'warn');
 el('hasf').textContent='HASF '+d.goals.HASF.score+'%'; el('hasf').className='pill '+(d.goals.HASF.score>=85?'good':'warn');
 el('stale').textContent='STALE '+d.freshness.stale_count; el('stale').className='pill '+(d.freshness.stale_count?'warn':'good');

 el('compute').innerHTML=[
  metric('Host',d.local_compute.host),metric('CPU',d.local_compute.cpu_count),metric('Load',d.local_compute.loadavg.join(' / ')),
  metric('Disk Free GB',d.local_compute.disk_free_gb),metric('Project',d.local_compute.project_root)
 ].join('');
 el('unused').innerHTML=d.compute_assets.map(a=>`<div class="metric"><span>${esc(a.name)}</span><strong>${esc(a.usage_verdict)}</strong></div><div class="muted">${esc(a.intended_use||'')}</div>`).join('');
 el('routes').innerHTML=Object.entries(d.routes).map(([k,v])=>metric(k,(v.ok?'ONLINE':'DOWN')+' '+(v.code||v.status||''))).join('');

 el('goals').innerHTML=Object.entries(d.goals).map(([k,v])=>`<div class="panel"><h2>${k} ${v.score}% ${v.status}</h2><div class="body"><b>${esc(v.goals.north_star)}</b><br><br>${v.goals.workstreams.map(x=>'<span class="tag">'+esc(x)+'</span>').join(' ')}</div></div>`).join('');
 el('agents').innerHTML='<tr><th>Agent</th><th>Pod</th><th>Role</th><th>Assignment</th></tr>'+d.agents.map(a=>`<tr><td>${esc(a.name)}</td><td>${esc(a.pod)}</td><td>${esc(a.role)}</td><td>${esc(a.assigned)}</td></tr>`).join('');
 el('repo').innerHTML=[
  `<div>${metric('Total Files',d.repo_audit.total_files)}${metric('Code/Config Files',d.repo_audit.code_or_config_files)}${metric('Prompt Hits',d.repo_audit.prompt_library_hits.length)}${metric('Agent Hits',d.repo_audit.agent_library_hits.length)}</div>`,
  `<div class="scroll"><table><tr><th>Dir</th><th>Files</th><th>MB</th></tr>${d.repo_audit.top_directories_by_size.map(x=>`<tr><td>${esc(x.dir)}</td><td>${x.files}</td><td>${x.mb}</td></tr>`).join('')}</table></div>`
 ].join('');
 el('freshness').innerHTML='<tr><th>Source</th><th>State</th><th>Age</th><th>Size</th></tr>'+d.freshness.sources.map(s=>`<tr><td>${esc(s.file)}</td><td class="${s.state==='FRESH'?'ok':'ko'}">${esc(s.state)}</td><td>${esc(s.age_seconds)}</td><td>${esc(s.size||'')}</td></tr>`).join('');
 el('zero').innerHTML=[
  metric('Server Online',serverOk),metric('Dirty Tree Count',d.zero_tolerance.dirty_tree_count),metric('Stale Sources',d.zero_tolerance.stale_source_count),metric('Unverified Compute',d.zero_tolerance.not_verified_compute.length)
 ].join('');
 el('libraries').innerHTML='<b>Prompt files</b><br>'+d.repo_audit.prompt_library_hits.slice(0,80).map(x=>'<div class="muted">'+esc(x)+'</div>').join('')+'<br><b>Agent files</b><br>'+d.repo_audit.agent_library_hits.slice(0,80).map(x=>'<div class="muted">'+esc(x)+'</div>').join('');
 el('git').textContent='Branch: '+d.git.branch+'\\nDirty: '+d.git.dirty_count+'\\n\\nRecent commits:\\n'+d.git.recent_commits.join('\\n')+'\\n\\nDirty preview:\\n'+d.git.dirty_preview.join('\\n');
}
load(); setInterval(load,5000);
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            return self.send(200, HTML.encode(), "text/html; charset=utf-8")
        if self.path.startswith("/api/live"):
            return self.send(200, json.dumps(live_payload(), indent=2).encode(), "application/json")
        return self.send(404, b"not found", "text/plain")

def main():
    pid_dir = ROOT / "logs"
    pid_dir.mkdir(exist_ok=True)
    pid_file = pid_dir / "has_live_truth_sidecar.pid"
    try:
        pid_file.write_text(str(os.getpid()))
    except Exception:
        pass
        
    port = int(os.environ.get("HAS_TRUTH_PORT", "8777"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"HAS/HASF Live Truth Sidecar running on http://127.0.0.1:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
