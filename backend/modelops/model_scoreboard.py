import sqlite3
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

def get_scoreboard() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM model_eval_runs").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
