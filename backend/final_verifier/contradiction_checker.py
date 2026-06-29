import sqlite3
from typing import Dict, Any, List
from backend.runtime_truth.state_store import DB_PATH

class ContradictionChecker:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def check_contradictions(self, readiness_override: float = None) -> Dict[str, Any]:
        violations = []
        
        # Connect to DB and read signals
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT signal_id, value FROM runtime_truth_signals")
                signals = {row["signal_id"]: row["value"] for row in cursor.fetchall()}
        except Exception as e:
            return {"is_valid": False, "violations": [f"DB access error: {str(e)}"]}

        # Rule 1: GO and NO-GO active contradiction
        go_active = signals.get("production_go_status") == "GO"
        nogo_active = signals.get("production_nogo_status") == "NO-GO"
        if go_active and nogo_active:
            violations.append("GO and NO-GO contradiction: both statuses are active simultaneously.")

        # Rule 2: 100% readiness with critical gaps
        readiness_val = readiness_override if readiness_override is not None else float(signals.get("readiness_score", 0.0))
        critical_gaps = int(signals.get("critical_gap_count", 0))
        if readiness_val >= 100.0 and critical_gaps > 0:
            violations.append(f"Contradiction: Readiness is {readiness_val}% but critical gaps count is {critical_gaps}.")

        # Rule 3: 100% readiness with ownerless domains
        ownerless_domains = int(signals.get("ownerless_domain_count", 0))
        if readiness_val >= 100.0 and ownerless_domains > 0:
            violations.append(f"Contradiction: Readiness is {readiness_val}% but ownerless domains count is {ownerless_domains}.")

        # Rule 4: Revenue ready but buyer signal status is not verified
        revenue_ready = signals.get("revenue_package_status") == "READY"
        buyer_verified = signals.get("buyer_signal_status") == "VERIFIED"
        if revenue_ready and not buyer_verified:
            violations.append("Contradiction: Revenue package marked READY but buyer signal status is NOT VERIFIED.")

        # Rule 5: Zero-defect claim but open defects exist
        zero_defect_status = signals.get("zero_defect_gate_status") == "PASS"
        open_defects = int(signals.get("open_defect_count", 0))
        if zero_defect_status and open_defects > 0:
            violations.append(f"Contradiction: Zero-defect gate passed but open defect count is {open_defects}.")

        return {
            "is_valid": len(violations) == 0,
            "violations": violations
        }
