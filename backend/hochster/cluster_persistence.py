import sqlite3
import json
from datetime import datetime
from backend.ledger_manager import DB_FILE, _db_lock
from backend.db.sqlite_pragmas import apply_wal_pragmas

def init_job_results_table():
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        apply_wal_pragmas(conn)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hochster_job_results (
                    job_id TEXT PRIMARY KEY,
                    instance TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    findings TEXT NOT NULL,
                    patches_generated INTEGER NOT NULL,
                    patches_validated INTEGER NOT NULL,
                    evidence_refs TEXT NOT NULL,
                    trace_id TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

def save_job_result(result: dict):
    init_job_results_table()
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        apply_wal_pragmas(conn)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO hochster_job_results (
                    job_id, instance, correlation_id, status, started_at, completed_at,
                    findings, patches_generated, patches_validated, evidence_refs, trace_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result["job_id"],
                result["instance"],
                result["correlation_id"],
                result["status"],
                result["started_at"],
                result["completed_at"],
                json.dumps(result["findings"]),
                result["patches_generated"],
                result["patches_validated"],
                json.dumps(result["evidence_refs"]),
                result["trace_id"]
            ))
            conn.commit()
        finally:
            conn.close()

def get_job_results() -> list:
    init_job_results_table()
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        apply_wal_pragmas(conn)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT job_id, instance, correlation_id, status, started_at, completed_at, findings, patches_generated, patches_validated, evidence_refs, trace_id FROM hochster_job_results")
            rows = cursor.fetchall()
        finally:
            conn.close()
            
    results = []
    for r in rows:
        results.append({
            "job_id": r[0],
            "instance": r[1],
            "correlation_id": r[2],
            "status": r[3],
            "started_at": r[4],
            "completed_at": r[5],
            "findings": json.loads(r[6]),
            "patches_generated": r[7],
            "patches_validated": r[8],
            "evidence_refs": json.loads(r[9]),
            "trace_id": r[10]
        })
    return results
