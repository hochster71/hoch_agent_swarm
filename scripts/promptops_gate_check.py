import os
import json
import sqlite3
import sys
from pathlib import Path

def get_db_path() -> Path:
    db_env = os.getenv("HOCHSTER_DB_PATH")
    if db_env:
        return Path(db_env)
    if os.path.exists("/app"):
        return Path("/app/backend/swarm_ledger.db")
    return Path(__file__).resolve().parent.parent / "backend/swarm_ledger.db"

def run_gate() -> bool:
    history_path = "/app/frontend/data/prompt_history.json"
    if not os.path.exists(history_path):
        history_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/data/prompt_history.json"))
        
    if not os.path.exists(history_path):
        print("[FAIL] Prompt history store is missing.")
        return False
        
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        print(f"[FAIL] Failed to load prompt history: {e}")
        return False
        
    if not history:
        print("[WARN] No prompt evaluations recorded yet. Skipping threshold check.")
        return True
        
    latest = history[-1]
    score = latest.get("score", 0.0)
    risk = latest.get("risk_level", "LOW")
    
    print(f"Latest Prompt Class: {latest.get('prompt_class')}")
    print(f"Quality Score: {score}/100")
    print(f"Fake-completion Risk: {risk}")
    
    if score < 60:
        print("[FAIL] Prompt quality score is below minimum threshold (60).")
        return False
        
    if risk == "HIGH":
        print("[FAIL] Fake-completion risk is HIGH without matching control gates.")
        return False
        
    # Check SQLite telemetry signals
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"[FAIL] Ledger database missing at {db_path}")
        return False
        
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM runtime_truth_signals WHERE signal_id LIKE 'promptops%' OR signal_id LIKE 'prompt_%'").fetchall()
        signals = {r["signal_id"]: r["value"] for r in rows}
        
        required = ["promptops_status", "prompt_score", "prompt_fake_completion_risk", "prompt_contract_status"]
        for req in required:
            if req not in signals:
                print(f"[FAIL] Missing required PromptOps signal: {req}")
                return False
                
        print(f"[PASS] PromptOps Runtime Truth verified in database (Status: {signals['promptops_status']})")
    except Exception as e:
        print(f"[FAIL] SQLite read error: {e}")
        return False
    finally:
        conn.close()
        
    return True

if __name__ == "__main__":
    if not run_gate():
        sys.exit(1)
    print("[SUCCESS] PromptOps Closure Control Plane Gate PASSED.")
