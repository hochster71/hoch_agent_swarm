from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Literal, Optional
import json
import sqlite3
from pathlib import Path

Status = Literal["pass", "block", "warning", "not_run"]
DB_PATH = Path(__file__).resolve().parent / "swarm_ledger.db"

@dataclass
class HochsterClusterJobResult:
    job_id: str
    instance: str
    correlation_id: str
    status: Status
    started_at: str
    completed_at: str
    findings: list[str]
    patches_generated: int
    patches_validated: int
    evidence_refs: list[str]
    trace_id: str

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def init_hochster_cluster_tables() -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hochster_cluster_job_results (
                job_id TEXT PRIMARY KEY,
                instance TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                patches_generated INTEGER NOT NULL,
                patches_validated INTEGER NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

def persist_hochster_cluster_job(result: HochsterClusterJobResult) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_cluster_job_results (
                job_id,
                instance,
                correlation_id,
                status,
                started_at,
                completed_at,
                findings_json,
                patches_generated,
                patches_validated,
                evidence_refs_json,
                trace_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.job_id,
                result.instance,
                result.correlation_id,
                result.status,
                result.started_at,
                result.completed_at,
                json.dumps(result.findings),
                result.patches_generated,
                result.patches_validated,
                json.dumps(result.evidence_refs),
                result.trace_id,
                now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

def list_hochster_cluster_jobs() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        rows = conn.execute(
            """
            SELECT *
            FROM hochster_cluster_job_results
            ORDER BY job_id ASC
            """
        ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["findings"] = json.loads(item.pop("findings_json"))
            item["evidence_refs"] = json.loads(item.pop("evidence_refs_json"))
            output.append(item)
        return output
    finally:
        conn.close()
