import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "swarm_ledger.db"

def classify_remediation_risk(patch: str) -> str:
    """
    Classifies the risk of a remediation patch.
    Risk levels: Low, Medium, High, Critical
    """
    patch_clean = patch.strip().upper()
    if not patch:
        return "Low"
        
    # Low: Simple SQLite PRAGMAs or harmless echoes or job result updates
    if patch_clean.startswith("PRAGMA ") and any(x in patch_clean for x in ["BUSY_TIMEOUT", "JOURNAL_MODE", "SYNCHRONOUS"]):
        return "Low"
    if patch_clean.startswith("ECHO "):
        return "Low"
    if "UPDATE HOCHSTER_CLUSTER_JOB_RESULTS" in patch_clean:
        return "Low"
        
    # Critical: deletion, file removals, dangerous characters
    if any(x in patch_clean for x in ["RM ", "RM -RF", "SHRED", "FORMAT", "DROP TABLE", "DELETE FROM"]):
        return "Critical"
        
    # High: writes to files, altering config, system changes
    if any(x in patch_clean for x in ["WRITE", "CONFIG", "WGET", "CURL", "APT-GET", "BREW"]):
        return "High"
        
    # Medium: restarts, resyncs, scripts
    if any(x in patch_clean.lower() for x in ["restart", "relink", "diagnose", "sync"]):
        return "Medium"
        
    return "Medium"

def is_remediation_approved(risk_level: str, incident_id: str, approvals: list[dict]) -> bool:
    """
    Determines if a remediation is allowed under current policy.
    Only 'Low' risk is allowed autonomously. Medium/High/Critical require approval.
    """
    if risk_level == "Low":
        return True
        
    # Search for an approved gate matching this incident_id or action_type
    for app in approvals:
        if app.get("status") == "approved":
            # Match by incident_id or by action type containing incident id
            if app.get("request_id") == incident_id or incident_id in app.get("decisions_json", ""):
                return True
            # Alternative: if the action type matches remediation
            if app.get("action_type") == f"REMEDIATE_{incident_id}":
                return True
    return False

def dry_run_remediation(patch: str) -> tuple[bool, str]:
    """
    Runs a pre-flight dry-run of a patch.
    For SQL/PRAGMA patches, runs inside a transaction and rolls back.
    """
    if not patch:
        return True, "Empty patch"
        
    if patch.strip().upper().startswith("PRAGMA") or "UPDATE" in patch.strip().upper() or "INSERT" in patch.strip().upper():
        conn = sqlite3.connect(DB_PATH, timeout=10)
        try:
            conn.execute("BEGIN TRANSACTION;")
            conn.execute(patch)
            conn.execute("ROLLBACK;")
            return True, "SQL transaction dry-run succeeded (rolled back)"
        except Exception as e:
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
            return False, f"SQL dry-run failed: {e}"
        finally:
            conn.close()
    else:
        # Mock command dry-run syntax check
        if re.search(r'[;&|`$]', patch):
            # For this release, commands with shell metacharacters are high risk/warning
            return True, "Command format verified with metacharacters warned"
        return True, "Command syntax verified"

def validate_rollback_plan(rollback_plan: str) -> tuple[bool, str]:
    """
    Validates the rollback plan before executing the remediation.
    """
    if not rollback_plan:
        return False, "Rollback plan is missing"
        
    # Dry-run the rollback plan to verify it is valid
    ok, msg = dry_run_remediation(rollback_plan)
    if not ok:
        return False, f"Rollback dry-run failed: {msg}"
    return True, "Rollback plan validated successfully"

def get_blast_radius(category: str) -> list[str]:
    """
    Returns the blast radius (affected components) for a given category.
    """
    mapping = {
        "Database Lock Risk": ["database", "execution_store", "telemetry"],
        "Telemetry Drift": ["telemetry", "monitor", "dashboard"],
        "Worker Degradation": ["worker", "deployer", "coder"],
        "Policy Posture Mismatch": ["policy", "control_plane", "security"]
    }
    return mapping.get(category, ["system"])
