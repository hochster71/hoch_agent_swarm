import sqlite3
import os
from pathlib import Path
from datetime import datetime, timezone

def get_db_path() -> Path:
    db_env = os.getenv("HOCHSTER_DB_PATH")
    if db_env:
        return Path(db_env)
    if os.path.exists("/app"):
        return Path("/app/backend/swarm_ledger.db")
    return Path(__file__).resolve().parent.parent / "swarm_ledger.db"

def update_promptops_telemetry(contract: dict, score_result: dict, risk_result: dict):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    signals = [
        ("promptops_status", "PromptOps Engine State", "ACTIVE", "promptops", "system", 300),
        ("prompt_score", "Prompt Quality Score", str(score_result.get("score", 0.0)), "promptops", "system", 300),
        ("prompt_fake_completion_risk", "Fake-completion Risk Level", risk_result.get("risk_level", "LOW"), "promptops", "system", 300),
        ("prompt_contract_status", "Prompt Contract Lifecycle State", "BOUND", "promptops", "system", 300),
        ("gate_binding_status", "Bound Telemetry Verification Gates", "VERIFIED", "promptops", "system", 300),
        ("closeout_authority_status", "Closeout Promotion Authority Mode", "GATED", "promptops", "system", 300),
        ("human_loop_reduction_status", "Human Operator Assist Status", "ACTIVE", "promptops", "system", 300),
        ("last_prompt_class", "Last Evaluated Prompt Class", contract.get("prompt_class", "GENERAL_E2E_BUILD"), "promptops", "system", 300),
        ("last_prompt_contract_id", "Last Generated Contract ID", contract.get("mission_id", "N/A"), "promptops", "system", 300)
    ]
    
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        for sig in signals:
            conn.execute("""
                INSERT OR REPLACE INTO runtime_truth_signals
                (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence, evidence_link, git_sha, source_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sig[0], sig[1], sig[2], sig[3], sig[4], timestamp, sig[5], "fresh", 1.0, "", "", ""))
        conn.commit()
    except Exception as e:
        print(f"Error updating PromptOps telemetry: {e}")
    finally:
        conn.close()
