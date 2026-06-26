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
        # Create discovered_devices table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS discovered_devices (
                node_id TEXT PRIMARY KEY,
                display_name TEXT,
                hostname TEXT,
                ip_address TEXT,
                mac_address TEXT,
                vendor TEXT,
                model TEXT,
                model_identifier TEXT,
                device_class TEXT,
                fleet_group TEXT,
                compute_tier TEXT,
                service_roles_json TEXT,
                service_endpoints_json TEXT,
                trusted_compute INTEGER,
                approval_required INTEGER,
                onboarding_status TEXT,
                network_profile TEXT,
                power_profile TEXT,
                sandbox_level TEXT,
                requires_operator_presence INTEGER,
                last_seen TEXT,
                discovery_sources_json TEXT,
                confidence_score REAL,
                operator_notes TEXT,
                raw_fingerprint_json TEXT
            )
            """
        )
        # Create device_service_registry table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS device_service_registry (
                node_id TEXT PRIMARY KEY,
                approved_at TEXT,
                approved_by_operator TEXT,
                display_name TEXT,
                device_class TEXT,
                fleet_group TEXT,
                compute_tier TEXT,
                service_roles_json TEXT,
                service_endpoints_json TEXT,
                trusted_compute INTEGER,
                onboarding_status TEXT,
                last_seen TEXT,
                health_status TEXT,
                no_auto_install_guarantee INTEGER
            )
            """
        )
        # Create swarm_routing_history table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS swarm_routing_history (
                routing_id TEXT PRIMARY KEY,
                task_type TEXT,
                prompt TEXT,
                required_capabilities_json TEXT,
                selected_node_id TEXT,
                selected_node_name TEXT,
                eligible_nodes_json TEXT,
                routing_decisions_json TEXT,
                created_at TEXT
            )
            """
        )
        # Create service_node_leases table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_node_leases (
                node_id TEXT PRIMARY KEY,
                last_seen TEXT,
                battery_level REAL,
                power_source TEXT,
                network_status TEXT,
                availability TEXT,
                lease_duration_seconds INTEGER
            )
            """
        )
        # Create model_providers table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_providers (
                model_provider_id TEXT PRIMARY KEY,
                node_id TEXT,
                display_name TEXT,
                device_name TEXT,
                device_class TEXT,
                fleet_group TEXT,
                provider_type TEXT,
                endpoint_url TEXT,
                health_url TEXT,
                models_url TEXT,
                api_key_required INTEGER,
                api_key_ref TEXT,
                approved_for_inference INTEGER,
                trusted_for_sensitive_context INTEGER,
                allowed_agent_roles_json TEXT,
                allowed_task_types_json TEXT,
                model_ids_json TEXT,
                default_model TEXT,
                context_window INTEGER,
                supports_streaming INTEGER,
                supports_tools INTEGER,
                supports_vision INTEGER,
                supports_audio INTEGER,
                supports_json_mode INTEGER,
                latency_ms REAL,
                last_health_check_at TEXT,
                health_status TEXT,
                operator_notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        # Create inference_runs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inference_runs (
                inference_run_id TEXT PRIMARY KEY,
                created_at TEXT,
                completed_at TEXT,
                model_provider_id TEXT,
                node_id TEXT,
                agent_id TEXT,
                task_id TEXT,
                model_id TEXT,
                prompt_hash TEXT,
                prompt_preview TEXT,
                response_hash TEXT,
                response_preview TEXT,
                status TEXT,
                latency_ms REAL,
                token_usage_json TEXT,
                error_message TEXT,
                evidence_path TEXT,
                metadata_json TEXT
            )
            """
        )
        # Create multi_model_runs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS multi_model_runs (
                multi_model_run_id TEXT PRIMARY KEY,
                prompt_hash TEXT,
                consensus_agreement_score REAL,
                consensus_response_preview TEXT,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                latency_ms REAL,
                evidence_path TEXT,
                metadata_json TEXT
            )
            """
        )
        # Create agent_model_policies table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_model_policies (
                agent_role TEXT PRIMARY KEY,
                allowed_model_classes TEXT NOT NULL,
                preferred_providers TEXT NOT NULL,
                fallback_providers TEXT NOT NULL,
                require_trusted_for_sensitive INTEGER NOT NULL,
                quorum_size INTEGER NOT NULL,
                dissent_similarity_threshold REAL NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        # Create agent_model_policy_logs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_model_policy_logs (
                log_id TEXT PRIMARY KEY,
                task_id TEXT,
                run_id TEXT,
                agent_role TEXT,
                agent_id TEXT,
                prompt_hash TEXT,
                policy_status TEXT NOT NULL,
                selected_providers TEXT NOT NULL,
                use_multi_model INTEGER NOT NULL,
                trusted_enforced INTEGER NOT NULL,
                reason TEXT,
                logged_at TEXT NOT NULL
            )
            """
        )
        # Create crewai_ingested_artifacts table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crewai_ingested_artifacts (
                id TEXT PRIMARY KEY,
                source_path TEXT UNIQUE NOT NULL,
                hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                run_context_json TEXT NOT NULL,
                ingested_at TEXT NOT NULL
            )
            """
        )
        # Create evidence_graph_links table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_graph_links (
                link_id TEXT PRIMARY KEY,
                source_graph_id TEXT NOT NULL,
                target_graph_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source_graph_id, target_graph_id, relation_type)
            )
            """
        )
        # Create formal_release_authority_tokens table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS formal_release_authority_tokens (
                token_id TEXT PRIMARY KEY,
                candidate_packet_id TEXT NOT NULL,
                operator TEXT NOT NULL,
                scope TEXT NOT NULL,
                token_value TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # Create formal_release_authority_logs table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS formal_release_authority_logs (
                log_id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                candidate_packet_id TEXT NOT NULL,
                operator TEXT NOT NULL,
                token_value TEXT,
                status TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # Create release_evidence_retention table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS release_evidence_retention (
                evidence_id TEXT PRIMARY KEY,
                artifact_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                retention_decision TEXT NOT NULL,
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

def persist_discovered_device(device: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO discovered_devices (
                node_id, display_name, hostname, ip_address, mac_address,
                vendor, model, model_identifier, device_class, fleet_group,
                compute_tier, service_roles_json, service_endpoints_json,
                trusted_compute, approval_required, onboarding_status,
                network_profile, power_profile, sandbox_level,
                requires_operator_presence, last_seen, discovery_sources_json,
                confidence_score, operator_notes, raw_fingerprint_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device["node_id"],
                device.get("display_name"),
                device.get("hostname"),
                device.get("ip_address"),
                device.get("mac_address"),
                device.get("vendor"),
                device.get("model"),
                device.get("model_identifier"),
                device.get("device_class"),
                device.get("fleet_group"),
                device.get("compute_tier"),
                json.dumps(device.get("service_roles") or []),
                json.dumps(device.get("service_endpoints") or []),
                1 if device.get("trusted_compute") else 0,
                1 if device.get("approval_required") else 0,
                device.get("onboarding_status", "discovered"),
                device.get("network_profile"),
                device.get("power_profile"),
                device.get("sandbox_level", "unknown"),
                1 if device.get("requires_operator_presence") else 0,
                device.get("last_seen") or now_iso(),
                json.dumps(device.get("discovery_sources") or []),
                device.get("confidence_score", 1.0),
                device.get("operator_notes"),
                json.dumps(device.get("raw_fingerprint") or {})
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_discovered_devices() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM discovered_devices").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "node_id": d["node_id"],
                "display_name": d["display_name"],
                "hostname": d["hostname"],
                "ip_address": d["ip_address"],
                "mac_address": d["mac_address"],
                "vendor": d["vendor"],
                "model": d["model"],
                "model_identifier": d["model_identifier"],
                "device_class": d["device_class"],
                "fleet_group": d["fleet_group"],
                "compute_tier": d["compute_tier"],
                "service_roles": json.loads(d["service_roles_json"] or "[]"),
                "service_endpoints": json.loads(d["service_endpoints_json"] or "[]"),
                "trusted_compute": bool(d["trusted_compute"]),
                "approval_required": bool(d["approval_required"]),
                "onboarding_status": d["onboarding_status"],
                "network_profile": d["network_profile"],
                "power_profile": d["power_profile"],
                "sandbox_level": d["sandbox_level"],
                "requires_operator_presence": bool(d["requires_operator_presence"]),
                "last_seen": d["last_seen"],
                "discovery_sources": json.loads(d["discovery_sources_json"] or "[]"),
                "confidence_score": d["confidence_score"],
                "operator_notes": d["operator_notes"],
                "raw_fingerprint": json.loads(d["raw_fingerprint_json"] or "{}")
            })
        return result
    finally:
        conn.close()

def get_discovered_device(node_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        r = conn.execute("SELECT * FROM discovered_devices WHERE node_id = ?", (node_id,)).fetchone()
        if r:
            d = dict(r)
            return {
                "node_id": d["node_id"],
                "display_name": d["display_name"],
                "hostname": d["hostname"],
                "ip_address": d["ip_address"],
                "mac_address": d["mac_address"],
                "vendor": d["vendor"],
                "model": d["model"],
                "model_identifier": d["model_identifier"],
                "device_class": d["device_class"],
                "fleet_group": d["fleet_group"],
                "compute_tier": d["compute_tier"],
                "service_roles": json.loads(d["service_roles_json"] or "[]"),
                "service_endpoints": json.loads(d["service_endpoints_json"] or "[]"),
                "trusted_compute": bool(d["trusted_compute"]),
                "approval_required": bool(d["approval_required"]),
                "onboarding_status": d["onboarding_status"],
                "network_profile": d["network_profile"],
                "power_profile": d["power_profile"],
                "sandbox_level": d["sandbox_level"],
                "requires_operator_presence": bool(d["requires_operator_presence"]),
                "last_seen": d["last_seen"],
                "discovery_sources": json.loads(d["discovery_sources_json"] or "[]"),
                "confidence_score": d["confidence_score"],
                "operator_notes": d["operator_notes"],
                "raw_fingerprint": json.loads(d["raw_fingerprint_json"] or "{}")
            }
        return None
    finally:
        conn.close()

def persist_service_node(node: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO device_service_registry (
                node_id, approved_at, approved_by_operator, display_name,
                device_class, fleet_group, compute_tier, service_roles_json,
                service_endpoints_json, trusted_compute, onboarding_status,
                last_seen, health_status, no_auto_install_guarantee
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node["node_id"],
                node.get("approved_at") or now_iso(),
                node.get("approved_by_operator"),
                node.get("display_name"),
                node.get("device_class"),
                node.get("fleet_group"),
                node.get("compute_tier"),
                json.dumps(node.get("service_roles") or []),
                json.dumps(node.get("service_endpoints") or []),
                1 if node.get("trusted_compute") else 0,
                node.get("onboarding_status", "approved"),
                node.get("last_seen") or now_iso(),
                node.get("health_status", "Active"),
                1 if node.get("no_auto_install_guarantee", True) else 0
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_service_nodes() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM device_service_registry").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "node_id": d["node_id"],
                "approved_at": d["approved_at"],
                "approved_by_operator": d["approved_by_operator"],
                "display_name": d["display_name"],
                "device_class": d["device_class"],
                "fleet_group": d["fleet_group"],
                "compute_tier": d["compute_tier"],
                "service_roles": json.loads(d["service_roles_json"] or "[]"),
                "service_endpoints": json.loads(d["service_endpoints_json"] or "[]"),
                "trusted_compute": bool(d["trusted_compute"]),
                "onboarding_status": d["onboarding_status"],
                "last_seen": d["last_seen"],
                "health_status": d["health_status"],
                "no_auto_install_guarantee": bool(d["no_auto_install_guarantee"])
            })
        return result
    finally:
        conn.close()

def get_service_node(node_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        r = conn.execute("SELECT * FROM device_service_registry WHERE node_id = ?", (node_id,)).fetchone()
        if r:
            d = dict(r)
            return {
                "node_id": d["node_id"],
                "approved_at": d["approved_at"],
                "approved_by_operator": d["approved_by_operator"],
                "display_name": d["display_name"],
                "device_class": d["device_class"],
                "fleet_group": d["fleet_group"],
                "compute_tier": d["compute_tier"],
                "service_roles": json.loads(d["service_roles_json"] or "[]"),
                "service_endpoints": json.loads(d["service_endpoints_json"] or "[]"),
                "trusted_compute": bool(d["trusted_compute"]),
                "onboarding_status": d["onboarding_status"],
                "last_seen": d["last_seen"],
                "health_status": d["health_status"],
                "no_auto_install_guarantee": bool(d["no_auto_install_guarantee"])
            }
        return None
    finally:
        conn.close()

def delete_service_node(node_id: str) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute("DELETE FROM device_service_registry WHERE node_id = ?", (node_id,))
        conn.commit()
    finally:
        conn.close()

def persist_routing_decision(
    routing_id: str,
    task_type: str,
    prompt: str,
    required_caps: list[str],
    selected_node_id: str,
    selected_node_name: str,
    eligible_nodes: list[str],
    routing_decisions: dict[str, dict]
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            """
            INSERT OR REPLACE INTO swarm_routing_history (
                routing_id, task_type, prompt, required_capabilities_json,
                selected_node_id, selected_node_name, eligible_nodes_json,
                routing_decisions_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                routing_id,
                task_type,
                prompt,
                json.dumps(required_caps),
                selected_node_id,
                selected_node_name,
                json.dumps(eligible_nodes),
                json.dumps(routing_decisions),
                now_str
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_routing_history(limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            "SELECT * FROM swarm_routing_history ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "routing_id": r["routing_id"],
                "task_type": r["task_type"],
                "prompt": r["prompt"],
                "required_capabilities": json.loads(r["required_capabilities_json"] or "[]"),
                "selected_node_id": r["selected_node_id"],
                "selected_node_name": r["selected_node_name"],
                "eligible_nodes": json.loads(r["eligible_nodes_json"] or "[]"),
                "routing_decisions": json.loads(r["routing_decisions_json"] or "{}"),
                "created_at": r["created_at"]
            })
        return result
    finally:
        conn.close()

def update_service_node_lease(
    node_id: str,
    battery_level: float,
    power_source: str,
    network_status: str,
    availability: str,
    lease_duration_seconds: int
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO service_node_leases (
                node_id, last_seen, battery_level, power_source, network_status, availability, lease_duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (node_id, now_iso(), battery_level, power_source, network_status, availability, lease_duration_seconds)
        )
        health_status = "Active" if availability == "available" else ("Sleeping" if availability == "sleeping" else "Offline")
        conn.execute(
            """
            UPDATE device_service_registry 
            SET last_seen = ?, health_status = ? 
            WHERE node_id = ?
            """,
            (now_iso(), health_status, node_id)
        )
        conn.commit()
    finally:
        conn.close()

def get_service_node_leases() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM service_node_leases").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "node_id": d["node_id"],
                "last_seen": d["last_seen"],
                "battery_level": d["battery_level"],
                "power_source": d["power_source"],
                "network_status": d["network_status"],
                "availability": d["availability"],
                "lease_duration_seconds": d["lease_duration_seconds"]
            })
        return result
    finally:
        conn.close()

def register_model_provider_db(model_provider_id: str, payload: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        now = now_iso()
        conn.execute(
            """
            INSERT OR REPLACE INTO model_providers (
                model_provider_id, node_id, display_name, device_name, device_class, fleet_group,
                provider_type, endpoint_url, health_url, models_url, api_key_required, api_key_ref,
                approved_for_inference, trusted_for_sensitive_context, allowed_agent_roles_json,
                allowed_task_types_json, model_ids_json, default_model, context_window,
                supports_streaming, supports_tools, supports_vision, supports_audio, supports_json_mode,
                latency_ms, last_health_check_at, health_status, operator_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model_provider_id,
                payload.get("node_id"),
                payload.get("display_name"),
                payload.get("device_name"),
                payload.get("device_class"),
                payload.get("fleet_group"),
                payload.get("provider_type"),
                payload.get("endpoint_url"),
                payload.get("health_url"),
                payload.get("models_url"),
                1 if payload.get("api_key_required") else 0,
                payload.get("api_key_ref"),
                1 if payload.get("approved_for_inference") else 0,
                1 if payload.get("trusted_for_sensitive_context") else 0,
                json.dumps(payload.get("allowed_agent_roles", [])),
                json.dumps(payload.get("allowed_task_types", [])),
                json.dumps(payload.get("model_ids", [])),
                payload.get("default_model"),
                payload.get("context_window", 2048),
                1 if payload.get("supports_streaming") else 0,
                1 if payload.get("supports_tools") else 0,
                1 if payload.get("supports_vision") else 0,
                1 if payload.get("supports_audio") else 0,
                1 if payload.get("supports_json_mode") else 0,
                payload.get("latency_ms", 0.0),
                payload.get("last_health_check_at"),
                payload.get("health_status", "unverified"),
                payload.get("operator_notes"),
                payload.get("created_at") or now,
                payload.get("updated_at") or now
            )
        )
        conn.commit()
    finally:
        conn.close()

def update_model_provider_db(model_provider_id: str, payload: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        now = now_iso()
        fields = []
        params = []
        for k, v in payload.items():
            if k in ["allowed_agent_roles", "allowed_task_types", "model_ids"]:
                fields.append(f"{k}_json = ?")
                params.append(json.dumps(v))
            elif k in ["api_key_required", "approved_for_inference", "trusted_for_sensitive_context",
                       "supports_streaming", "supports_tools", "supports_vision", "supports_audio", "supports_json_mode"]:
                fields.append(f"{k} = ?")
                params.append(1 if v else 0)
            elif k not in ["model_provider_id", "created_at"]:
                fields.append(f"{k} = ?")
                params.append(v)
        fields.append("updated_at = ?")
        params.append(now)
        params.append(model_provider_id)
        
        query = f"UPDATE model_providers SET {', '.join(fields)} WHERE model_provider_id = ?"
        conn.execute(query, tuple(params))
        conn.commit()
    finally:
        conn.close()

def get_model_provider_db(model_provider_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM model_providers WHERE model_provider_id = ?", (model_provider_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        return {
            "model_provider_id": d["model_provider_id"],
            "node_id": d["node_id"],
            "display_name": d["display_name"],
            "device_name": d["device_name"],
            "device_class": d["device_class"],
            "fleet_group": d["fleet_group"],
            "provider_type": d["provider_type"],
            "endpoint_url": d["endpoint_url"],
            "health_url": d["health_url"],
            "models_url": d["models_url"],
            "api_key_required": bool(d["api_key_required"]),
            "api_key_ref": d["api_key_ref"],
            "approved_for_inference": bool(d["approved_for_inference"]),
            "trusted_for_sensitive_context": bool(d["trusted_for_sensitive_context"]),
            "allowed_agent_roles": json.loads(d["allowed_agent_roles_json"] or "[]"),
            "allowed_task_types": json.loads(d["allowed_task_types_json"] or "[]"),
            "model_ids": json.loads(d["model_ids_json"] or "[]"),
            "default_model": d["default_model"],
            "context_window": d["context_window"],
            "supports_streaming": bool(d["supports_streaming"]),
            "supports_tools": bool(d["supports_tools"]),
            "supports_vision": bool(d["supports_vision"]),
            "supports_audio": bool(d["supports_audio"]),
            "supports_json_mode": bool(d["supports_json_mode"]),
            "latency_ms": d["latency_ms"],
            "last_health_check_at": d["last_health_check_at"],
            "health_status": d["health_status"],
            "operator_notes": d["operator_notes"],
            "created_at": d["created_at"],
            "updated_at": d["updated_at"]
        }
    finally:
        conn.close()

def list_model_providers_db() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM model_providers").fetchall()
        results = []
        for row in rows:
            d = dict(row)
            results.append({
                "model_provider_id": d["model_provider_id"],
                "node_id": d["node_id"],
                "display_name": d["display_name"],
                "device_name": d["device_name"],
                "device_class": d["device_class"],
                "fleet_group": d["fleet_group"],
                "provider_type": d["provider_type"],
                "endpoint_url": d["endpoint_url"],
                "health_url": d["health_url"],
                "models_url": d["models_url"],
                "api_key_required": bool(d["api_key_required"]),
                "api_key_ref": d["api_key_ref"],
                "approved_for_inference": bool(d["approved_for_inference"]),
                "trusted_for_sensitive_context": bool(d["trusted_for_sensitive_context"]),
                "allowed_agent_roles": json.loads(d["allowed_agent_roles_json"] or "[]"),
                "allowed_task_types": json.loads(d["allowed_task_types_json"] or "[]"),
                "model_ids": json.loads(d["model_ids_json"] or "[]"),
                "default_model": d["default_model"],
                "context_window": d["context_window"],
                "supports_streaming": bool(d["supports_streaming"]),
                "supports_tools": bool(d["supports_tools"]),
                "supports_vision": bool(d["supports_vision"]),
                "supports_audio": bool(d["supports_audio"]),
                "supports_json_mode": bool(d["supports_json_mode"]),
                "latency_ms": d["latency_ms"],
                "last_health_check_at": d["last_health_check_at"],
                "health_status": d["health_status"],
                "operator_notes": d["operator_notes"],
                "created_at": d["created_at"],
                "updated_at": d["updated_at"]
            })
        return results
    finally:
        conn.close()

def delete_model_provider_db(model_provider_id: str) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute("DELETE FROM model_providers WHERE model_provider_id = ?", (model_provider_id,))
        conn.commit()
    finally:
        conn.close()

def persist_inference_run_db(inference_run_id: str, data: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO inference_runs (
                inference_run_id, created_at, completed_at, model_provider_id, node_id, agent_id,
                task_id, model_id, prompt_hash, prompt_preview, response_hash, response_preview,
                status, latency_ms, token_usage_json, error_message, evidence_path, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inference_run_id,
                data.get("created_at"),
                data.get("completed_at"),
                data.get("model_provider_id"),
                data.get("node_id"),
                data.get("agent_id"),
                data.get("task_id"),
                data.get("model_id"),
                data.get("prompt_hash"),
                data.get("prompt_preview"),
                data.get("response_hash"),
                data.get("response_preview"),
                data.get("status"),
                data.get("latency_ms"),
                json.dumps(data.get("token_usage", {})),
                data.get("error_message"),
                data.get("evidence_path"),
                json.dumps(data.get("metadata", {}))
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_inference_runs_db() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM inference_runs ORDER BY created_at DESC").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append({
                "inference_run_id": d["inference_run_id"],
                "created_at": d["created_at"],
                "completed_at": d["completed_at"],
                "model_provider_id": d["model_provider_id"],
                "node_id": d["node_id"],
                "agent_id": d["agent_id"],
                "task_id": d["task_id"],
                "model_id": d["model_id"],
                "prompt_hash": d["prompt_hash"],
                "prompt_preview": d["prompt_preview"],
                "response_hash": d["response_hash"],
                "response_preview": d["response_preview"],
                "status": d["status"],
                "latency_ms": d["latency_ms"],
                "token_usage": json.loads(d["token_usage_json"] or "{}"),
                "error_message": d["error_message"],
                "evidence_path": d["evidence_path"],
                "metadata": json.loads(d["metadata_json"] or "{}")
            })
        return results
    finally:
        conn.close()

def persist_multi_model_run_db(multi_model_run_id: str, data: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO multi_model_runs (
                multi_model_run_id, prompt_hash, consensus_agreement_score,
                consensus_response_preview, status, created_at, completed_at,
                latency_ms, evidence_path, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                multi_model_run_id,
                data.get("prompt_hash"),
                data.get("consensus_agreement_score"),
                data.get("consensus_response_preview"),
                data.get("status"),
                data.get("created_at"),
                data.get("completed_at"),
                data.get("latency_ms"),
                data.get("evidence_path"),
                json.dumps(data.get("metadata", {}))
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_multi_model_runs_db() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM multi_model_runs ORDER BY created_at DESC").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append({
                "multi_model_run_id": d["multi_model_run_id"],
                "prompt_hash": d["prompt_hash"],
                "consensus_agreement_score": d["consensus_agreement_score"],
                "consensus_response_preview": d["consensus_response_preview"],
                "status": d["status"],
                "created_at": d["created_at"],
                "completed_at": d["completed_at"],
                "latency_ms": d["latency_ms"],
                "evidence_path": d["evidence_path"],
                "metadata": json.loads(d["metadata_json"] or "{}")
            })
        return results
    finally:
        conn.close()

def persist_agent_model_policy_db(policy: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO agent_model_policies (
                agent_role, allowed_model_classes, preferred_providers,
                fallback_providers, require_trusted_for_sensitive,
                quorum_size, dissent_similarity_threshold, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                policy["agent_role"],
                json.dumps(policy["allowed_model_classes"]),
                json.dumps(policy["preferred_providers"]),
                json.dumps(policy["fallback_providers"]),
                1 if policy["require_trusted_for_sensitive"] else 0,
                policy["quorum_size"],
                policy["dissent_similarity_threshold"],
                policy.get("updated_at") or now_iso()
            )
        )
        conn.commit()
    finally:
        conn.close()

def get_agent_model_policy_db(agent_role: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM agent_model_policies WHERE agent_role = ?", (agent_role,)).fetchone()
        if not row:
            return None
        d = dict(row)
        return {
            "agent_role": d["agent_role"],
            "allowed_model_classes": json.loads(d["allowed_model_classes"] or "[]"),
            "preferred_providers": json.loads(d["preferred_providers"] or "[]"),
            "fallback_providers": json.loads(d["fallback_providers"] or "[]"),
            "require_trusted_for_sensitive": bool(d["require_trusted_for_sensitive"]),
            "quorum_size": d["quorum_size"],
            "dissent_similarity_threshold": d["dissent_similarity_threshold"],
            "updated_at": d["updated_at"]
        }
    finally:
        conn.close()

def list_agent_model_policies_db() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM agent_model_policies ORDER BY agent_role").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append({
                "agent_role": d["agent_role"],
                "allowed_model_classes": json.loads(d["allowed_model_classes"] or "[]"),
                "preferred_providers": json.loads(d["preferred_providers"] or "[]"),
                "fallback_providers": json.loads(d["fallback_providers"] or "[]"),
                "require_trusted_for_sensitive": bool(d["require_trusted_for_sensitive"]),
                "quorum_size": d["quorum_size"],
                "dissent_similarity_threshold": d["dissent_similarity_threshold"],
                "updated_at": d["updated_at"]
            })
        return results
    finally:
        conn.close()

def log_agent_model_policy_decision_db(log: dict) -> None:
    import uuid
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT INTO agent_model_policy_logs (
                log_id, task_id, run_id, agent_role, agent_id, prompt_hash,
                policy_status, selected_providers, use_multi_model,
                trusted_enforced, reason, logged_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log.get("log_id") or f"POL-{uuid.uuid4().hex[:6].upper()}",
                log.get("task_id"),
                log.get("run_id"),
                log["agent_role"],
                log.get("agent_id"),
                log.get("prompt_hash"),
                log["policy_status"],
                json.dumps(log["selected_providers"]),
                1 if log.get("use_multi_model") else 0,
                1 if log.get("trusted_enforced") else 0,
                log.get("reason"),
                log.get("logged_at") or now_iso()
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_agent_model_policy_logs_db() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM agent_model_policy_logs ORDER BY logged_at DESC").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append({
                "log_id": d["log_id"],
                "task_id": d["task_id"],
                "run_id": d["run_id"],
                "agent_role": d["agent_role"],
                "agent_id": d["agent_id"],
                "prompt_hash": d["prompt_hash"],
                "policy_status": d["policy_status"],
                "selected_providers": json.loads(d["selected_providers"] or "[]"),
                "use_multi_model": bool(d["use_multi_model"]),
                "trusted_enforced": bool(d["trusted_enforced"]),
                "reason": d["reason"],
                "logged_at": d["logged_at"]
            })
        return results
    finally:
        conn.close()

def persist_crewai_ingested_artifact(artifact: dict) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO crewai_ingested_artifacts (
                id, source_path, hash, created_at, artifact_type, run_context_json, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.get("id"),
                artifact.get("source_path"),
                artifact.get("hash"),
                artifact.get("created_at"),
                artifact.get("artifact_type"),
                artifact.get("run_context_json"),
                artifact.get("ingested_at")
            )
        )
        conn.commit()
    finally:
        conn.close()

def list_crewai_ingested_artifacts() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM crewai_ingested_artifacts ORDER BY ingested_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_crewai_ingested_artifact(artifact_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        row = conn.execute("SELECT * FROM crewai_ingested_artifacts WHERE id = ?", (artifact_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def persist_evidence_graph_link(link_id: str, source_graph_id: str, target_graph_id: str, relation_type: str) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO evidence_graph_links (
                link_id, source_graph_id, target_graph_id, relation_type, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (link_id, source_graph_id, target_graph_id, relation_type, now_iso())
        )
        conn.commit()
    finally:
        conn.close()

def get_evidence_graph_links() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM evidence_graph_links ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def delete_evidence_graph_link(link_id: str) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute("DELETE FROM evidence_graph_links WHERE link_id = ?", (link_id,))
        conn.commit()
    finally:
        conn.close()

def persist_authority_token(
    token_id: str,
    candidate_packet_id: str,
    operator: str,
    scope: str,
    token_value: str,
    expires_at: str
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO formal_release_authority_tokens (
                token_id, candidate_packet_id, operator, scope, token_value, expires_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (token_id, candidate_packet_id, operator, scope, token_value, expires_at, now_iso())
        )
        conn.commit()
    finally:
        conn.close()

def get_active_authority_token(candidate_packet_id: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        now = now_iso()
        row = conn.execute(
            """
            SELECT * FROM formal_release_authority_tokens 
            WHERE candidate_packet_id = ? AND expires_at > ?
            ORDER BY expires_at DESC LIMIT 1
            """,
            (candidate_packet_id, now)
        )
        res = row.fetchone()
        return dict(res) if res else None
    finally:
        conn.close()

def persist_authority_log(
    log_id: str,
    action: str,
    candidate_packet_id: str,
    operator: str,
    token_value: str | None,
    status: str,
    details: str | None
) -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            """
            INSERT INTO formal_release_authority_logs (
                log_id, action, candidate_packet_id, operator, token_value, status, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (log_id, action, candidate_packet_id, operator, token_value, status, details, now_iso())
        )
        conn.commit()
    finally:
        conn.close()

def list_authority_logs() -> list[dict]:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    apply_pragmas(conn)
    try:
        rows = conn.execute("SELECT * FROM formal_release_authority_logs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_file_sha256(filepath: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
    except Exception:
        pass
    return h.hexdigest()

def get_path_hash(target_path: Path) -> str:
    import hashlib
    import os
    if target_path.is_file():
        return get_file_sha256(target_path)
    elif target_path.is_dir():
        h = hashlib.sha256()
        files = []
        for root, _, filenames in os.walk(target_path):
            for f in filenames:
                files.append(Path(root) / f)
        files.sort()
        for f in files:
            h.update(str(f.relative_to(target_path)).encode('utf-8'))
            h.update(get_file_sha256(f).encode('utf-8'))
        return h.hexdigest()
    return hashlib.sha256(str(target_path).encode('utf-8')).hexdigest()

def scan_and_index_evidence() -> list[dict]:
    import os
    import hashlib
    
    project_root = Path(__file__).resolve().parent.parent
    
    # Folders and their artifact type mapping
    scan_configs = [
        ("dist/candidates", "candidate", True),
        ("dist/formal-previews", "formal-preview", True),
        ("dist/attestations", "attestation", True),
        ("dist/releases", "release-bundle", False),
        ("artifacts/qa", "qa-artifact", False),
        ("test-results", "temporary-run", False)
    ]
    
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    
    try:
        # Get existing indexed items
        existing = {}
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT evidence_id, source_path, file_hash, retention_decision, created_at FROM release_evidence_retention").fetchall()
        for r in rows:
            existing[r["evidence_id"]] = {
                "evidence_id": r["evidence_id"],
                "source_path": r["source_path"],
                "file_hash": r["file_hash"],
                "retention_decision": r["retention_decision"],
                "created_at": r["created_at"]
            }
            
        new_records = []
        
        for rel_dir, artifact_type, dir_is_single_entry in scan_configs:
            full_dir = project_root / rel_dir
            if not full_dir.exists() or not full_dir.is_dir():
                continue
                
            for item in full_dir.iterdir():
                # For qa-artifact, skip subdirectories to avoid deep playwright-report indexing
                if artifact_type == "qa-artifact" and item.is_dir():
                    continue
                # Skip system files like .DS_Store
                if item.name == ".DS_Store" or item.name.startswith("."):
                    continue
                    
                item_rel = str(item.relative_to(project_root))
                evidence_id = hashlib.sha256(item_rel.encode('utf-8')).hexdigest()
                
                # Check if already exists in DB
                if evidence_id in existing:
                    # Update file hash if changed (e.g. preview summary updated) but keep decision
                    current_hash = get_path_hash(item)
                    if existing[evidence_id]["file_hash"] != current_hash:
                        conn.execute(
                            "UPDATE release_evidence_retention SET file_hash = ? WHERE evidence_id = ?",
                            (current_hash, evidence_id)
                        )
                    continue
                
                # If new, compute hash and created_at
                file_hash = get_path_hash(item)
                mtime = os.path.getmtime(item)
                created_at = datetime.fromtimestamp(mtime, timezone.utc).isoformat()
                
                new_records.append((
                    evidence_id,
                    artifact_type,
                    item_rel,
                    file_hash,
                    "needs-review",
                    created_at
                ))
                
        if new_records:
            conn.executemany(
                """
                INSERT INTO release_evidence_retention (
                    evidence_id, artifact_type, source_path, file_hash, retention_decision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                new_records
            )
            conn.commit()
            
        # Re-fetch everything
        conn.row_factory = sqlite3.Row
        all_rows = conn.execute("SELECT * FROM release_evidence_retention ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in all_rows]
        
    finally:
        conn.close()

def classify_evidence(evidence_id: str, decision: str) -> None:
    if decision not in ("retain", "archive", "ignore", "needs-review"):
        raise ValueError(f"Invalid retention decision: {decision}")
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute(
            "UPDATE release_evidence_retention SET retention_decision = ? WHERE evidence_id = ?",
            (decision, evidence_id)
        )
        conn.commit()
    finally:
        conn.close()





