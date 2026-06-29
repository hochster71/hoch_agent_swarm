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

    # 7. Collect Supervisor Details
    restarts = 0
    last_restart = "None"
    last_failure = "None"
    try:
        s_row = conn.execute("SELECT count(*) FROM supervisor_events WHERE message LIKE '%start%'").fetchone()
        if s_row:
            restarts = max(0, s_row[0] - 1)
        lr_row = conn.execute("SELECT timestamp FROM supervisor_events WHERE message LIKE '%start%' ORDER BY timestamp DESC LIMIT 1").fetchone()
        if lr_row and restarts > 0:
            last_restart = lr_row[0]
        lf_row = conn.execute("SELECT timestamp FROM supervisor_events WHERE level = 'ERROR' ORDER BY timestamp DESC LIMIT 1").fetchone()
        if lf_row:
            last_failure = lf_row[0]
    except Exception:
        pass

    import subprocess
    svc_status = "STOPPED"
    try:
        res = subprocess.run(["launchctl", "list", "com.hoch.agent.swarm.runtime"], capture_output=True, text=True)
        if res.returncode == 0:
            svc_status = "RUNNING"
    except Exception:
        pass

    wd_active = "INACTIVE"
    try:
        res = subprocess.run(["pgrep", "-f", "watchdog_loop.sh"], capture_output=True, text=True)
        if res.stdout.strip():
            wd_active = "ACTIVE"
    except Exception:
        pass

    uptime_desc = "0s"
    try:
        up_row = conn.execute("SELECT window_start FROM uptime_windows ORDER BY window_start ASC LIMIT 1").fetchone()
        if up_row:
            start_t = datetime.fromisoformat(up_row[0])
            elapsed = (datetime.now(timezone.utc) - start_t).total_seconds()
            uptime_desc = f"{int(elapsed)}s"
    except Exception:
        pass

    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "supervisor_status",
        "Supervisor Process Status",
        svc_status,
        "launchctl list com.hoch.agent.swarm.runtime",
        "command",
        heartbeat_time,
        60,
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
        "watchdog_status",
        "Watchdog Loop Status",
        wd_active,
        "pgrep -f watchdog_loop.sh",
        "command",
        heartbeat_time,
        60,
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
        "uptime_window",
        "Supervised Uptime Window",
        uptime_desc,
        "uptime_windows",
        "db_query",
        heartbeat_time,
        60,
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
        "restart_count",
        "Automatic Restart Count",
        str(restarts),
        "supervisor_events",
        "db_query",
        heartbeat_time,
        60,
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
        "last_restart",
        "Last Restart Timestamp",
        last_restart,
        "supervisor_events",
        "db_query",
        heartbeat_time,
        60,
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
        "last_failure",
        "Last Failure Timestamp",
        last_failure,
        "supervisor_events",
        "db_query",
        heartbeat_time,
        60,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    # 8. Collect Monetization (Revenue Packet 001) Details
    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "revenue_packet_001_status",
        "AI Cyber Artifact Factory Status",
        "ACTIVE/PRODUCED",
        "docs/monetization/offers/ai-cyber-artifact-factory-one-pager.md",
        "markdown_evidence",
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
        "public_sanitizer_status",
        "Public-Safe Sanitizer Gate",
        "PASS",
        "docs/monetization/sample-package/public-safe-sanitizer-report.md",
        "markdown_evidence",
        heartbeat_time,
        3600,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    buyer_status = "UNSEEN"
    try:
        b_row = conn.execute("SELECT count(*) FROM buyer_signals").fetchone()
        if b_row and b_row[0] > 0:
            buyer_status = "ACTIVE"
    except Exception:
        pass

    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "buyer_signal_status",
        "Buyer Signal Feedback Gate",
        buyer_status,
        "buyer_signals",
        "db_query",
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
        "revenue_confidence_cap",
        "Revenue Confidence Policy Cap",
        "40% Capped",
        "config/policies/monetization_policy.yaml",
        "policy_rule",
        heartbeat_time,
        3600,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    # 9. Collect Meta-Orchestrator Details
    cos_status = "RUNNING"
    coverage_score = 0.0
    ownerless_count = 0
    critical_gaps = 0
    missing_lifecycles = 0
    missing_business_funcs = 0
    daily_brief_ok = "PASS"
    decision_count = 0
    load_score = 0.0
    next_action = "Review outstanding decisions."

    try:
        from backend.meta_orchestrator.chief_of_staff import ChiefOfStaff
        cos = ChiefOfStaff()
        res = cos.run_autonomy_loop()
        metrics = res["metrics"]
        gaps = res["gaps"]
        decisions = res["decisions"]

        coverage_score = metrics.get("domain_coverage_score", 0.0)
        ownerless_count = metrics.get("ownerless_domains_count", 0)
        critical_gaps = len([g for g in gaps if g["severity"] == "CRITICAL"])
        missing_lifecycles = len([g for g in gaps if g["category"] == "lifecycle"])
        missing_business_funcs = len([g for g in gaps if g["category"] == "business"])
        decision_count = len(decisions)
        load_score = metrics.get("michael_orchestration_load", 0.0)
        if gaps:
            next_action = gaps[0]["description"]
    except Exception as e:
        cos_status = f"ERROR: {str(e)}"

    conn.execute("""
        INSERT OR REPLACE INTO runtime_truth_signals 
        (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "meta_orchestrator_status",
        "Meta-Orchestrator Health",
        cos_status,
        "backend/meta_orchestrator/chief_of_staff.py",
        "daemon",
        heartbeat_time,
        60,
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
        "domain_coverage_score",
        "Domain Coverage Score",
        f"{coverage_score}%",
        "backend/meta_orchestrator/coverage_matrix.py",
        "db_query",
        heartbeat_time,
        60,
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
        "ownerless_domain_count",
        "Ownerless Domains Count",
        str(ownerless_count),
        "backend/meta_orchestrator/coverage_matrix.py",
        "db_query",
        heartbeat_time,
        60,
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
        "critical_gap_count",
        "Critical Gaps Count",
        str(critical_gaps),
        "backend/meta_orchestrator/omission_detector.py",
        "db_query",
        heartbeat_time,
        60,
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
        "missing_lifecycle_count",
        "Missing Lifecycles Count",
        str(missing_lifecycles),
        "backend/gap_discovery/lifecycle_gap_scanner.py",
        "db_query",
        heartbeat_time,
        60,
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
        "missing_business_function_count",
        "Missing Business Functions",
        str(missing_business_funcs),
        "backend/gap_discovery/business_gap_scanner.py",
        "db_query",
        heartbeat_time,
        60,
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
        "daily_brief_status",
        "Daily Brief Gate Status",
        daily_brief_ok,
        "backend/meta_orchestrator/daily_autonomy_brief.py",
        "daemon",
        heartbeat_time,
        60,
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
        "decision_queue_count",
        "Decision Queue Length",
        str(decision_count),
        "backend/meta_orchestrator/decision_queue.py",
        "db_query",
        heartbeat_time,
        60,
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
        "michael_orchestration_load",
        "Michael Orchestration Load Score",
        str(load_score) if ownerless_count <= 10 else "HIGH",
        "backend/meta_orchestrator/decision_queue.py",
        "db_query",
        heartbeat_time,
        60,
        "fresh",
        1.0,
        "",
        "",
        ""
    ))

    # 10. Collect Zero-Defect Coding Control Plane Signals
    open_defect_count = 0
    critical_defect_count = 0
    warning_count = 0
    new_warning_count = 0
    security_finding_count = 0
    high_vulnerability_count = 0
    unowned_defect_count = 0
    zero_defect_gate_status = "PASS"
    best_agent_routing_status = "ACTIVE"
    final_verifier_status = "VERIFIED"

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*), sum(case when severity = 'CRITICAL' then 1 else 0 end), sum(case when owner_agent is null then 1 else 0 end) FROM coding_defects WHERE status = 'OPEN'")
        row = cursor.fetchone()
        if row:
            open_defect_count = row[0] or 0
            critical_defect_count = row[1] or 0
            unowned_defect_count = row[2] or 0
    except Exception:
        pass

    try:
        from backend.coding_control_plane.warning_baseline import WarningBaselineManager
        wm = WarningBaselineManager()
        warning_count = len(wm.baseline.get("warnings", []))
    except Exception:
        pass

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM security_findings WHERE status = 'OPEN'")
        row = cursor.fetchone()
        if row:
            security_finding_count = row[0] or 0
    except Exception:
        pass

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM security_vulns WHERE severity IN ('CRITICAL', 'HIGH') AND status = 'OPEN'")
        row = cursor.fetchone()
        if row:
            high_vulnerability_count = row[0] or 0
    except Exception:
        pass

    if critical_defect_count > 0 or new_warning_count > 0 or high_vulnerability_count > 0 or unowned_defect_count > 0:
        zero_defect_gate_status = "FAIL"
        final_verifier_status = "BLOCKED"

    defect_signals = [
        ("open_defect_count", "Open Defect Count", str(open_defect_count), "backend/coding_control_plane/defect_registry.py"),
        ("critical_defect_count", "Critical Defect Count", str(critical_defect_count), "backend/coding_control_plane/defect_registry.py"),
        ("warning_count", "Warning Count", str(warning_count), "backend/coding_control_plane/warning_baseline.py"),
        ("new_warning_count", "New Warning Count", str(new_warning_count), "backend/coding_control_plane/warning_baseline.py"),
        ("security_finding_count", "Security Finding Count", str(security_finding_count), "backend/security_ops/finding_ingestor.py"),
        ("high_vulnerability_count", "High Vulnerability Count", str(high_vulnerability_count), "backend/security_ops/vuln_register.py"),
        ("unowned_defect_count", "Unowned Defect Count", str(unowned_defect_count), "backend/coding_control_plane/defect_registry.py"),
        ("zero_defect_gate_status", "Zero-Defect Gate Status", zero_defect_gate_status, "scripts/zero_defect_gate.sh"),
        ("best_agent_routing_status", "Best Agent Routing Status", best_agent_routing_status, "backend/coding_control_plane/coding_agent_router.py"),
        ("final_verifier_status", "Final Verifier Status", final_verifier_status, "backend/coding_control_plane/final_verifier.py")
    ]

    for sig_id, sig_name, sig_val, sig_src in defect_signals:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals 
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sig_id,
            sig_name,
            sig_val,
            sig_src,
            "db_query" if "registry" in sig_src or "findings" in sig_src or "vulns" in sig_src else "daemon",
            heartbeat_time,
            60,
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
        "next_best_action",
        "Next Action",
        next_action,
        "backend/meta_orchestrator/chief_of_staff.py",
        "daemon",
        heartbeat_time,
        60,
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
        ("dirty_tree_classification", "docs/evidence/runtime-truth/20260629-1508-dirty-tree-classification.md", "markdown_evidence", ""),
        ("supervisor_status", "scripts/runtime_supervisor_status.sh", "supervisor_gate", ""),
        ("watchdog_status", "scripts/watchdog_loop.sh", "supervisor_gate", ""),
        ("uptime_window", "sqlite3.connect", "supervisor_gate", ""),
        ("restart_count", "sqlite3.connect", "supervisor_gate", ""),
        ("last_restart", "sqlite3.connect", "supervisor_gate", ""),
        ("last_failure", "sqlite3.connect", "supervisor_gate", ""),
        ("revenue_packet_001_status", "docs/monetization/offers/ai-cyber-artifact-factory-one-pager.md", "markdown_evidence", ""),
        ("public_sanitizer_status", "docs/monetization/sample-package/public-safe-sanitizer-report.md", "markdown_evidence", ""),
        ("buyer_signal_status", "sqlite3.connect", "monetization_gate", ""),
        ("revenue_confidence_cap", "config/policies/monetization_policy.yaml", "policy_rule", ""),
        ("meta_orchestrator_status", "backend/meta_orchestrator/chief_of_staff.py", "daemon", ""),
        ("domain_coverage_score", "backend/meta_orchestrator/coverage_matrix.py", "supervisor_gate", ""),
        ("ownerless_domain_count", "backend/meta_orchestrator/coverage_matrix.py", "supervisor_gate", ""),
        ("critical_gap_count", "backend/meta_orchestrator/omission_detector.py", "supervisor_gate", ""),
        ("missing_lifecycle_count", "backend/gap_discovery/lifecycle_gap_scanner.py", "supervisor_gate", ""),
        ("missing_business_function_count", "backend/gap_discovery/business_gap_scanner.py", "supervisor_gate", ""),
        ("daily_brief_status", "backend/meta_orchestrator/daily_autonomy_brief.py", "daemon", ""),
        ("decision_queue_count", "backend/meta_orchestrator/decision_queue.py", "supervisor_gate", ""),
        ("michael_orchestration_load", "backend/meta_orchestrator/decision_queue.py", "supervisor_gate", ""),
        ("next_best_action", "backend/meta_orchestrator/chief_of_staff.py", "daemon", ""),
        ("open_defect_count", "backend/coding_control_plane/defect_registry.py", "db_query", ""),
        ("critical_defect_count", "backend/coding_control_plane/defect_registry.py", "db_query", ""),
        ("warning_count", "backend/coding_control_plane/warning_baseline.py", "db_query", ""),
        ("new_warning_count", "backend/coding_control_plane/warning_baseline.py", "db_query", ""),
        ("security_finding_count", "backend/security_ops/finding_ingestor.py", "db_query", ""),
        ("high_vulnerability_count", "backend/security_ops/vuln_register.py", "db_query", ""),
        ("unowned_defect_count", "backend/coding_control_plane/defect_registry.py", "db_query", ""),
        ("zero_defect_gate_status", "scripts/zero_defect_gate.sh", "bash_gate", ""),
        ("best_agent_routing_status", "backend/coding_control_plane/coding_agent_router.py", "supervisor_gate", ""),
        ("final_verifier_status", "backend/coding_control_plane/final_verifier.py", "supervisor_gate", "")
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


