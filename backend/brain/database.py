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
        
        conn.commit()
        logger.info("Brain SQLite tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize brain SQLite tables: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_brain_tables()
