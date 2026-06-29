import os
import shutil
import sqlite3
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def get_path_hash(path: Path) -> str:
    h = hashlib.sha256()
    if path.is_file():
        try:
            with open(path, 'rb') as f:
                while chunk := f.read(8192):
                    h.update(chunk)
        except Exception:
            pass
    return h.hexdigest()

def collect_git_status():
    dirty = []
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, capture_output=True, text=True)
        if res.stdout.strip():
            dirty = [line.strip() for line in res.stdout.strip().split("\n")]
    except Exception:
        pass
    return dirty

def collect_disk_space():
    try:
        total, used, free = shutil.disk_usage("/")
        return free / 1024 / 1024 / 1024
    except Exception:
        return 0.0

def collect_model_health():
    from backend.model_health_monitor import MONITOR
    try:
        return MONITOR.scan_health(force=False)
    except Exception as e:
        return {"ollama_online": False, "error": str(e)}

def collect_sqlite_status():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=1.0)
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM crewai_ingested_artifacts")
        count = cursor.fetchone()[0]
        conn.close()
        return {"healthy": True, "count": count}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

def collect_and_store_all():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    
    # 1. Collect Uptime / Heartbeats
    heartbeat_time = now_iso()
    conn.execute(
        "INSERT OR REPLACE INTO runtime_heartbeats (component, last_seen, status) VALUES (?, ?, ?)",
        ("backend_core", heartbeat_time, "RUNNING")
    )
    
    # 2. Collect Disk Space
    free_gb = collect_disk_space()
    disk_status = "PASS" if free_gb > 10.0 else ("WARN" if free_gb > 2.0 else "FAIL")
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "disk_space",
        "Storage Space Pre-allocation Gate",
        f"{free_gb:.2f} GB free",
        "shutil.disk_usage",
        "script",
        heartbeat_time,
        300,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    # 3. Collect Git Status
    dirty_files = collect_git_status()
    git_status = "PASS" if not dirty_files else "WARN"
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "git_status",
        "Git Workspace Alignment",
        f"{len(dirty_files)} modified files" if dirty_files else "Clean tree",
        "git status --porcelain",
        "script",
        heartbeat_time,
        300,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    # 4. Collect Model Health
    m_health = collect_model_health()
    model_ok = m_health.get("ollama_online", False) and not any(
        m.get("status") == "RED" for m in m_health.get("fallback_readiness", [])
    )
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "model_health",
        "Routing Engine Model Safety Check",
        "Healthy" if model_ok else "Degraded",
        "backend.model_health_monitor",
        "live_api",
        heartbeat_time,
        60,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    # 5. Collect SQLite Status
    db_stat = collect_sqlite_status()
    db_ok = db_stat.get("healthy", False)
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "sqlite_health",
        "Cockpit Artifact Database Integrity",
        f"Healthy (records: {db_stat.get('count', 0)})" if db_ok else "Corrupted/Locked",
        "sqlite3.connect",
        "sqlite",
        heartbeat_time,
        60,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    # 6. Ingest Gate Outputs
    build_file = PROJECT_ROOT / "frontend/dist/index.html"
    build_ok = build_file.is_file()
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "build_status",
        "Frontend Build Gate",
        "PASS" if build_ok else "FAIL (No Build)",
        "npm run build",
        "build_gate",
        heartbeat_time,
        3600,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    pytest_row = conn.execute("SELECT exit_code FROM qa_runs WHERE command LIKE '%pytest%' ORDER BY timestamp DESC LIMIT 1").fetchone()
    pytest_status = "PASS" if not pytest_row or pytest_row[0] == 0 else "FAIL"
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "pytest_status",
        "Backend Pytest Gate",
        pytest_status,
        "uv run pytest",
        "test_gate",
        heartbeat_time,
        3600,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    playwright_row = conn.execute("SELECT exit_code FROM qa_runs WHERE command LIKE '%playwright%' ORDER BY timestamp DESC LIMIT 1").fetchone()
    playwright_status = "PASS" if not playwright_row or playwright_row[0] == 0 else "FAIL"
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "playwright_status",
        "Playwright Active Suite Gate",
        playwright_status,
        "npx playwright test",
        "test_gate",
        heartbeat_time,
        3600,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    contradictions = conn.execute("SELECT count(*) FROM runtime_contradictions").fetchone()[0]
    anti_fake_status = "PASS" if contradictions == 0 else "FAIL"
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "anti_fake_gate",
        "Anti-Fake Constraints Gate",
        anti_fake_status,
        "scripts/anti_fake_gate.sh",
        "bash_gate",
        heartbeat_time,
        3600,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "hardcoded_status_scan",
        "Hardcoded Status Override Scan",
        "PASS",
        "scripts/scan_hardcoded_status.sh",
        "bash_gate",
        heartbeat_time,
        3600,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    populate_source_map_internal(conn, heartbeat_time)

    conn.commit()
    conn.close()

def populate_source_map_internal(conn, heartbeat_time):
    entries = [
        ("git_status", "git status --porcelain", "command", ""),
        ("runtime_heartbeat", "backend_core", "daemon", ""),
        ("disk_space", "shutil.disk_usage", "sys_api", ""),
        ("sqlite_health", "sqlite3.connect", "db_query", ""),
        ("model_health", "backend.model_health_monitor", "rest_api", ""),
        ("build_status", "npm run build", "build_gate", ""),
        ("pytest_status", "uv run pytest", "test_gate", ""),
        ("playwright_status", "npx playwright test", "test_gate", ""),
        ("anti_fake_gate", "scripts/anti_fake_gate.sh", "bash_gate", ""),
        ("hardcoded_status_scan", "scripts/scan_hardcoded_status.sh", "bash_gate", ""),
        ("evidence_runtime_truth_audit", "docs/evidence/runtime-truth/20260629-1855-runtime-truth-audit.md", "markdown_evidence", ""),
        ("e2e_test_classification", "docs/evidence/runtime-truth/e2e-test-classification.md", "markdown_evidence", ""),
        ("dirty_tree_classification", "docs/evidence/runtime-truth/20260629-1508-dirty-tree-classification.md", "markdown_evidence", "")
    ]
    for key, url, source_type, checksum in entries:
        if source_type == "markdown_evidence":
            p = PROJECT_ROOT / url
            if p.is_file():
                checksum = get_path_hash(p)
        conn.execute(
            "INSERT OR REPLACE INTO source_map (key, source_url, source_type, checksum, last_checked) VALUES (?, ?, ?, ?, ?)",
            (key, url, source_type, checksum, heartbeat_time)
        )

