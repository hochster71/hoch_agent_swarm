import sqlite3
from datetime import datetime, timezone
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

def check_signal_freshness():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    
    try:
        now = datetime.now(timezone.utc)
        rows = conn.execute("SELECT signal_id, last_updated, ttl_seconds FROM runtime_truth_signals").fetchall()
        
        for r in rows:
            signal_id = r["signal_id"]
            last_updated_str = r["last_updated"]
            ttl = r["ttl_seconds"]
            
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
                age = (now - last_updated).total_seconds()
                
                if age > ttl:
                    freshness = "stale"
                elif age > (ttl * 0.7):
                    freshness = "aging"
                else:
                    freshness = "fresh"
                    
                conn.execute(
                    "UPDATE runtime_truth_signals SET freshness = ? WHERE signal_id = ?",
                    (freshness, signal_id)
                )
            except Exception:
                conn.execute(
                    "UPDATE runtime_truth_signals SET freshness = ? WHERE signal_id = ?",
                    ("missing", signal_id)
                )
        conn.commit()
    finally:
        conn.close()
