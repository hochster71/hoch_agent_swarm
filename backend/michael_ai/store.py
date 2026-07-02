import sqlite3
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas, now_iso

def get_db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    return conn

def init_michael_ai_tables():
    conn = get_db_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS michael_prompts (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                normalized_text TEXT,
                detected_lane TEXT,
                urgency TEXT,
                sentiment TEXT,
                goal TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS michael_decisions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT,
                accepted_state TEXT,
                rejected_state TEXT,
                related_prompt_id TEXT,
                evidence_ref TEXT,
                commit_hash TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS michael_workflows (
                id TEXT PRIMARY KEY,
                lane TEXT NOT NULL,
                status TEXT NOT NULL,
                current_goal TEXT,
                blockers TEXT,
                next_action TEXT,
                evidence_refs TEXT,
                commit_refs TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS michael_lessons (
                id TEXT PRIMARY KEY,
                lesson_type TEXT NOT NULL,
                lesson TEXT NOT NULL,
                trigger_text TEXT,
                do_next_time TEXT,
                avoid_next_time TEXT,
                confidence REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS michael_training_examples (
                id TEXT PRIMARY KEY,
                input_text TEXT NOT NULL,
                desired_output TEXT NOT NULL,
                lane TEXT,
                quality_score REAL NOT NULL,
                source_refs TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

# Initialize tables
init_michael_ai_tables()
