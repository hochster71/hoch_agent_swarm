# buyer_signal_tracker.py
import sqlite3
import time
from pathlib import Path
from backend.hochster_cluster import DB_PATH

class BuyerSignalTracker:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS buyer_signals (
                    signal_id TEXT PRIMARY KEY,
                    signal_type TEXT NOT NULL,
                    target_offer_id TEXT NOT NULL,
                    buyer_ip TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
            
            # Populate baseline mock buyer signals for display
            rows = conn.execute("SELECT COUNT(*) as cnt FROM buyer_signals").fetchone()
            if rows and rows[0] == 0:
                conn.execute(
                    """
                    INSERT INTO buyer_signals (signal_id, signal_type, target_offer_id, buyer_ip, details, created_at)
                    VALUES 
                    ('SIG-001', 'CLICK', 'OFFER-001', '192.168.1.144', 'Clicked AI Cyber Artifact Factory pricing link', '2026-06-29T12:05:00Z'),
                    ('SIG-002', 'CLICK', 'OFFER-002', '10.0.0.98', 'Downloaded Secure Agent Swarm setup documentation', '2026-06-29T12:12:00Z'),
                    ('SIG-003', 'DEMO_REQUEST', 'OFFER-001', '192.168.1.155', 'Submitted pilot interest form for RMF evidence automation', '2026-06-29T12:22:00Z')
                    """
                )
                conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    def get_signals(self) -> list[dict]:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM buyer_signals ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []
        finally:
            conn.close()
            
    def record_signal(self, signal_type: str, offer_id: str, buyer_ip: str, details: str) -> None:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            conn.execute(
                "INSERT INTO buyer_signals (signal_id, signal_type, target_offer_id, buyer_ip, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"SIG-{int(time.time())}", signal_type, offer_id, buyer_ip, details, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
