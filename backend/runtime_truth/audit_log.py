import sqlite3
import hashlib
import json
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

def append_audit_event(actor: str, action: str, target: str, risk_class: str, approval_id: str = None, before_state: dict = None, after_state: dict = None) -> str:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get previous event hash
        prev_row = conn.execute("SELECT event_hash FROM audit_events ORDER BY timestamp DESC LIMIT 1").fetchone()
        prev_hash = prev_row["event_hash"] if prev_row else "0" * 64
        
        event_id = f"evt-{hashlib.sha256(now_iso().encode()).hexdigest()[:8]}"
        timestamp = now_iso()
        
        before_hash = hashlib.sha256(json.dumps(before_state or {}).encode()).hexdigest()
        after_hash = hashlib.sha256(json.dumps(after_state or {}).encode()).hexdigest()
        
        # Calculate event hash chain
        payload = f"{event_id}|{timestamp}|{actor}|{action}|{target}|{risk_class}|{approval_id}|{before_hash}|{after_hash}|{prev_hash}"
        event_hash = hashlib.sha256(payload.encode()).hexdigest()
        
        conn.execute("""
            INSERT INTO audit_events 
            (event_id, timestamp, actor, action, target, risk_class, approval_id, before_hash, after_hash, previous_event_hash, event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            timestamp,
            actor,
            action,
            target,
            risk_class,
            approval_id,
            before_hash,
            after_hash,
            prev_hash,
            event_hash
        ))
        conn.commit()
        return event_id
    finally:
        conn.close()

def verify_audit_integrity() -> bool:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    
    try:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY timestamp ASC").fetchall()
        prev_hash = "0" * 64
        
        for r in rows:
            event_id = r["event_id"]
            timestamp = r["timestamp"]
            actor = r["actor"]
            action = r["action"]
            target = r["target"]
            risk_class = r["risk_class"]
            approval_id = r["approval_id"]
            b_hash = r["before_hash"]
            a_hash = r["after_hash"]
            p_hash = r["previous_event_hash"]
            e_hash = r["event_hash"]
            
            if p_hash != prev_hash:
                return False
                
            # Recalculate hash
            payload = f"{event_id}|{timestamp}|{actor}|{action}|{target}|{risk_class}|{approval_id}|{b_hash}|{a_hash}|{p_hash}"
            calc_hash = hashlib.sha256(payload.encode()).hexdigest()
            if calc_hash != e_hash:
                return False
                
            prev_hash = e_hash
            
        return True
    finally:
        conn.close()
