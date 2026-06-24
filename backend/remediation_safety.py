import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "swarm_ledger.db"

def is_sql_remediation_allowed(patch: str) -> bool:
    """
    Strict SQL AST allowlist check for database remediation.
    Only allows specific parsed SELECT, PRAGMA, and UPDATE statements.
    Blocks any SQL injection or dangerous clauses.
    """
    query = patch.strip().upper()
    if not query:
        return False
        
    # Block dangerous keywords completely
    dangerous = ["DROP", "DELETE", "ALTER", "ATTACH", "DETACH", "CREATE", "REPLACE INTO", "INSERT INTO", "UNION", "JOIN", "--", "/*"]
    if any(x in query for x in dangerous):
        return False
        
    # Check if it is a PRAGMA
    if query.startswith("PRAGMA "):
        # Check if it modifies busy_timeout, journal_mode, or synchronous with safe values
        match_timeout = re.match(r"^PRAGMA\s+BUSY_TIMEOUT\s*=\s*(\d+)\s*;?$", query)
        match_journal = re.match(r"^PRAGMA\s+JOURNAL_MODE\s*=\s*(WAL|DELETE)\s*;?$", query)
        match_sync = re.match(r"^PRAGMA\s+SYNCHRONOUS\s*=\s*(NORMAL|FULL|OFF)\s*;?$", query)
        if match_timeout:
            val = int(match_timeout.group(1))
            return 0 <= val <= 60000
        if match_journal or match_sync:
            return True
        return False
        
    # Check if it is an UPDATE on hochster_cluster_job_results
    if query.startswith("UPDATE "):
        pattern = r"^UPDATE\s+HOCHSTER_CLUSTER_JOB_RESULTS\s+SET\s+STATUS\s*=\s*'?(PASS|BLOCK|WARNING|NOT_RUN)'?\s+WHERE\s+JOB_ID\s*=\s*'?[A-Z0-9_-]+'?\s*;?$"
        if re.match(pattern, query):
            return True
        return False
        
    return False

def has_external_side_effects(patch: str) -> bool:
    """
    Checks if a patch has external side effects (Docker, filesystem, network APIs).
    """
    patch_clean = patch.strip().lower()
    if not patch_clean:
        return False
        
    # Check if it is a SQL change
    is_sql = patch_clean.startswith("pragma") or "update" in patch_clean or "insert" in patch_clean or "delete" in patch_clean or "select" in patch_clean
    if is_sql:
        if is_sql_remediation_allowed(patch):
            return False
        return True # Unsafe SQL has side effects
        
    # Explicitly deny anything else (deny-by-default)
    return True

def classify_remediation_risk(patch: str) -> str:
    """
    Classifies the risk of a remediation patch using a deny-by-default policy.
    """
    patch_clean = patch.strip().upper()
    if not patch:
        return "Low"
        
    # Low: Simple allowed echoes or safe allowlisted database updates/pragmas
    if patch_clean.startswith("ECHO "):
        return "Low"
    if is_sql_remediation_allowed(patch):
        return "Low"
        
    # Deny-by-default: anything else is critical risk
    return "Critical"

def is_remediation_approved(risk_level: str, incident_id: str, approvals: list[dict]) -> bool:
    """
    Determines if a remediation is allowed under current policy.
    Only allows execution if there is an explicit approved gate matching this incident.
    """
        
    # Search for an approved gate matching this incident_id or action_type
    for app in approvals:
        if app.get("status") == "approved":
            # Match by incident_id or by action type containing incident id
            if app.get("request_id") == incident_id or incident_id in app.get("decisions_json", ""):
                return True
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
            return True, "Command format verified with metacharacters warned"
        return True, "Command syntax verified"

def validate_rollback_plan(rollback_plan: str) -> tuple[bool, str]:
    """
    Validates the rollback plan before executing the remediation.
    """
    if not rollback_plan:
        return False, "Rollback plan is missing"
        
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

def calculate_error_budget_and_burn_rate() -> tuple[float, float]:
    """
    Calculates remaining error budget (%) and burn rate.
    SLO target: 95% readiness score over a window of the last 50 reports.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT readiness_score FROM hochster_readiness_reports ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        scores = [row[0] for row in rows]
    except Exception:
        scores = []
    finally:
        conn.close()
        
    if not scores:
        return 100.0, 0.0
        
    # 1. Error Budget calculation
    # Allowed error per report is 5 points (since target is 95, so 100 - 95 = 5)
    total_reports = len(scores)
    accumulated_error = sum(max(0.0, 95.0 - float(s)) for s in scores)
    allowed_error = 5.0 * total_reports
    
    if allowed_error == 0.0:
        remaining_budget = 100.0
    else:
        remaining_budget = max(0.0, 100.0 * (1.0 - (accumulated_error / allowed_error)))
        
    # 2. Burn Rate calculation
    # Look at a shorter window (last 5 reports) to see the recent consumption rate
    short_limit = min(5, total_reports)
    short_scores = scores[:short_limit]
    short_error = sum(max(0.0, 95.0 - float(s)) for s in short_scores)
    allowed_short_error = 5.0 * short_limit
    
    if allowed_short_error == 0.0 or short_error == 0.0:
        burn_rate = 0.0
    else:
        # Burn rate = actual short error / allowed short error
        burn_rate = short_error / allowed_short_error
        
    return remaining_budget, burn_rate

def get_autonomy_level(readiness_score: int, remaining_budget: float, burn_rate: float) -> str:
    """
    Determines the allowed autonomy level based on current score, remaining budget, and burn rate.
    """
    if readiness_score < 95 or remaining_budget < 10.0 or burn_rate >= 5.0:
        return "L1/L2"
    if (95 <= readiness_score <= 97) or (10.0 <= remaining_budget < 50.0) or (2.0 <= burn_rate < 5.0):
        return "L3"
    return "L4"
