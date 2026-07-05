import sqlite3
import json
import uuid
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

def detect_contradictions() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    
    contradictions = []
    
    try:
        # Clear old contradictions first
        conn.execute("DELETE FROM runtime_contradictions")
        conn.commit()

        # Fetch signals
        signals = {r["signal_id"]: r for r in conn.execute("SELECT * FROM runtime_truth_signals").fetchall()}
        heartbeats = {r["component"]: r for r in conn.execute("SELECT * FROM runtime_heartbeats").fetchall()}
        
        # 1. Check if no heartbeat but signal claims live/running
        if "backend_core" in heartbeats:
            hb = heartbeats["backend_core"]
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            cleaned_str = hb["last_seen"].replace("Z", "+00:00")
            hb_time = datetime.fromisoformat(cleaned_str)
            hb_age = (now - hb_time).total_seconds()
            
            # Determine threshold based on ttl_ms (fallback to 120.0s)
            ttl_ms = 120000
            try:
                if "ttl_ms" in hb.keys() and hb["ttl_ms"] is not None:
                    ttl_ms = int(hb["ttl_ms"])
            except Exception:
                pass
            threshold = max(ttl_ms / 1000.0, 120.0)
            
            # If heartbeat is dead but signal says it's healthy
            if hb_age > threshold:
                contradictions.append({
                    "id": f"contradiction-{uuid.uuid4().hex[:8]}",
                    "claims": json.dumps({
                        "heartbeat": "NOT RUNNING",
                        "status_signal": "RUNNING"
                    }),
                    "severity": "CRITICAL",
                    "detected_at": now_iso()
                })
        
        # 2. Check if git tree has modified files but readiness score is 100%
        git_sig = signals.get("git_status")
        if git_sig and "modified" in str(git_sig["value"]).lower():
            # If git tree is dirty but readiness score claims 100%
            readiness_sig = signals.get("readiness_score")
            if readiness_sig and float(readiness_sig["value"]) == 100.0:
                contradictions.append({
                    "id": f"contradiction-{uuid.uuid4().hex[:8]}",
                    "claims": json.dumps({
                        "git_status": "DIRTY",
                        "readiness_score": "100%"
                    }),
                    "severity": "HIGH",
                    "detected_at": now_iso()
                })

        # Save contradictions to table
        if contradictions:
            for c in contradictions:
                conn.execute("""
                    INSERT OR REPLACE INTO runtime_contradictions (id, claims, severity, detected_at)
                    VALUES (?, ?, ?, ?)
                """, (c["id"], c["claims"], c["severity"], c["detected_at"]))
            conn.commit()
            
        # Retrieve all contradictions
        rows = conn.execute("SELECT * FROM runtime_contradictions").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
