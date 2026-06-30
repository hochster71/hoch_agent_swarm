import sqlite3
import os
import yaml
from typing import Dict, Any, List, Tuple
from backend.runtime_truth.state_store import DB_PATH

class ReadinessCapEngine:
    def __init__(self, policy_path: str = "config/readiness_cap_policy.yaml", db_path: str = DB_PATH):
        self.policy_path = policy_path
        self.db_path = db_path
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def calculate_caps(self) -> Dict[str, Any]:
        score = 100.0
        caps = []

        policy_caps = self.policy.get("readiness_cap_policy", {}).get("caps", {})
        critical_gap_cap = policy_caps.get("critical_gap", 80.0)
        missing_ui_cap = policy_caps.get("missing_ui", 75.0)
        not_ready_cap = policy_caps.get("not_ready", 50.0)

        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get signals
                cursor.execute("SELECT signal_id, value FROM runtime_truth_signals")
                signals = {row["signal_id"]: row["value"] for row in cursor.fetchall()}

                # Rule 1: Critical gaps exist
                crit_gaps = int(signals.get("critical_gap_count", 0))
                if crit_gaps > 0:
                    score = min(score, critical_gap_cap)
                    caps.append(("critical gaps exist", critical_gap_cap))

                # Rule 2: Ownerless domains exist
                ownerless = int(signals.get("ownerless_domain_count", 0))
                if ownerless > 0:
                    score = min(score, not_ready_cap)
                    caps.append(("business autonomy is NOT READY", not_ready_cap))

                # Rule 3: Missing UI containers (like view-meta-orchestrator or view-defect-zero)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                index_path = os.path.join(project_root, "frontend/index.html")
                ui_missing = True
                if os.path.exists(index_path):
                    with open(index_path, "r") as f:
                        content = f.read()
                        if "view-meta-orchestrator" in content and "view-defect-zero" in content:
                            ui_missing = False

                if ui_missing:
                    score = min(score, missing_ui_cap)
                    caps.append(("missing UI container", missing_ui_cap))

                from backend.runtime_truth.go_nogo_manager import GoNoGoManager
                try:
                    manager = GoNoGoManager(db_path=self.db_path)
                    summary = manager.process_and_update()
                    contradiction_active = summary["contradiction_status"] == "ACTIVE"
                except Exception:
                    contradiction_active = False

                if contradiction_active:
                    score = min(score, not_ready_cap)
                    caps.append(("GO/NO-GO contradiction active", not_ready_cap))

                # Rule 5: Open defects or vulnerabilities
                open_defects = int(signals.get("open_defect_count", 0))
                if open_defects > 0:
                    score = min(score, critical_gap_cap)
                    caps.append(("open codebase defects remain", critical_gap_cap))

                # Rule 6: Git working tree is dirty
                git_status = signals.get("git_status", "")
                if "modified" in str(git_status).lower() or "dirty" in str(git_status).lower():
                    score = min(score, 90.0)
                    caps.append(("git working tree is dirty", 90.0))

        except Exception as e:
            return {
                "score": 0.0,
                "caps": [f"Error calculating caps: {str(e)}"],
                "min_cap": 0.0
            }

        return {
            "score": score,
            "caps": [c[0] for c in caps],
            "min_cap": min([c[1] for c in caps]) if caps else 100.0
        }
