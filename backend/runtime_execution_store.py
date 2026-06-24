from __future__ import annotations
import json
import sqlite3
import re
from datetime import datetime, timezone
from pathlib import Path
from backend.hochster_cluster import DB_PATH

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def apply_pragmas(conn: sqlite3.Connection):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA synchronous=NORMAL;")

def init_execution_store_tables() -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        # 1. Tool calls
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hochster_tool_calls (
                id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                request_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL,
                output_summary TEXT NOT NULL,
                has_evidence INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        # 2. Redaction records
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hochster_redaction_records (
                id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                original_length INTEGER NOT NULL,
                redacted_length INTEGER NOT NULL,
                redactions_count INTEGER NOT NULL,
                redacted_keys TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # 3. Approval gates
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hochster_approval_gates (
                approval_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                decisions_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # 4. Validation evidence
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hochster_validation_evidence (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                tests_run INTEGER NOT NULL,
                tests_passed INTEGER NOT NULL,
                tests_failed INTEGER NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # 5. Readiness reports
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hochster_readiness_reports (
                report_id TEXT PRIMARY KEY,
                readiness_score INTEGER NOT NULL,
                breakdown_json TEXT NOT NULL,
                status TEXT NOT NULL,
                drift_detected INTEGER NOT NULL,
                drift_findings_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # 6. Incidents
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hochster_incidents (
                incident_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                findings_json TEXT NOT NULL,
                remediation_patch TEXT NOT NULL,
                rollback_plan TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

def persist_tool_call(
    id: str,
    trace_id: str,
    correlation_id: str,
    request_id: str,
    job_id: str,
    tool_name: str,
    arguments: str,
    output_summary: str,
    has_evidence: bool = True
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_tool_calls (
                id, trace_id, correlation_id, request_id, job_id, tool_name, arguments, output_summary, has_evidence, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id, trace_id, correlation_id, request_id, job_id, tool_name, arguments, output_summary, 1 if has_evidence else 0, now_iso())
        )
        conn.commit()
    finally:
        conn.close()

def persist_redaction_record(
    id: str,
    trace_id: str,
    original_length: int,
    redacted_length: int,
    redactions_count: int,
    redacted_keys: list[str]
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_redaction_records (
                id, trace_id, original_length, redacted_length, redactions_count, redacted_keys, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (id, trace_id, original_length, redacted_length, redactions_count, json.dumps(redacted_keys), now_iso())
        )
        conn.commit()
    finally:
        conn.close()

def persist_approval_gate(
    approval_id: str,
    request_id: str,
    correlation_id: str,
    trace_id: str,
    action_type: str,
    risk_level: str,
    status: str,
    requested_by: str,
    decisions: list[dict]
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_approval_gates (
                approval_id, request_id, correlation_id, trace_id, action_type, risk_level, status, requested_by, decisions_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (approval_id, request_id, correlation_id, trace_id, action_type, risk_level, status, requested_by, json.dumps(decisions), now_iso())
        )
        conn.commit()
    finally:
        conn.close()

def persist_validation_evidence(
    id: str,
    request_id: str,
    correlation_id: str,
    trace_id: str,
    tests_run: int,
    tests_passed: int,
    tests_failed: int,
    evidence_refs: list[str]
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_validation_evidence (
                id, request_id, correlation_id, trace_id, tests_run, tests_passed, tests_failed, evidence_refs_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id, request_id, correlation_id, trace_id, tests_run, tests_passed, tests_failed, json.dumps(evidence_refs), now_iso())
        )
        conn.commit()
    finally:
        conn.close()

def list_tool_calls() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM hochster_tool_calls ORDER BY created_at ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def list_redaction_records() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM hochster_redaction_records ORDER BY created_at ASC").fetchall()
        output = []
        for r in rows:
            d = dict(r)
            d["redacted_keys"] = json.loads(d["redacted_keys"])
            output.append(d)
        return output
    finally:
        conn.close()

def list_approval_gates() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM hochster_approval_gates ORDER BY created_at ASC").fetchall()
        output = []
        for r in rows:
            d = dict(r)
            d["decisions"] = json.loads(d.pop("decisions_json"))
            output.append(d)
        return output
    finally:
        conn.close()

def list_validation_evidence() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM hochster_validation_evidence ORDER BY created_at ASC").fetchall()
        output = []
        for r in rows:
            d = dict(r)
            d["evidence_refs"] = json.loads(d.pop("evidence_refs_json"))
            output.append(d)
        return output
    finally:
        conn.close()

def redact_secrets(text: str) -> tuple[str, int, list[str]]:
    """
    Redacts credentials and sensitive attributes in standard outputs/errors.
    Matches attributes like API_KEY, Password, Token, Secret.
    Returns (redacted_text, redaction_count, redacted_keys).
    """
    pattern = r'(?i)(api_key|password|secret|token|private_key|auth_token|jwt|credential)([\s:=\'"]+)([^\s\'",;%&]+)'
    redacted = text
    count = 0
    keys_found = []
    
    def replace_match(m):
        nonlocal count
        key = m.group(1)
        sep = m.group(2)
        val = m.group(3)
        # Redact value if it's not a generic placeholder
        if len(val) > 4 and val.lower() not in ("none", "null", "undefined", "[redacted]"):
            count += 1
            if key.lower() not in keys_found:
                keys_found.append(key.lower())
            return f"{key}{sep}[REDACTED]"
        return m.group(0)
        
    redacted = re.sub(pattern, replace_match, text)
    return redacted, count, keys_found

def persist_readiness_report(
    report_id: str,
    readiness_score: int,
    breakdown: dict,
    status: str,
    drift_detected: bool,
    drift_findings: list[str]
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_readiness_reports (
                report_id, readiness_score, breakdown_json, status, drift_detected, drift_findings_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                readiness_score,
                json.dumps(breakdown),
                status,
                1 if drift_detected else 0,
                json.dumps(drift_findings),
                now_iso()
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_readiness_reports(limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute(
            "SELECT * FROM hochster_readiness_reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        output = []
        for r in rows:
            d = dict(r)
            d["breakdown"] = json.loads(d.pop("breakdown_json"))
            d["drift_findings"] = json.loads(d.pop("drift_findings_json"))
            d["drift_detected"] = bool(d["drift_detected"])
            output.append(d)
        return output
    finally:
        conn.close()

def persist_incident(
    incident_id: str,
    category: str,
    severity: str,
    findings: list[str],
    remediation_patch: str,
    rollback_plan: str,
    status: str
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_incidents (
                incident_id, category, severity, findings_json, remediation_patch, rollback_plan, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                category,
                severity,
                json.dumps(findings),
                remediation_patch,
                rollback_plan,
                status,
                now_iso()
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_incidents() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM hochster_incidents ORDER BY created_at DESC").fetchall()
        output = []
        for r in rows:
            d = dict(r)
            d["findings"] = json.loads(d.pop("findings_json"))
            output.append(d)
        return output
    finally:
        conn.close()

def update_incident_status(incident_id: str, status: str) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            "UPDATE hochster_incidents SET status = ? WHERE incident_id = ?",
            (status, incident_id)
        )
        conn.commit()
    finally:
        conn.close()

