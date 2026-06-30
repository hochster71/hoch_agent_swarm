import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timezone
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

class GoNoGoManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_sources(self) -> List[Dict[str, Any]]:
        sources = []
        with sqlite3.connect(self.db_path, timeout=60) as conn:
            apply_pragmas(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch all raw signal definitions that indicate GO/NO-GO
            cursor.execute("""
                SELECT signal_id, value, source, source_type, last_updated, freshness, confidence 
                FROM runtime_truth_signals 
                WHERE signal_id IN ('production_go_status', 'production_nogo_status')
            """)
            rows = cursor.fetchall()
            
            for r in rows:
                signal_id = r["signal_id"]
                val = r["value"]
                src = r["source"]
                src_type = r["source_type"]
                last_updated = r["last_updated"]
                freshness = r["freshness"]
                confidence = r["confidence"]
                
                # Check stale conditions
                is_stale = False
                try:
                    lu_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - lu_dt).total_seconds()
                    if age > 300.0:
                        is_stale = True
                except Exception:
                    is_stale = True
                
                # Classification rules
                active = True
                classification = "computed"
                reason = "Valid active system signal."
                
                if src == "test":
                    classification = "test"
                    active = False
                    reason = "Stale test record from staging run."
                elif src == "demo":
                    classification = "demo"
                    active = False
                    reason = "Static demo indicator."
                elif is_stale:
                    classification = "stale_manual"
                    active = False
                    reason = "Manual release override expired (older than 5 mins)."
                
                sources.append({
                    "source_id": f"src-{signal_id}-{src}",
                    "signal_id": signal_id,
                    "value": val,
                    "source_type": src_type,
                    "freshness": "stale" if is_stale else freshness,
                    "confidence": confidence,
                    "file_module_endpoint": f"database:{signal_id}",
                    "active": active,
                    "classification": classification,
                    "reason": reason
                })
        return sources

    def process_and_update(self):
        sources = self.get_sources()
        
        # 1. Count categories
        active_go_count = 0
        active_nogo_count = 0
        stale_go_count = 0
        
        go_sources = []
        nogo_sources = []
        
        for s in sources:
            is_go = s["signal_id"] == "production_go_status" and s["value"] == "GO"
            is_nogo = s["signal_id"] == "production_nogo_status" and s["value"] == "NO-GO"
            
            if s["active"]:
                if is_go:
                    active_go_count += 1
                    go_sources.append(s["source_id"])
                elif is_nogo:
                    active_nogo_count += 1
                    nogo_sources.append(s["source_id"])
            else:
                if is_go:
                    stale_go_count += 1
        
        # 2. Compute contradiction status
        contradiction_active = (active_go_count > 0 and active_nogo_count > 0)
        contradiction_status = "ACTIVE" if contradiction_active else "INACTIVE"
        
        # 3. Compute overall release go status
        if active_go_count > 0 and active_nogo_count == 0:
            release_go_status = "GO"
            release_go_source = ",".join(go_sources)
        else:
            release_go_status = "NO-GO"
            release_go_source = "none" if not nogo_sources else ",".join(nogo_sources)
            
        # Write back to SQLite
        with sqlite3.connect(self.db_path, timeout=60) as conn:
            apply_pragmas(conn)
            cursor = conn.cursor()
            
            # Quarantine/Mark inactive in the DB by changing value/freshness of test/stale rows
            for s in sources:
                if not s["active"] and s["value"] in ("GO", "NO-GO"):
                    cursor.execute("""
                        UPDATE runtime_truth_signals
                        SET value = 'QUARANTINED', freshness = 'stale'
                        WHERE signal_id = ? AND source = ?
                    """, (s["signal_id"], s["value"].lower() if s["classification"] == "test" else "test"))
                    
            # Insert the 6 required telemetry signals
            signals_to_write = [
                ("go_nogo_contradiction_status", "Contradiction Status", contradiction_status, "go_nogo_manager", "system"),
                ("go_signal_source_count", "GO Source Count", str(active_go_count), "go_nogo_manager", "system"),
                ("no_go_signal_source_count", "NO-GO Source Count", str(active_nogo_count), "go_nogo_manager", "system"),
                ("stale_go_signal_count", "Stale GO Signal Count", str(stale_go_count), "go_nogo_manager", "system"),
                ("active_release_go_status", "Active Release GO Status", release_go_status, "go_nogo_manager", "system"),
                ("release_go_source", "Release GO Source", release_go_source, "go_nogo_manager", "system")
            ]
            
            now = now_iso()
            for sig_id, name, val, src, src_type in signals_to_write:
                cursor.execute("""
                    INSERT OR REPLACE INTO runtime_truth_signals
                    (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, 60, 'fresh', 1.0)
                """, (sig_id, name, val, src, src_type, now))
                
            conn.commit()
            
        return {
            "contradiction_status": contradiction_status,
            "active_go_count": active_go_count,
            "active_nogo_count": active_nogo_count,
            "stale_go_count": stale_go_count,
            "release_go_status": release_go_status,
            "release_go_source": release_go_source
        }
