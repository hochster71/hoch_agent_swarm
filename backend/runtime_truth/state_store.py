import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

import os
DB_ENV_PATH = os.getenv("HOCHSTER_DB_PATH")
if DB_ENV_PATH:
    DB_PATH = Path(DB_ENV_PATH)
else:
    if os.path.exists("/app"):
        DB_PATH = Path("/app/backend/swarm_ledger.db")
    else:
        DB_PATH = Path(__file__).resolve().parent.parent / "swarm_ledger.db"

def apply_pragmas(conn):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA synchronous=NORMAL;")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def resolve_root_dir(root_dir=None) -> str:
    from backend.runtime_paths import project_root
    if root_dir is not None and os.path.exists(root_dir):
        return os.path.abspath(root_dir)
    return str(project_root())

def init_runtime_truth_tables():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        # Create all 22 required autonomy and truth tables
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runtime_truth_signals (
                signal_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                value TEXT,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                ttl_seconds INTEGER NOT NULL,
                freshness TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_link TEXT,
                evidence_ref TEXT,
                git_sha TEXT,
                source_hash TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runtime_truth_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                state_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runtime_heartbeats (
                component TEXT PRIMARY KEY,
                last_seen TEXT NOT NULL,
                status TEXT NOT NULL,
                ttl_ms INTEGER DEFAULT 10000
            )
        """)
        try:
            conn.execute("ALTER TABLE runtime_heartbeats ADD COLUMN ttl_ms INTEGER DEFAULT 10000")
        except Exception:
            pass
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runtime_contradictions (
                id TEXT PRIMARY KEY,
                claims TEXT NOT NULL,
                severity TEXT NOT NULL,
                detected_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                approval_id TEXT,
                before_hash TEXT,
                after_hash TEXT,
                previous_event_hash TEXT,
                event_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence_index (
                evidence_id TEXT PRIMARY KEY,
                artifact_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claim_verifications (
                claim_id TEXT PRIMARY KEY,
                claim_text TEXT NOT NULL,
                verified INTEGER NOT NULL,
                evidence_ref TEXT,
                verified_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readiness_scores (
                metric_name TEXT PRIMARY KEY,
                score REAL NOT NULL,
                cap_applied REAL,
                reason TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS source_map (
                key TEXT PRIMARY KEY,
                source_url TEXT NOT NULL,
                source_type TEXT NOT NULL,
                checksum TEXT,
                last_checked TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS approval_events (
                approval_id TEXT PRIMARY KEY,
                requested_action TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                approver TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                scope TEXT NOT NULL,
                expiration TEXT NOT NULL,
                decision TEXT NOT NULL,
                evidence_link TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS service_health (
                service_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                latency_ms REAL,
                last_checked TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS supervisor_events (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uptime_windows (
                window_start TEXT PRIMARY KEY,
                window_end TEXT,
                status TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                owner_agent TEXT,
                start_time TEXT NOT NULL,
                affected_component TEXT,
                root_cause TEXT,
                remediation TEXT,
                evidence_ref TEXT,
                closed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mission_cycles (
                cycle_id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                trace_id TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qa_runs (
                run_id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                exit_code INTEGER,
                output TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                agent_role TEXT NOT NULL,
                task_description TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                started_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS model_eval_runs (
                eval_id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                task TEXT NOT NULL,
                metric_score REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_capabilities (
                device_id TEXT,
                capability TEXT,
                available INTEGER NOT NULL,
                source TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                read_only INTEGER NOT NULL,
                requires_approval INTEGER NOT NULL,
                last_verified TEXT NOT NULL,
                PRIMARY KEY (device_id, capability)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS homeops_events (
                event_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                action TEXT NOT NULL,
                risk_class TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS revenue_experiments (
                experiment_id TEXT PRIMARY KEY,
                offer_name TEXT NOT NULL,
                price REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS buyer_signals (
                signal_id TEXT PRIMARY KEY,
                buyer_identifier TEXT NOT NULL,
                action_type TEXT NOT NULL,
                offer_name TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runtime_worker_mesh (
                node_name TEXT PRIMARY KEY,
                host TEXT NOT NULL,
                ollama_base_url TEXT NOT NULL,
                status TEXT NOT NULL,
                routing_enabled INTEGER NOT NULL DEFAULT 0,
                approval_required INTEGER NOT NULL DEFAULT 1,
                models_observed TEXT,
                last_seen TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_plaid_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                institution_name TEXT NOT NULL,
                plaid_item_id TEXT UNIQUE NOT NULL,
                encrypted_access_token TEXT NOT NULL,
                products_enabled TEXT,
                consent_status TEXT NOT NULL,
                last_successful_sync_at TEXT,
                last_error_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plaid_account_id TEXT UNIQUE NOT NULL,
                item_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                official_name TEXT,
                type TEXT NOT NULL,
                subtype TEXT,
                mask_last4 TEXT,
                current_balance REAL NOT NULL,
                available_balance REAL,
                iso_currency_code TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (item_id) REFERENCES finance_plaid_items(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plaid_transaction_id TEXT UNIQUE NOT NULL,
                account_id TEXT NOT NULL,
                date TEXT NOT NULL,
                authorized_date TEXT,
                merchant_name TEXT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                iso_currency_code TEXT,
                category_primary TEXT,
                category_detailed TEXT,
                household_category TEXT,
                pending INTEGER NOT NULL DEFAULT 0,
                confidence REAL,
                needs_review INTEGER NOT NULL DEFAULT 0,
                raw_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES finance_accounts(plaid_account_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_liabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT UNIQUE NOT NULL,
                liability_type TEXT NOT NULL,
                balance REAL NOT NULL,
                apr REAL NOT NULL,
                minimum_payment REAL NOT NULL,
                next_payment_due_date TEXT,
                raw_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES finance_accounts(plaid_account_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plaid_statement_id TEXT UNIQUE NOT NULL,
                account_id TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                posted_date TEXT,
                sha256_hash TEXT,
                storage_path TEXT,
                downloaded_at TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES finance_accounts(plaid_account_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT,
                decision TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                evidence_json TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_transaction_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL,
                target_budget REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                current REAL NOT NULL,
                available REAL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES finance_accounts(plaid_account_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_budget_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_name TEXT UNIQUE NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_budget_actuals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                target REAL NOT NULL,
                actual REAL NOT NULL,
                variance REAL NOT NULL,
                FOREIGN KEY (period_id) REFERENCES finance_budget_periods(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_debt_plan_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT NOT NULL,
                monthly_surplus REAL NOT NULL,
                avalanche_order_json TEXT,
                snowball_order_json TEXT,
                hybrid_order_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_agent_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                finding_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence_json TEXT,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

# Initialize right away
init_runtime_truth_tables()
