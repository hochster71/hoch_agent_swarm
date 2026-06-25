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
                risk_level TEXT,
                blast_radius_json TEXT,
                state TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # 7. Swarm Runs
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS swarm_runs (
                run_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                score INTEGER
            )
            """
        )
        # 8. Swarm Agents
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS swarm_agents (
                agent_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                title TEXT NOT NULL,
                tag TEXT NOT NULL,
                system_role TEXT NOT NULL,
                avatar_variant TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                catchphrase TEXT NOT NULL,
                skills_json TEXT NOT NULL,
                stats_json TEXT NOT NULL,
                tier TEXT NOT NULL
            )
            """
        )
        # 9. Swarm Tasks
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS swarm_tasks (
                task_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                owner_agent_id TEXT NOT NULL,
                dependencies_json TEXT NOT NULL,
                planning_frameworks_json TEXT NOT NULL,
                acceptance_criteria TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                approval_required INTEGER NOT NULL,
                PRIMARY KEY (task_id, run_id)
            )
            """
        )
        # 10. Swarm Artifacts
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS swarm_artifacts (
                artifact_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                hash TEXT NOT NULL,
                task_id TEXT,
                run_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by_agent_id TEXT,
                mime_type TEXT,
                evidence_type TEXT,
                retention_policy TEXT,
                signature_status TEXT
            )
            """
        )
        # 11. Agent Capability Manifests
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_capability_manifests (
                agent_id TEXT PRIMARY KEY,
                allowed_tools TEXT NOT NULL,
                denied_tools TEXT NOT NULL,
                file_scopes TEXT NOT NULL,
                network_scopes TEXT NOT NULL,
                approval_threshold TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                audit_sink TEXT NOT NULL
            )
            """
        )

        # Migrate/add columns if they do not exist
        for col, col_type in [("risk_level", "TEXT"), ("blast_radius_json", "TEXT"), ("state", "TEXT")]:
            try:
                conn.execute(f"ALTER TABLE hochster_incidents ADD COLUMN {col} {col_type}")
            except Exception:
                pass
        # Migrate/add columns for swarm_artifacts
        for col, col_type in [
            ("created_by_agent_id", "TEXT"),
            ("mime_type", "TEXT"),
            ("evidence_type", "TEXT"),
            ("retention_policy", "TEXT"),
            ("signature_status", "TEXT")
        ]:
            try:
                conn.execute(f"ALTER TABLE swarm_artifacts ADD COLUMN {col} {col_type}")
            except Exception:
                pass

        # Create candidate_release_packets table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_release_packets (
                candidate_packet_id TEXT PRIMARY KEY,
                candidate_version TEXT NOT NULL,
                candidate_channel TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by_operator TEXT NOT NULL,
                reason TEXT NOT NULL,
                head_sha TEXT NOT NULL,
                branch TEXT NOT NULL,
                working_tree_clean INTEGER NOT NULL,
                qa_status TEXT NOT NULL,
                signing_policy_status TEXT NOT NULL,
                release_channel_policy_status TEXT NOT NULL,
                tag_status TEXT NOT NULL,
                formal_release_blockers_json TEXT NOT NULL,
                packet_status TEXT NOT NULL,
                packet_path TEXT NOT NULL,
                packet_manifest_path TEXT NOT NULL,
                included_artifacts_json TEXT NOT NULL,
                missing_artifacts_json TEXT NOT NULL,
                operator_decision_id TEXT,
                formal_release_ready INTEGER NOT NULL
            )
            """
        )
        # Create formal_release_previews table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS formal_release_previews (
                formal_preview_id TEXT PRIMARY KEY,
                candidate_packet_id TEXT NOT NULL,
                candidate_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                head_sha TEXT NOT NULL,
                branch TEXT NOT NULL,
                release_tag TEXT NOT NULL,
                tag_sha TEXT NOT NULL,
                tag_points_at_head INTEGER NOT NULL,
                tag_status TEXT NOT NULL,
                signing_policy_status TEXT NOT NULL,
                release_channel_policy_status TEXT NOT NULL,
                working_tree_clean INTEGER NOT NULL,
                qa_status TEXT NOT NULL,
                readiness_status TEXT NOT NULL,
                operator_approval_status TEXT NOT NULL,
                formal_release_ready INTEGER NOT NULL,
                formal_release_blockers_json TEXT NOT NULL,
                required_operator_actions_json TEXT NOT NULL,
                preview_manifest_path TEXT NOT NULL,
                preview_status TEXT NOT NULL
            )
            """
        )
        # Create formal_release_seal_dry_runs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS formal_release_seal_dry_runs (
                seal_dry_run_id TEXT PRIMARY KEY,
                formal_preview_id TEXT NOT NULL,
                candidate_packet_id TEXT NOT NULL,
                candidate_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                operator TEXT NOT NULL,
                head_sha TEXT NOT NULL,
                branch TEXT NOT NULL,
                release_tag TEXT NOT NULL,
                seal_status TEXT NOT NULL,
                formal_release_blockers_json TEXT NOT NULL,
                seal_manifest_path TEXT NOT NULL,
                seal_report_path TEXT NOT NULL
            )
            """
        )
        # Create release_seal_attestation_bundles table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS release_seal_attestation_bundles (
                attestation_bundle_id TEXT PRIMARY KEY,
                seal_dry_run_id TEXT,
                formal_preview_id TEXT,
                candidate_packet_id TEXT,
                created_at TEXT,
                created_by_operator TEXT,
                reason TEXT,
                head_sha TEXT,
                branch TEXT,
                release_tag TEXT,
                tag_status TEXT,
                signing_policy_status TEXT,
                release_channel_policy_status TEXT,
                seal_status TEXT,
                attestation_status TEXT,
                bundle_path TEXT,
                bundle_manifest_path TEXT,
                bundle_summary_path TEXT,
                included_artifacts_json TEXT,
                missing_artifacts_json TEXT,
                artifact_checksums_json TEXT,
                formal_release_ready INTEGER,
                no_mutation_guarantee INTEGER
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
    status: str,
    risk_level: str = "Low",
    blast_radius: list[str] = None,
    state: str = "detected"
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO hochster_incidents (
                incident_id, category, severity, findings_json, remediation_patch, rollback_plan, status, risk_level, blast_radius_json, state, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                category,
                severity,
                json.dumps(findings),
                remediation_patch,
                rollback_plan,
                status,
                risk_level,
                json.dumps(blast_radius or []),
                state,
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
            d["blast_radius"] = json.loads(d.pop("blast_radius_json")) if d.get("blast_radius_json") else []
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

def update_incident_state(incident_id: str, state: str) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            "UPDATE hochster_incidents SET state = ? WHERE incident_id = ?",
            (state, incident_id)
        )
        conn.commit()
    finally:
        conn.close()

def persist_swarm_run(run_id: str, name: str, status: str, score: Optional[int] = None, completed_at: Optional[str] = None) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO swarm_runs (run_id, name, status, created_at, completed_at, score)
            VALUES (?, ?, ?, COALESCE((SELECT created_at FROM swarm_runs WHERE run_id = ?), ?), ?, ?)
            """,
            (run_id, name, status, run_id, now_iso(), completed_at, score)
        )
        conn.commit()
    finally:
        conn.close()

def list_swarm_runs() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM swarm_runs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def persist_swarm_agent(agent: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO swarm_agents (
                agent_id, display_name, title, tag, system_role, avatar_variant, status, description, catchphrase, skills_json, stats_json, tier
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                agent["id"],
                agent["displayName"],
                agent["title"],
                agent["tag"],
                agent["systemRole"],
                agent["avatarVariant"],
                agent["status"],
                agent["description"],
                agent["catchphrase"],
                json.dumps(agent["skills"]),
                json.dumps(agent["stats"]),
                agent["tier"]
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_swarm_agents() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM swarm_agents").fetchall()
        output = []
        for r in rows:
            d = dict(r)
            # Fetch capability manifest if it exists
            cap_row = conn.execute("SELECT * FROM agent_capability_manifests WHERE agent_id = ?", (d["agent_id"],)).fetchone()
            capability = None
            if cap_row:
                cd = dict(cap_row)
                capability = {
                    "agent_id": cd["agent_id"],
                    "allowed_tools": json.loads(cd["allowed_tools"]),
                    "denied_tools": json.loads(cd["denied_tools"]),
                    "file_scopes": json.loads(cd["file_scopes"]),
                    "network_scopes": json.loads(cd["network_scopes"]),
                    "approval_threshold": cd["approval_threshold"],
                    "risk_class": cd["risk_class"],
                    "audit_sink": cd["audit_sink"]
                }
            agent_dict = {
                "id": d["agent_id"],
                "displayName": d["display_name"],
                "title": d["title"],
                "tag": d["tag"],
                "systemRole": d["system_role"],
                "avatarVariant": d["avatar_variant"],
                "status": d["status"],
                "description": d["description"],
                "catchphrase": d["catchphrase"],
                "skills": json.loads(d["skills_json"]),
                "stats": json.loads(d["stats_json"]),
                "tier": d["tier"],
                "capability": capability
            }
            output.append(agent_dict)
        return output
    finally:
        conn.close()

def persist_swarm_task(task: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO swarm_tasks (
                task_id, run_id, title, description, status, priority, owner_agent_id, dependencies_json, planning_frameworks_json, acceptance_criteria, risk_level, approval_required
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task["id"],
                task["run_id"],
                task["title"],
                task["description"],
                task["status"],
                task["priority"],
                task["ownerAgentId"],
                json.dumps(task["dependencies"]),
                json.dumps(task["planningFrameworks"]),
                task["acceptanceCriteria"],
                task["riskLevel"],
                1 if task["approvalRequired"] else 0
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_swarm_tasks(run_id: Optional[str] = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        if run_id:
            rows = conn.execute("SELECT * FROM swarm_tasks WHERE run_id = ?", (run_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM swarm_tasks").fetchall()
        output = []
        for r in rows:
            d = dict(r)
            task_dict = {
                "id": d["task_id"],
                "run_id": d["run_id"],
                "title": d["title"],
                "description": d["description"],
                "status": d["status"],
                "priority": d["priority"],
                "ownerAgentId": d["owner_agent_id"],
                "dependencies": json.loads(d["dependencies_json"]),
                "planningFrameworks": json.loads(d["planning_frameworks_json"]),
                "acceptanceCriteria": d["acceptance_criteria"],
                "riskLevel": d["risk_level"],
                "approvalRequired": bool(d["approval_required"])
            }
            output.append(task_dict)
        return output
    finally:
        conn.close()

def persist_swarm_artifact(artifact: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO swarm_artifacts (
                artifact_id, name, path, hash, task_id, run_id, status, created_at,
                created_by_agent_id, mime_type, evidence_type, retention_policy, signature_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact["id"],
                artifact["name"],
                artifact["path"],
                artifact["hash"],
                artifact.get("task_id"),
                artifact.get("run_id"),
                artifact["status"],
                artifact.get("created_at", now_iso()),
                artifact.get("created_by_agent_id"),
                artifact.get("mime_type"),
                artifact.get("evidence_type"),
                artifact.get("retention_policy"),
                artifact.get("signature_status")
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_swarm_artifacts(run_id: Optional[str] = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        if run_id:
            rows = conn.execute("SELECT * FROM swarm_artifacts WHERE run_id = ?", (run_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM swarm_artifacts").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def persist_agent_capability_manifest(manifest: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO agent_capability_manifests (
                agent_id, allowed_tools, denied_tools, file_scopes, network_scopes, approval_threshold, risk_class, audit_sink
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                manifest["agent_id"],
                json.dumps(manifest["allowed_tools"]),
                json.dumps(manifest["denied_tools"]),
                json.dumps(manifest["file_scopes"]),
                json.dumps(manifest["network_scopes"]),
                manifest["approval_threshold"],
                manifest["risk_class"],
                manifest["audit_sink"]
            )
        )
        conn.commit()
    finally:
        conn.close()

def get_agent_capability_manifest(agent_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM agent_capability_manifests WHERE agent_id = ?", (agent_id,)).fetchone()
        if row:
            d = dict(row)
            return {
                "agent_id": d["agent_id"],
                "allowed_tools": json.loads(d["allowed_tools"]),
                "denied_tools": json.loads(d["denied_tools"]),
                "file_scopes": json.loads(d["file_scopes"]),
                "network_scopes": json.loads(d["network_scopes"]),
                "approval_threshold": d["approval_threshold"],
                "risk_class": d["risk_class"],
                "audit_sink": d["audit_sink"]
            }
        return None
    finally:
        conn.close()

def persist_candidate_release_packet(packet: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO candidate_release_packets (
                candidate_packet_id, candidate_version, candidate_channel, created_at,
                created_by_operator, reason, head_sha, branch, working_tree_clean,
                qa_status, signing_policy_status, release_channel_policy_status, tag_status,
                formal_release_blockers_json, packet_status, packet_path, packet_manifest_path,
                included_artifacts_json, missing_artifacts_json, operator_decision_id, formal_release_ready
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                packet["candidate_packet_id"],
                packet["candidate_version"],
                packet["candidate_channel"],
                packet["created_at"],
                packet["created_by_operator"],
                packet["reason"],
                packet["head_sha"],
                packet["branch"],
                1 if packet["working_tree_clean"] else 0,
                packet["qa_status"],
                packet["signing_policy_status"],
                packet["release_channel_policy_status"],
                packet["tag_status"],
                json.dumps(packet["formal_release_blockers"]),
                packet["packet_status"],
                packet["packet_path"],
                packet["packet_manifest_path"],
                json.dumps(packet["included_artifacts"]),
                json.dumps(packet["missing_artifacts"]),
                packet.get("operator_decision_id"),
                1 if packet["formal_release_ready"] else 0
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_candidate_release_packets() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM candidate_release_packets ORDER BY created_at DESC").fetchall()
        packets = []
        for r in rows:
            d = dict(r)
            packets.append({
                "candidate_packet_id": d["candidate_packet_id"],
                "candidate_version": d["candidate_version"],
                "candidate_channel": d["candidate_channel"],
                "created_at": d["created_at"],
                "created_by_operator": d["created_by_operator"],
                "reason": d["reason"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "working_tree_clean": bool(d["working_tree_clean"]),
                "qa_status": d["qa_status"],
                "signing_policy_status": d["signing_policy_status"],
                "release_channel_policy_status": d["release_channel_policy_status"],
                "tag_status": d["tag_status"],
                "formal_release_blockers": json.loads(d["formal_release_blockers_json"]),
                "packet_status": d["packet_status"],
                "packet_path": d["packet_path"],
                "packet_manifest_path": d["packet_manifest_path"],
                "included_artifacts": json.loads(d["included_artifacts_json"]),
                "missing_artifacts": json.loads(d["missing_artifacts_json"]),
                "operator_decision_id": d["operator_decision_id"],
                "formal_release_ready": bool(d["formal_release_ready"])
            })
        return packets
    finally:
        conn.close()

def get_candidate_release_packet(packet_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM candidate_release_packets WHERE candidate_packet_id = ?", (packet_id,)).fetchone()
        if row:
            d = dict(row)
            return {
                "candidate_packet_id": d["candidate_packet_id"],
                "candidate_version": d["candidate_version"],
                "candidate_channel": d["candidate_channel"],
                "created_at": d["created_at"],
                "created_by_operator": d["created_by_operator"],
                "reason": d["reason"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "working_tree_clean": bool(d["working_tree_clean"]),
                "qa_status": d["qa_status"],
                "signing_policy_status": d["signing_policy_status"],
                "release_channel_policy_status": d["release_channel_policy_status"],
                "tag_status": d["tag_status"],
                "formal_release_blockers": json.loads(d["formal_release_blockers_json"]),
                "packet_status": d["packet_status"],
                "packet_path": d["packet_path"],
                "packet_manifest_path": d["packet_manifest_path"],
                "included_artifacts": json.loads(d["included_artifacts_json"]),
                "missing_artifacts": json.loads(d["missing_artifacts_json"]),
                "operator_decision_id": d["operator_decision_id"],
                "formal_release_ready": bool(d["formal_release_ready"])
            }
        return None
    finally:
        conn.close()

def persist_formal_release_preview(preview: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO formal_release_previews (
                formal_preview_id, candidate_packet_id, candidate_version, created_at,
                head_sha, branch, release_tag, tag_sha, tag_points_at_head, tag_status,
                signing_policy_status, release_channel_policy_status, working_tree_clean,
                qa_status, readiness_status, operator_approval_status, formal_release_ready,
                formal_release_blockers_json, required_operator_actions_json, preview_manifest_path,
                preview_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preview["formal_preview_id"],
                preview["candidate_packet_id"],
                preview["candidate_version"],
                preview["created_at"],
                preview["head_sha"],
                preview["branch"],
                preview["release_tag"],
                preview["tag_sha"],
                1 if preview["tag_points_at_head"] else 0,
                preview["tag_status"],
                preview["signing_policy_status"],
                preview["release_channel_policy_status"],
                1 if preview["working_tree_clean"] else 0,
                preview["qa_status"],
                preview["readiness_status"],
                preview["operator_approval_status"],
                1 if preview["formal_release_ready"] else 0,
                json.dumps(preview["formal_release_blockers"]),
                json.dumps(preview["required_operator_actions"]),
                preview["preview_manifest_path"],
                preview["preview_status"]
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_formal_release_previews() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM formal_release_previews ORDER BY created_at DESC").fetchall()
        previews = []
        for r in rows:
            d = dict(r)
            previews.append({
                "formal_preview_id": d["formal_preview_id"],
                "candidate_packet_id": d["candidate_packet_id"],
                "candidate_version": d["candidate_version"],
                "created_at": d["created_at"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "release_tag": d["release_tag"],
                "tag_sha": d["tag_sha"],
                "tag_points_at_head": bool(d["tag_points_at_head"]),
                "tag_status": d["tag_status"],
                "signing_policy_status": d["signing_policy_status"],
                "release_channel_policy_status": d["release_channel_policy_status"],
                "working_tree_clean": bool(d["working_tree_clean"]),
                "qa_status": d["qa_status"],
                "readiness_status": d["readiness_status"],
                "operator_approval_status": d["operator_approval_status"],
                "formal_release_ready": bool(d["formal_release_ready"]),
                "formal_release_blockers": json.loads(d["formal_release_blockers_json"]),
                "required_operator_actions": json.loads(d["required_operator_actions_json"]),
                "preview_manifest_path": d["preview_manifest_path"],
                "preview_status": d["preview_status"]
            })
        return previews
    finally:
        conn.close()

def get_formal_release_preview(preview_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM formal_release_previews WHERE formal_preview_id = ?", (preview_id,)).fetchone()
        if row:
            d = dict(row)
            return {
                "formal_preview_id": d["formal_preview_id"],
                "candidate_packet_id": d["candidate_packet_id"],
                "candidate_version": d["candidate_version"],
                "created_at": d["created_at"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "release_tag": d["release_tag"],
                "tag_sha": d["tag_sha"],
                "tag_points_at_head": bool(d["tag_points_at_head"]),
                "tag_status": d["tag_status"],
                "signing_policy_status": d["signing_policy_status"],
                "release_channel_policy_status": d["release_channel_policy_status"],
                "working_tree_clean": bool(d["working_tree_clean"]),
                "qa_status": d["qa_status"],
                "readiness_status": d["readiness_status"],
                "operator_approval_status": d["operator_approval_status"],
                "formal_release_ready": bool(d["formal_release_ready"]),
                "formal_release_blockers": json.loads(d["formal_release_blockers_json"]),
                "required_operator_actions": json.loads(d["required_operator_actions_json"]),
                "preview_manifest_path": d["preview_manifest_path"],
                "preview_status": d["preview_status"]
            }
        return None
    finally:
        conn.close()

def persist_seal_dry_run(dry_run: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO formal_release_seal_dry_runs (
                    seal_dry_run_id, formal_preview_id, candidate_packet_id, candidate_version,
                    created_at, operator, head_sha, branch, release_tag, seal_status,
                    formal_release_blockers_json, seal_manifest_path, seal_report_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dry_run["seal_dry_run_id"],
                    dry_run["formal_preview_id"],
                    dry_run["candidate_packet_id"],
                    dry_run["candidate_version"],
                    dry_run["created_at"],
                    dry_run["operator"],
                    dry_run["head_sha"],
                    dry_run["branch"],
                    dry_run["release_tag"],
                    dry_run["seal_status"],
                    json.dumps(dry_run["formal_release_blockers"]),
                    dry_run["seal_manifest_path"],
                    dry_run["seal_report_path"]
                )
            )
    finally:
        conn.close()

def list_seal_dry_runs() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM formal_release_seal_dry_runs ORDER BY created_at DESC").fetchall()
        runs = []
        for row in rows:
            d = dict(row)
            runs.append({
                "seal_dry_run_id": d["seal_dry_run_id"],
                "formal_preview_id": d["formal_preview_id"],
                "candidate_packet_id": d["candidate_packet_id"],
                "candidate_version": d["candidate_version"],
                "created_at": d["created_at"],
                "operator": d["operator"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "release_tag": d["release_tag"],
                "seal_status": d["seal_status"],
                "formal_release_blockers": json.loads(d["formal_release_blockers_json"]),
                "seal_manifest_path": d["seal_manifest_path"],
                "seal_report_path": d["seal_report_path"]
            })
        return runs
    finally:
        conn.close()

def get_seal_dry_run(dry_run_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM formal_release_seal_dry_runs WHERE seal_dry_run_id = ?", (dry_run_id,)).fetchone()
        if row:
            d = dict(row)
            return {
                "seal_dry_run_id": d["seal_dry_run_id"],
                "formal_preview_id": d["formal_preview_id"],
                "candidate_packet_id": d["candidate_packet_id"],
                "candidate_version": d["candidate_version"],
                "created_at": d["created_at"],
                "operator": d["operator"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "release_tag": d["release_tag"],
                "seal_status": d["seal_status"],
                "formal_release_blockers": json.loads(d["formal_release_blockers_json"]),
                "seal_manifest_path": d["seal_manifest_path"],
                "seal_report_path": d["seal_report_path"]
            }
        return None
    finally:
        conn.close()

def persist_attestation_bundle(bundle: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO release_seal_attestation_bundles (
                    attestation_bundle_id, seal_dry_run_id, formal_preview_id, candidate_packet_id,
                    created_at, created_by_operator, reason, head_sha, branch, release_tag,
                    tag_status, signing_policy_status, release_channel_policy_status, seal_status,
                    attestation_status, bundle_path, bundle_manifest_path, bundle_summary_path,
                    included_artifacts_json, missing_artifacts_json, artifact_checksums_json,
                    formal_release_ready, no_mutation_guarantee
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bundle["attestation_bundle_id"],
                    bundle["seal_dry_run_id"],
                    bundle["formal_preview_id"],
                    bundle["candidate_packet_id"],
                    bundle["created_at"],
                    bundle["created_by_operator"],
                    bundle["reason"],
                    bundle["head_sha"],
                    bundle["branch"],
                    bundle["release_tag"],
                    bundle["tag_status"],
                    bundle["signing_policy_status"],
                    bundle["release_channel_policy_status"],
                    bundle["seal_status"],
                    bundle["attestation_status"],
                    bundle["bundle_path"],
                    bundle["bundle_manifest_path"],
                    bundle["bundle_summary_path"],
                    json.dumps(bundle["included_artifacts"]),
                    json.dumps(bundle["missing_artifacts"]),
                    json.dumps(bundle["artifact_checksums"]),
                    1 if bundle["formal_release_ready"] else 0,
                    1 if bundle["no_mutation_guarantee"] else 0
                )
            )
    finally:
        conn.close()

def list_attestation_bundles() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM release_seal_attestation_bundles ORDER BY created_at DESC").fetchall()
        bundles = []
        for row in rows:
            d = dict(row)
            bundles.append({
                "attestation_bundle_id": d["attestation_bundle_id"],
                "seal_dry_run_id": d["seal_dry_run_id"],
                "formal_preview_id": d["formal_preview_id"],
                "candidate_packet_id": d["candidate_packet_id"],
                "created_at": d["created_at"],
                "created_by_operator": d["created_by_operator"],
                "reason": d["reason"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "release_tag": d["release_tag"],
                "tag_status": d["tag_status"],
                "signing_policy_status": d["signing_policy_status"],
                "release_channel_policy_status": d["release_channel_policy_status"],
                "seal_status": d["seal_status"],
                "attestation_status": d["attestation_status"],
                "bundle_path": d["bundle_path"],
                "bundle_manifest_path": d["bundle_manifest_path"],
                "bundle_summary_path": d["bundle_summary_path"],
                "included_artifacts": json.loads(d["included_artifacts_json"] or "[]"),
                "missing_artifacts": json.loads(d["missing_artifacts_json"] or "[]"),
                "artifact_checksums": json.loads(d["artifact_checksums_json"] or "{}"),
                "formal_release_ready": bool(d["formal_release_ready"]),
                "no_mutation_guarantee": bool(d["no_mutation_guarantee"])
            })
        return bundles
    finally:
        conn.close()

def get_attestation_bundle(bundle_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM release_seal_attestation_bundles WHERE attestation_bundle_id = ?", (bundle_id,)).fetchone()
        if row:
            d = dict(row)
            return {
                "attestation_bundle_id": d["attestation_bundle_id"],
                "seal_dry_run_id": d["seal_dry_run_id"],
                "formal_preview_id": d["formal_preview_id"],
                "candidate_packet_id": d["candidate_packet_id"],
                "created_at": d["created_at"],
                "created_by_operator": d["created_by_operator"],
                "reason": d["reason"],
                "head_sha": d["head_sha"],
                "branch": d["branch"],
                "release_tag": d["release_tag"],
                "tag_status": d["tag_status"],
                "signing_policy_status": d["signing_policy_status"],
                "release_channel_policy_status": d["release_channel_policy_status"],
                "seal_status": d["seal_status"],
                "attestation_status": d["attestation_status"],
                "bundle_path": d["bundle_path"],
                "bundle_manifest_path": d["bundle_manifest_path"],
                "bundle_summary_path": d["bundle_summary_path"],
                "included_artifacts": json.loads(d["included_artifacts_json"] or "[]"),
                "missing_artifacts": json.loads(d["missing_artifacts_json"] or "[]"),
                "artifact_checksums": json.loads(d["artifact_checksums_json"] or "{}"),
                "formal_release_ready": bool(d["formal_release_ready"]),
                "no_mutation_guarantee": bool(d["no_mutation_guarantee"])
            }
        return None
    finally:
        conn.close()



