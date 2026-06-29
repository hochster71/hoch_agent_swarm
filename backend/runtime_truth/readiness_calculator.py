import sqlite3
import json
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

def calculate_governed_readiness() -> dict:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    
    score = 100.0
    caps = []
    
    try:
        # 1. Fetch all contradictions
        contradictions = conn.execute("SELECT * FROM runtime_contradictions").fetchall()
        if contradictions:
            score = min(score, 65.0)
            caps.append(("contradiction present", 65.0))
            
        # 2. Fetch git status
        git_row = conn.execute("SELECT * FROM runtime_truth_signals WHERE signal_id = 'git_status'").fetchone()
        if git_row and "modified" in str(git_row["value"]).lower():
            score = min(score, 90.0)
            caps.append(("git working tree is dirty", 90.0))
            
        # 3. Check heartbeats
        hb = conn.execute("SELECT * FROM runtime_heartbeats WHERE component = 'backend_core'").fetchone()
        if not hb or hb["status"] != "RUNNING":
            score = min(score, 80.0)
            caps.append(("no live heartbeat", 80.0))
            
        # 4. Check QA evidence
        qa = conn.execute("SELECT * FROM qa_runs ORDER BY timestamp DESC LIMIT 1").fetchone()
        if not qa or qa["exit_code"] != 0:
            score = min(score, 60.0)
            caps.append(("no passing QA evidence", 60.0))

        # 5. Check buyer signals for monetization
        buyer_sig = conn.execute("SELECT * FROM buyer_signals LIMIT 1").fetchone()
        if not buyer_sig:
            score = min(score, 60.0)
            caps.append(("no buyer signals / monetization outreach", 60.0))
            
        # Save score in SQLite
        conn.execute("""
            INSERT OR REPLACE INTO readiness_scores (metric_name, score, cap_applied, reason, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "overall_readiness",
            score,
            caps[0][1] if caps else None,
            caps[0][0] if caps else "All checks passing",
            now_iso()
        ))
        conn.commit()
        
        return {
            "score": score,
            "caps": [c[0] for c in caps],
            "min_cap": caps[0][1] if caps else 100.0
        }
    finally:
        conn.close()
