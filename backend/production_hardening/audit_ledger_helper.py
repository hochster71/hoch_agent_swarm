# Append-Only Audit Ledger Helper
import sqlite3
import json
import uuid
from typing import Any, Dict

class AuditLedgerHelper:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.initialize_schema()

    def initialize_schema(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_uuid TEXT UNIQUE,
                actor TEXT,
                action TEXT,
                payload_hash TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    def record_event(self, actor: str, action: str, payload: Dict[str, Any]) -> str:
        event_uuid = str(uuid.uuid4())
        payload_hash = hash(json.dumps(payload, sort_keys=True))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_ledger (event_uuid, actor, action, payload_hash, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (event_uuid, actor, action, str(payload_hash), json.dumps(payload)))
        conn.commit()
        conn.close()
        return event_uuid
