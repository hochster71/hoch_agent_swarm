import os
import sqlite3
import logging
from backend.db.sqlite_pragmas import apply_wal_pragmas

logger = logging.getLogger("BrainDatabase")
DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../swarm_ledger.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    apply_wal_pragmas(conn)
    return conn

def init_brain_tables():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. operator_chat_sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operator_chat_sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                mode TEXT NOT NULL,
                mission_id TEXT,
                summary TEXT
            );
        """)
        
        # 2. operator_messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operator_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        
        # 3. brain_suggestions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS brain_suggestions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                mission_id TEXT,
                suggested_action TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                approval_required INTEGER NOT NULL,
                confidence REAL NOT NULL,
                rationale_summary TEXT,
                created_at TEXT NOT NULL
            );
        """)
        
        # 4. operator_feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operator_feedback (
                id TEXT PRIMARY KEY,
                suggestion_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                correction TEXT,
                created_at TEXT NOT NULL
            );
        """)
        
        # 5. doctrine_rules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctrine_rules (
                id TEXT PRIMARY KEY,
                rule_text TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
        """)

        # 6. artifact_workflows
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifact_workflows (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                requester TEXT NOT NULL,
                classification TEXT NOT NULL,
                workflow_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # 7. delivery_receipts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_receipts (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                folder TEXT NOT NULL,
                filename TEXT NOT NULL,
                receipt_data TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)

        # 8. monetization_audits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monetization_audits (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                write_path_pass INTEGER NOT NULL,
                blocked_actions_pass INTEGER NOT NULL,
                secret_redaction_pass INTEGER NOT NULL,
                evidence_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        
        conn.commit()
        logger.info("Brain SQLite tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize brain SQLite tables: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_brain_tables()
