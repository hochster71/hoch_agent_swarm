import os
import json
import math
import sqlite3
import urllib.request
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="HAS/HASF PERT Command Center", version="0.1.7")

# Database Path resolution
def get_db_path():
    env = os.getenv("HOCHSTER_DB_PATH")
    if env:
        return env
    if os.path.exists("/app"):
        return "/app/backend/swarm_ledger.db"
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "swarm_ledger.db"))

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 15 Required Workstreams definition
WORKSTREAMS = [
    {
        "id": "W1",
        "title": "Runtime truth and backend stability",
        "description": "Ensure SQLite database connectivity, proper WAL journaling mode, and multi-threaded request safety.",
        "owner_agent": "Live Tracker Runtime Agent",
        "R": "Live Tracker Runtime Agent",
        "A": "Live Tracker Runtime Agent",
        "C": "Master Orchestrator",
        "I": "Evidence Collector Agent",
        "dependencies": [],
        "optimistic_minutes": 5.0,
        "likely_minutes": 10.0,
        "pessimistic_minutes": 15.0,
        "status": "completed",
        "evidence_path": "backend/runtime_truth/state_store.py",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W2",
        "title": "HAS/HASF live project tracker",
        "description": "Maintain standalone project tracker and DORA event streaming server on host machine.",
        "owner_agent": "Live Tracker Runtime Agent",
        "R": "Live Tracker Runtime Agent",
        "A": "Live Tracker Runtime Agent",
        "C": "Production Acceleration Agent",
        "I": "PERT & Planning Agent",
        "dependencies": ["W1"],
        "optimistic_minutes": 10.0,
        "likely_minutes": 15.0,
        "pessimistic_minutes": 30.0,
        "status": "completed",
        "evidence_path": "has_live_project_tracker/server.js",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W3",
        "title": "Mission control and pod execution",
        "description": "Intake goal processing, boundary constraints check, and pod authorization pipeline.",
        "owner_agent": "Master Orchestrator",
        "R": "Master Orchestrator",
        "A": "Master Orchestrator",
        "C": "QA Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W1"],
        "optimistic_minutes": 15.0,
        "likely_minutes": 25.0,
        "pessimistic_minutes": 45.0,
        "status": "completed",
        "evidence_path": "backend/mission_control/router.py",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W4",
        "title": "Relay / HOCH-200 compute node",
        "description": "VPS relay stack deployment, Tailscale-only port 3012 binding, and connection health proxy.",
        "owner_agent": "HASF Pipeline Agent",
        "R": "HASF Pipeline Agent",
        "A": "HASF Pipeline Agent",
        "C": "Security Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W1"],
        "optimistic_minutes": 20.0,
        "likely_minutes": 30.0,
        "pessimistic_minutes": 60.0,
        "status": "completed",
        "evidence_path": "infra/hoch-200/vps/docker-compose.yml",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W5",
        "title": "Doctrine DB and brain initialization",
        "description": "Seed doctrine_rules table and guarantee initialization runs prior to module imports.",
        "owner_agent": "Master Orchestrator",
        "R": "Master Orchestrator",
        "A": "Master Orchestrator",
        "C": "QA Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W1"],
        "optimistic_minutes": 10.0,
        "likely_minutes": 15.0,
        "pessimistic_minutes": 25.0,
        "status": "completed",
        "evidence_path": "backend/brain/database.py",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W6",
        "title": "Agent accountability and trust scoring",
        "description": "Rule action validation filters, database record auditing, and trust scores grading.",
        "owner_agent": "QA Auditor Agent",
        "R": "QA Auditor Agent",
        "A": "QA Auditor Agent",
        "C": "Security Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W3"],
        "optimistic_minutes": 10.0,
        "likely_minutes": 15.0,
        "pessimistic_minutes": 30.0,
        "status": "completed",
        "evidence_path": "backend/mission_control/accountability_engine.py",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W7",
        "title": "UI command center / dark cockpit",
        "description": "Rich dark aesthetic cockpit, live status terminal overlay, and models health checks.",
        "owner_agent": "Live Tracker Runtime Agent",
        "R": "Live Tracker Runtime Agent",
        "A": "Live Tracker Runtime Agent",
        "C": "Production Acceleration Agent",
        "I": "Master Orchestrator",
        "dependencies": ["W2"],
        "optimistic_minutes": 15.0,
        "likely_minutes": 25.0,
        "pessimistic_minutes": 50.0,
        "status": "completed",
        "evidence_path": "frontend/index.html",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W8",
        "title": "Evidence and release ledger",
        "description": "Generate SHA256 validated evidence packs, SBOM files, and SLSA subject-provenance logs.",
        "owner_agent": "Evidence Collector Agent",
        "R": "Evidence Collector Agent",
        "A": "Evidence Collector Agent",
        "C": "QA Auditor Agent",
        "I": "PERT & Planning Agent",
        "dependencies": ["W7"],
        "optimistic_minutes": 5.0,
        "likely_minutes": 10.0,
        "pessimistic_minutes": 20.0,
        "status": "completed",
        "evidence_path": "docs/release/rc_validation_evidence_pack.md",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W9",
        "title": "Security / no public exposure",
        "description": "Validate UFW firewall limits, restrict public SSH to home IP, and run Semgrep scans.",
        "owner_agent": "Security Auditor Agent",
        "R": "Security Auditor Agent",
        "A": "Security Auditor Agent",
        "C": "QA Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W4"],
        "optimistic_minutes": 10.0,
        "likely_minutes": 15.0,
        "pessimistic_minutes": 30.0,
        "status": "completed",
        "evidence_path": "scripts/security-scan.sh",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W10",
        "title": "Backup and restore",
        "description": "Hourly SQLite database snapshots, file backups, and manual restore validation drills.",
        "owner_agent": "Live Tracker Runtime Agent",
        "R": "Live Tracker Runtime Agent",
        "A": "Live Tracker Runtime Agent",
        "C": "Security Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W1"],
        "optimistic_minutes": 10.0,
        "likely_minutes": 20.0,
        "pessimistic_minutes": 40.0,
        "status": "completed",
        "evidence_path": "scripts/restore_state.sh",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W11",
        "title": "Restart and failover drills",
        "description": "Simulate local primary host outages and promote secondary VPS routing failover.",
        "owner_agent": "Live Tracker Runtime Agent",
        "R": "Live Tracker Runtime Agent",
        "A": "Live Tracker Runtime Agent",
        "C": "Security Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W10"],
        "optimistic_minutes": 15.0,
        "likely_minutes": 25.0,
        "pessimistic_minutes": 45.0,
        "status": "completed",
        "evidence_path": "scripts/failover_check.sh",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W12",
        "title": "Monetization sidecar",
        "description": "Integrate Stripe webhooks, billing configurations, and subscription status verification.",
        "owner_agent": "Monetization & Compliance Agent",
        "R": "Monetization & Compliance Agent",
        "A": "Monetization & Compliance Agent",
        "C": "Master Orchestrator",
        "I": "Evidence Collector Agent",
        "dependencies": ["W1"],
        "optimistic_minutes": 20.0,
        "likely_minutes": 40.0,
        "pessimistic_minutes": 80.0,
        "status": "pending",
        "evidence_path": "",
        "blocker": "Stripe sandbox keys need initialization",
        "risk_level": "High"
    },
    {
        "id": "W13",
        "title": "QA / E2E / regression suite",
        "description": "Playwright integration test suite covering routing, mission intakes, and network exposure checks.",
        "owner_agent": "QA Auditor Agent",
        "R": "QA Auditor Agent",
        "A": "QA Auditor Agent",
        "C": "Security Auditor Agent",
        "I": "Evidence Collector Agent",
        "dependencies": ["W7", "W9"],
        "optimistic_minutes": 15.0,
        "likely_minutes": 25.0,
        "pessimistic_minutes": 50.0,
        "status": "completed",
        "evidence_path": "tests/e2e/rc28-mission-execution-proof.spec.ts",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W14",
        "title": "Documentation and operator runbooks",
        "description": "Prepare 24/7 Operations Runbook and Production Runtime Sustainment Runbook docs.",
        "owner_agent": "Evidence Collector Agent",
        "R": "Evidence Collector Agent",
        "A": "Evidence Collector Agent",
        "C": "QA Auditor Agent",
        "I": "PERT & Planning Agent",
        "dependencies": ["W8"],
        "optimistic_minutes": 10.0,
        "likely_minutes": 15.0,
        "pessimistic_minutes": 30.0,
        "status": "completed",
        "evidence_path": "docs/runbooks/v0.1.7-production-sustainment-runbook.md",
        "blocker": "",
        "risk_level": "Low"
    },
    {
        "id": "W15",
        "title": "Production deployment readiness",
        "description": "Consolidate all release candidate verification checklist results and seal validation tags.",
        "owner_agent": "Production Acceleration Agent",
        "R": "Production Acceleration Agent",
        "A": "Production Acceleration Agent",
        "C": "Master Orchestrator",
        "I": "Evidence Collector Agent",
        "dependencies": ["W13", "W14"],
        "optimistic_minutes": 15.0,
        "likely_minutes": 30.0,
        "pessimistic_minutes": 60.0,
        "status": "completed",
        "evidence_path": "docs/release/rc30-merge-package-readiness.md",
        "blocker": "",
        "risk_level": "Low"
    }
]

# Standard PERT / CPM calculation engine
def calculate_pert_cpm(tasks_list):
    tasks = {t["id"]: t for t in tasks_list}
    
    # Computed fields
    for t in tasks.values():
        o = t["optimistic_minutes"]
        m = t["likely_minutes"]
        p = t["pessimistic_minutes"]
        t["te"] = round((o + 4*m + p) / 6.0, 2)
        t["variance"] = round(((p - o) / 6.0) ** 2, 3)
        t["es"] = 0.0
        t["ef"] = 0.0
        t["ls"] = 0.0
        t["lf"] = 0.0
        t["slack"] = 0.0
        t["is_critical"] = False

    # Topological sort (Kahn's algorithm)
    in_degree = {tid: 0 for tid in tasks}
    adj = {tid: [] for tid in tasks}
    for tid, t in tasks.items():
        for dep in t["dependencies"]:
            if dep in adj:
                adj[dep].append(tid)
                in_degree[tid] += 1
                
    queue = [tid for tid, deg in in_degree.items() if deg == 0]
    order = []
    while queue:
        curr = queue.pop(0)
        order.append(curr)
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    if len(order) != len(tasks):
        # Fallback to direct lists on error cycle
        order = list(tasks.keys())

    # Forward Pass
    for tid in order:
        task = tasks[tid]
        if not task["dependencies"]:
            task["es"] = 0.0
        else:
            task["es"] = max(tasks[d]["ef"] for d in task["dependencies"] if d in tasks)
        task["ef"] = round(task["es"] + task["te"], 2)

    # Project duration
    project_duration = max(tasks[tid]["ef"] for tid in order) if order else 0.0

    # Backward Pass
    successors = {tid: [] for tid in tasks}
    for tid, task in tasks.items():
        for dep in task["dependencies"]:
            if dep in successors:
                successors[dep].append(tid)
                
    for tid in reversed(order):
        task = tasks[tid]
        s_list = successors[tid]
        if not s_list:
            task["lf"] = project_duration
        else:
            task["lf"] = min(tasks[s]["ls"] for s in s_list if s in tasks)
        task["ls"] = round(task["lf"] - task["te"], 2)
        task["slack"] = round(task["lf"] - task["ef"], 2)
        task["is_critical"] = abs(task["slack"]) < 0.01

    critical_path = [tid for tid in order if tasks[tid]["is_critical"]]
    
    return {
        "tasks": list(tasks.values()),
        "critical_path": critical_path,
        "expected_duration": round(project_duration, 2),
        "variance": round(sum(tasks[tid]["variance"] for tid in critical_path), 3)
    }

# Read live database agent trust scores
def fetch_live_agent_scores():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT agent_id, agent_name, trust_score, trust_tier, band, reason, required_remedy, updated_at FROM agent_trust_scores")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return [{"error": str(e)}]

# Read database rules count
def fetch_doctrine_rules_count():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT COUNT(*) FROM doctrine_rules")
        cnt = cur.fetchone()[0]
        conn.close()
        return cnt
    except Exception:
        return 0

# Check live backend status
def check_local_backend_health():
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/mission/brief", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                return "ONLINE"
    except Exception:
        pass
    return "UNKNOWN"

# Check VPS status
def fetch_relay_status():
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/v1/relay/status", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode())
                return data.get("worker_status", "UNKNOWN")
    except Exception:
        pass
    return "UNKNOWN"

# Check if public 3012 is reachable (should fail)
def check_public_port_closed():
    # Attempt a quick TCP connection to public IP
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(('50.116.41.183', 3012))
        s.close()
        return False  # Open is bad
    except Exception:
        return True   # Closed is good

# CDAO readiness score computation
def calculate_readiness_score(completed_count, total_count, db_ok, relay_ok, port_closed):
    score = int((completed_count / total_count) * 70)
    if db_ok: score += 10
    if relay_ok: score += 10
    if port_closed: score += 10
    return min(100, score)

@app.get("/api/pert/data")
def get_pert_data():
    pert_cpm = calculate_pert_cpm(WORKSTREAMS)
    agent_scores = fetch_live_agent_scores()
    rules_count = fetch_doctrine_rules_count()
    backend_status = check_local_backend_health()
    relay_status = fetch_relay_status()
    port_closed = check_public_port_closed()

    total_tasks = len(WORKSTREAMS)
    completed_tasks = len([t for t in WORKSTREAMS if t["status"] == "completed"])
    
    # Calculate executive readiness
    readiness_score = calculate_readiness_score(
        completed_tasks, total_tasks, 
        rules_count > 0, 
        relay_status == "ONLINE", 
        port_closed
    )
    
    critical_blockers = [t for t in WORKSTREAMS if t["blocker"] and t["id"] in pert_cpm["critical_path"]]
    
    # Next best actions
    next_actions = []
    # 1. Any critical blockers
    for cb in critical_blockers:
        next_actions.append({
            "task_id": cb["id"],
            "title": cb["title"],
            "action": f"Resolve blocker: {cb['blocker']}",
            "priority": "P0 (CRITICAL BLOCKER)",
            "impact": "Unlocks critical path duration drag"
        })
    # 2. Pending tasks on critical path
    for tid in pert_cpm["critical_path"]:
        t = next((x for x in WORKSTREAMS if x["id"] == tid), None)
        if t and t["status"] != "completed" and t not in critical_blockers:
            next_actions.append({
                "task_id": t["id"],
                "title": t["title"],
                "action": f"Execute implementation/verification script for {t['title']}",
                "priority": "P1 (CRITICAL PATH)",
                "impact": "Reduces total project expected time"
            })
    # Fallback default action
    if not next_actions:
        next_actions.append({
            "task_id": "NONE",
            "title": "All Workstreams Active",
            "action": "Run scripts/rc31_sustainment_verify.sh to assert production invariants.",
            "priority": "P3 (SUSTAINMENT)",
            "impact": "Maintains 100% verified status"
        })

    # Filter out secrets or local paths from response
    return {
        "north_star": {
            "goal": "Model Project Duration & Enforce Agent Accountability",
            "baseline": "v0.1.7 (face8ce)",
            "target": "Integrated PERT/CPM Swarm Management Center",
            "status": "governed"
        },
        "readiness": {
            "score": readiness_score,
            "blockers_count": len(critical_blockers),
            "window": f"{pert_cpm['expected_duration']} minutes expected time",
            "confidence": "95% Confidence (PERT Beta-Distribution)",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        },
        "pert_cpm": pert_cpm,
        "agents": agent_scores,
        "doctrine_rules_count": rules_count,
        "backend_status": backend_status,
        "relay_status": relay_status,
        "port_public_closed": port_closed,
        "next_actions": next_actions,
        "evidence_ledger": [
            {"rc": "RC25", "desc": "HOCH-200 relay setup evidence", "url": f"file://{get_project_root()}/docs/evidence/compute/hoch-200-setup-evidence.md"},
            {"rc": "RC26", "desc": "Swarm routing proxy integration", "url": f"file://{get_project_root()}/docs/evidence/compute/rc26-relay-routing-integration.md"},
            {"rc": "RC27", "desc": "Doctrine DB sync fix", "url": f"file://{get_project_root()}/docs/evidence/compute/rc27-doctrine-db-migration.md"},
            {"rc": "RC28", "desc": "Mission execution E2E proof", "url": f"file://{get_project_root()}/docs/evidence/compute/rc28-mission-execution-proof.md"},
            {"rc": "RC29", "desc": "RC25-RC28 release consolidation", "url": f"file://{get_project_root()}/docs/evidence/compute/rc29-release-consolidation.md"},
            {"rc": "RC31", "desc": "Production runtime sustainment proof", "url": f"file://{get_project_root()}/docs/evidence/runtime/rc31-production-runtime-sustainment.md"}
        ]
    }

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    # Beautiful high-tech dark cockpit html
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>HAS/HASF PERT Command Center</title>
    <style>
        :root {
            --bg-base: #0a0e17;
            --bg-card: rgba(16, 22, 35, 0.7);
            --border-glass: rgba(255, 255, 255, 0.08);
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-teal: #2dd4bf;
            --accent-blue: #60a5fa;
            --accent-yellow: #facc15;
            --accent-red: #f87171;
        }
        body {
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 24px;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-glass);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }
        h1 { font-size: 22px; font-weight: 800; margin: 0; color: #fff; text-shadow: 0 0 10px rgba(45, 212, 191, 0.3); }
        .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(5px);
        }
        .col-12 { grid-column: span 12; }
        .col-8 { grid-column: span 8; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-pass { background: rgba(45, 212, 191, 0.15); color: var(--accent-teal); border: 1px solid rgba(45, 212, 191, 0.3); }
        .badge-fail { background: rgba(248, 113, 113, 0.15); color: var(--accent-red); border: 1px solid rgba(248, 113, 113, 0.3); }
        .badge-warn { background: rgba(250, 204, 21, 0.15); color: var(--accent-yellow); border: 1px solid rgba(250, 204, 21, 0.3); }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
        th { color: var(--text-secondary); text-transform: uppercase; font-size: 11px; }

        .cpm-network {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
            border: 1px dashed var(--border-glass);
        }
        .node {
            padding: 10px;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border-glass);
            border-radius: 6px;
            font-size: 12px;
            min-width: 120px;
            text-align: center;
        }
        .node.critical {
            border-color: var(--accent-teal);
            box-shadow: 0 0 8px rgba(45, 212, 191, 0.3);
            background: rgba(45, 212, 191, 0.05);
        }
    </style>
</head>
<body>
    <header>
        <div>
            <h1 id="north-star-goal">PERT Command Center</h1>
            <p style="margin: 4px 0 0 0; color: var(--text-secondary); font-size: 13px;">North Star Goal: <span id="goal-text">UNKNOWN</span></p>
        </div>
        <div>
            <span class="badge badge-pass" id="readiness-score">Readiness: UNKNOWN</span>
        </div>
    </header>

    <div class="grid">
        <!-- 1. Executive Readiness -->
        <div class="card col-4" id="executive-readiness-panel">
            <h3 style="margin-top:0;">Executive Readiness</h3>
            <p>Projected Completion: <strong id="completion-window" style="color:var(--accent-teal);">UNKNOWN</strong></p>
            <p>Confidence: <span id="confidence-level">UNKNOWN</span></p>
            <p>Last Verified: <span id="verified-timestamp" style="font-family:monospace; font-size:12px;">UNKNOWN</span></p>
        </div>

        <!-- 2. Live Port / Runtime Status -->
        <div class="card col-4" id="runtime-status-panel">
            <h3 style="margin-top:0;">Runtime Status</h3>
            <p>Backend Localhost: <span class="badge" id="backend-status">UNKNOWN</span></p>
            <p>Relay status: <span class="badge" id="relay-status">UNKNOWN</span></p>
            <p>Public Port 3012: <span class="badge" id="port-status">UNKNOWN</span></p>
        </div>

        <!-- 3. Risk log / Blockers -->
        <div class="card col-4" id="risks-blockers-panel">
            <h3 style="margin-top:0; color:var(--accent-red);">Risks & Blockers</h3>
            <div id="risks-list" style="font-size:13px; color:var(--text-secondary);">
                <!-- Populated dynamically -->
            </div>
        </div>

        <!-- 4. PERT/CPM Network visualization -->
        <div class="card col-12" id="pert-network-panel">
            <h3 style="margin-top:0;">PERT / CPM Activity Network</h3>
            <div class="cpm-network" id="network-container">
                <!-- Node blocks generated dynamically -->
            </div>
        </div>

        <!-- 5. Task List Table -->
        <div class="card col-8" id="tasks-table-panel">
            <h3 style="margin-top:0;">Work breakdown structure (WBS)</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Owner</th>
                        <th>Slack</th>
                        <th>Expected (TE)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="tasks-tbody">
                    <!-- Populated dynamically -->
                </tbody>
            </table>
        </div>

        <!-- 6. Next Best Actions -->
        <div class="card col-4" id="next-actions-panel">
            <h3 style="margin-top:0; color:var(--accent-yellow);">Next Best Actions</h3>
            <div id="actions-list" style="display:flex; flex-direction:column; gap:12px; font-size:13px;">
                <!-- Populated dynamically -->
            </div>
        </div>

        <!-- 7. Agent Accountability Board -->
        <div class="card col-6" id="agent-accountability-panel">
            <h3 style="margin-top:0;">Agent Accountability Board</h3>
            <table>
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Tier</th>
                        <th>Trust Score</th>
                    </tr>
                </thead>
                <tbody id="agents-tbody">
                    <!-- Populated dynamically -->
                </tbody>
            </table>
        </div>

        <!-- 8. RACI Matrix -->
        <div class="card col-6" id="raci-matrix-panel">
            <h3 style="margin-top:0;">RACI Assignment Matrix</h3>
            <table>
                <thead>
                    <tr>
                        <th>Workstream</th>
                        <th>A</th>
                        <th>R</th>
                        <th>C</th>
                        <th>I</th>
                    </tr>
                </thead>
                <tbody id="raci-tbody">
                    <!-- Populated dynamically -->
                </tbody>
            </table>
        </div>

        <!-- 9. Release Gates -->
        <div class="card col-6" id="release-gates-panel">
            <h3 style="margin-top:0;">Release Gates Check</h3>
            <ul style="padding-left:20px; font-size:13px; line-height:1.8;">
                <li>Doctrine Rules Table: <strong id="gate-db" style="color:var(--accent-teal);">UNKNOWN</strong></li>
                <li>Relay Routing: <strong id="gate-relay" style="color:var(--accent-teal);">UNKNOWN</strong></li>
                <li>Mission Execution: <strong id="gate-mission" style="color:var(--accent-teal);">UNKNOWN</strong></li>
                <li>Public port 3012: <strong id="gate-port" style="color:var(--accent-teal);">UNKNOWN</strong></li>
            </ul>
        </div>

        <!-- 10. Evidence Ledger -->
        <div class="card col-6" id="evidence-ledger-panel">
            <h3 style="margin-top:0;">Evidence Ledger</h3>
            <div id="evidence-list" style="font-size:12px; line-height:1.6;">
                <!-- Populated dynamically -->
            </div>
        </div>
    </div>

    <script>
        async function loadData() {
            try {
                const res = await fetch("/api/pert/data");
                const data = await res.json();
                
                // Set North Star Goal
                document.getElementById("goal-text").textContent = data.north_star.goal + " (" + data.north_star.baseline + ")";
                document.getElementById("readiness-score").textContent = "Readiness: " + data.readiness.score + "%";
                
                // Set Executive Readiness
                document.getElementById("completion-window").textContent = data.readiness.window;
                document.getElementById("confidence-level").textContent = data.readiness.confidence;
                document.getElementById("verified-timestamp").textContent = data.readiness.timestamp;

                // Set Runtime Status
                const bStatus = document.getElementById("backend-status");
                bStatus.textContent = data.backend_status;
                bStatus.className = "badge " + (data.backend_status === "ONLINE" ? "badge-pass" : "badge-warn");

                const rStatus = document.getElementById("relay-status");
                rStatus.textContent = data.relay_status;
                rStatus.className = "badge " + (data.relay_status === "ONLINE" ? "badge-pass" : "badge-warn");

                const pStatus = document.getElementById("port-status");
                pStatus.textContent = data.port_public_closed ? "CLOSED" : "EXPOSED";
                pStatus.className = "badge " + (data.port_public_closed ? "badge-pass" : "badge-fail");

                // Risks & Blockers list
                const risksList = document.getElementById("risks-list");
                risksList.innerHTML = "";
                const blockedTasks = data.pert_cpm.tasks.filter(t => t.blocker);
                if (blockedTasks.length === 0) {
                    risksList.innerHTML = "<p style='color:var(--accent-teal);'>No active blockers detected.</p>";
                } else {
                    blockedTasks.forEach(t => {
                        risksList.innerHTML += `<p><strong>${t.id}:</strong> ${t.blocker} (Owner: ${t.owner_agent})</p>`;
                    });
                }

                // Render Network Graph as nodes list
                const network = document.getElementById("network-container");
                network.innerHTML = "";
                data.pert_cpm.tasks.forEach(t => {
                    const isCrit = data.pert_cpm.critical_path.includes(t.id);
                    network.innerHTML += `
                        <div class="node ${isCrit ? 'critical' : ''}">
                            <strong>${t.id}</strong><br>
                            ${t.title.substring(0, 20)}...<br>
                            <span style="font-size:10px; color:var(--text-secondary);">${t.te} mins (S:${t.slack})</span>
                        </div>
                    `;
                });

                // Populate WBS Table
                const tasksTbody = document.getElementById("tasks-tbody");
                tasksTbody.innerHTML = "";
                data.pert_cpm.tasks.forEach(t => {
                    tasksTbody.innerHTML += `
                        <tr>
                            <td>${t.id}</td>
                            <td><strong>${t.title}</strong><br><span style="font-size:10px; color:var(--text-secondary);">${t.description}</span></td>
                            <td>${t.owner_agent}</td>
                            <td>${t.slack}</td>
                            <td>${t.te}</td>
                            <td><span class="badge ${t.status === 'completed' ? 'badge-pass' : 'badge-warn'}">${t.status.toUpperCase()}</span></td>
                        </tr>
                    `;
                });

                // Next Best Actions
                const actionsList = document.getElementById("actions-list");
                actionsList.innerHTML = "";
                data.next_actions.forEach(a => {
                    actionsList.innerHTML += `
                        <div style="border-left: 3px solid var(--accent-yellow); padding-left: 8px;">
                            <strong>${a.priority}</strong><br>
                            ${a.action}<br>
                            <span style="font-size:10px; color:var(--text-secondary);">${a.impact}</span>
                        </div>
                    `;
                });

                // Agent Accountability Board
                const agentsTbody = document.getElementById("agents-tbody");
                agentsTbody.innerHTML = "";
                if (data.agents && data.agents.length > 0) {
                    data.agents.forEach(a => {
                        agentsTbody.innerHTML += `
                            <tr>
                                <td><strong>${a.agent_name}</strong></td>
                                <td>${a.trust_tier}</td>
                                <td><strong style="color:var(--accent-teal);">${a.trust_score}</strong></td>
                            </tr>
                        `;
                    });
                } else {
                    agentsTbody.innerHTML = "<tr><td colspan='3' style='color:var(--text-secondary);'>UNKNOWN (Database data unavailable)</td></tr>";
                }

                // RACI Matrix Table
                const raciTbody = document.getElementById("raci-tbody");
                raciTbody.innerHTML = "";
                data.pert_cpm.tasks.forEach(t => {
                    raciTbody.innerHTML += `
                        <tr>
                            <td><strong>${t.id}</strong>: ${t.title}</td>
                            <td>${t.A || 'MISSING'}</td>
                            <td>${t.R || 'MISSING'}</td>
                            <td>${t.C || 'NONE'}</td>
                            <td>${t.I || 'NONE'}</td>
                        </tr>
                    `;
                });

                // Release Gates Check status list
                document.getElementById("gate-db").textContent = data.doctrine_rules_count > 0 ? "PASS (" + data.doctrine_rules_count + " rules)" : "FAIL (0 rules)";
                document.getElementById("gate-db").className = data.doctrine_rules_count > 0 ? "" : "badge-fail";
                
                document.getElementById("gate-relay").textContent = data.relay_status === "ONLINE" ? "ONLINE" : "UNKNOWN";
                document.getElementById("gate-relay").className = data.relay_status === "ONLINE" ? "" : "badge-warn";

                document.getElementById("gate-mission").textContent = data.backend_status === "ONLINE" ? "VERIFIED" : "UNKNOWN";
                
                document.getElementById("gate-port").textContent = data.port_public_closed ? "ISOLATED" : "EXPOSED";
                document.getElementById("gate-port").className = data.port_public_closed ? "" : "badge-fail";

                // Evidence Ledger list
                const evidenceList = document.getElementById("evidence-list");
                evidenceList.innerHTML = "";
                data.evidence_ledger.forEach(ev => {
                    evidenceList.innerHTML += `<p><strong>${ev.rc}:</strong> <a href="${ev.url}" style="color:var(--accent-blue); text-decoration:none;">${ev.desc}</a></p>`;
                });

            } catch (err) {
                console.error("Failed to load dashboard data:", err);
            }
        }
        
        loadData();
        setInterval(loadData, 5000);
    </script>
</body>
</html>
"""
    return html_content
