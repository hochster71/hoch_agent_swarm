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
        if git_row and any(x in str(git_row["value"]).lower() for x in ["modified", "dirty"]):
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
            
        # 6. Check Meta-Orchestrator signals
        crit_gap_row = conn.execute("SELECT * FROM runtime_truth_signals WHERE signal_id = 'critical_gap_count'").fetchone()
        crit_gap_count = 0
        if crit_gap_row:
            try:
                crit_gap_count = int(crit_gap_row["value"])
            except Exception:
                crit_gap_count = 0
            
        if crit_gap_count > 0:
            score = min(score, 80.0)
            caps.append(("critical gaps exist", 80.0))
            
        # Check UI container presence
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        index_path = os.path.join(project_root, "frontend/index.html")
        ui_missing = True
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                if "view-meta-orchestrator" in f.read():
                    ui_missing = False
                    
        if ui_missing:
            score = min(score, 75.0)
            caps.append(("missing view-meta-orchestrator UI container", 75.0))
            
        ownerless_row = conn.execute("SELECT * FROM runtime_truth_signals WHERE signal_id = 'ownerless_domain_count'").fetchone()
        ownerless_count = 0
        if ownerless_row:
            try:
                ownerless_count = int(ownerless_row["value"])
            except Exception:
                ownerless_count = 0
                
        if ownerless_count > 0:
            caps.append(("business autonomy is NOT READY", 0.0))

        # Query Final Verdict to get final aligned capped score
        try:
            from backend.final_verifier.final_verdict import FinalVerdict
            verdict = FinalVerdict().get_final_verdict()
            score = verdict["readiness_score"]
            caps = [(c, score) for c in verdict["readiness_caps"]]
        except Exception:
            pass
            
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
