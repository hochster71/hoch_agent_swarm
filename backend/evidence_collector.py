import os
import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

EVIDENCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../artifacts/evidence/missions"))

class EvidenceCollector:
    def __init__(self, evidence_dir: str = EVIDENCE_DIR):
        self.evidence_dir = evidence_dir
        os.makedirs(self.evidence_dir, exist_ok=True)

    def create_mission_package(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new mission evidence package.
        """
        mission_id = f"mis-{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()
        
        task_description = payload.get("task_description", "")
        route_plan = payload.get("route_plan", {})
        approval_id = payload.get("approval_id")
        approval_status = payload.get("approval_status", "NOT_REQUIRED")
        
        mission_type = route_plan.get("mission_type", "UNKNOWN")
        risk_level = route_plan.get("risk_level", "LOW")
        selected_prompt_ids = route_plan.get("selected_prompt_ids", [])
        selected_prompt_titles = route_plan.get("selected_prompt_titles", [])
        human_approval_required = route_plan.get("human_approval_required", False)
        blocked_actions = route_plan.get("blocked_actions", [])
        fail_closed_triggers = route_plan.get("fail_closed_triggers", [])
        
        facts_observed = payload.get("facts_observed", [])
        assumptions = payload.get("assumptions", [])
        risks = payload.get("risks", [])
        validation_tests = payload.get("validation_tests", [])
        evidence_artifacts = payload.get("evidence_artifacts", [])
        open_questions = payload.get("open_questions", [])

        # Governance logic
        governance_wrapper_required = True
        
        # Enforce execution_allowed remains false in Phase 5
        execution_allowed = False
        
        # Determine initial release decision
        release_decision = "GO"
        
        # Invariant checks:
        # 1. FAIL_CLOSED risk level maps to FAIL_CLOSED and release decision FAIL_CLOSED
        if risk_level == "FAIL_CLOSED" or approval_status == "FAIL_CLOSED" or "FAIL_CLOSED" in fail_closed_triggers:
            risk_level = "FAIL_CLOSED"
            approval_status = "FAIL_CLOSED"
            release_decision = "FAIL_CLOSED"
        
        # 2. Missing selected prompts must produce FAIL_CLOSED
        elif not selected_prompt_ids or len(selected_prompt_ids) == 0:
            risk_level = "FAIL_CLOSED"
            approval_status = "FAIL_CLOSED"
            release_decision = "FAIL_CLOSED"
            fail_closed_triggers.append("missing_selected_prompts")
            blocked_actions.append("TASK_EXECUTION_BLOCKED")

        # 3. No mission may claim GO without validation_tests and evidence_artifacts
        elif not validation_tests or not evidence_artifacts:
            release_decision = "NO_GO"

        # 4. Missing approval for approval-required mission must produce CONDITIONAL_GO or NO_GO, never GO
        elif human_approval_required and approval_status != "APPROVED":
            release_decision = "CONDITIONAL_GO" if approval_status == "PENDING" else "NO_GO"

        mission_folder = os.path.join(self.evidence_dir, mission_id)
        os.makedirs(mission_folder, exist_ok=True)

        # Build final package structure
        evidence_package = {
            "mission_id": mission_id,
            "created_at": created_at,
            "source": "prompt_control_plane",
            "task_description": task_description,
            "mission_type": mission_type,
            "risk_level": risk_level,
            "selected_prompt_ids": selected_prompt_ids,
            "selected_prompt_titles": selected_prompt_titles,
            "governance_wrapper_required": governance_wrapper_required,
            "human_approval_required": human_approval_required,
            "approval_id": approval_id,
            "approval_status": approval_status,
            "execution_allowed": execution_allowed,
            "blocked_actions": blocked_actions,
            "fail_closed_triggers": fail_closed_triggers,
            "facts_observed": facts_observed,
            "assumptions": assumptions,
            "risks": risks,
            "validation_tests": validation_tests,
            "evidence_artifacts": evidence_artifacts,
            "open_questions": open_questions,
            "release_decision": release_decision,
            "integrity": {
                "sha256": "",
                "manifest_path": os.path.join(mission_folder, "evidence_manifest.json")
            }
        }

        # Write auxiliary files
        # selected_prompts.json
        with open(os.path.join(mission_folder, "selected_prompts.json"), "w") as f:
            json.dump({"selected_prompt_ids": selected_prompt_ids, "selected_prompt_titles": selected_prompt_titles}, f, indent=2)

        # assumptions.md
        with open(os.path.join(mission_folder, "assumptions.md"), "w") as f:
            f.write(f"# Mission Assumptions for {mission_id}\n\n")
            for asm in assumptions:
                f.write(f"- {asm}\n")

        # risks.md
        with open(os.path.join(mission_folder, "risks.md"), "w") as f:
            f.write(f"# Mission Risks for {mission_id}\n\n")
            for rsk in risks:
                f.write(f"- {rsk}\n")

        # validation.md
        with open(os.path.join(mission_folder, "validation.md"), "w") as f:
            f.write(f"# Validation Tests for {mission_id}\n\n")
            for tst in validation_tests:
                f.write(f"- {tst}\n")

        # Calculate checksum and write mission.json
        raw_payload = json.dumps(evidence_package, sort_keys=True)
        h = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        evidence_package["integrity"]["sha256"] = h

        with open(os.path.join(mission_folder, "mission.json"), "w") as f:
            json.dump(evidence_package, f, indent=2)

        # Write evidence_manifest.json
        manifest = {
            "mission_id": mission_id,
            "created_at": created_at,
            "files": [
                {"path": "mission.json", "sha256": h},
                {"path": "selected_prompts.json", "sha256": self._file_hash(os.path.join(mission_folder, "selected_prompts.json"))},
                {"path": "assumptions.md", "sha256": self._file_hash(os.path.join(mission_folder, "assumptions.md"))},
                {"path": "risks.md", "sha256": self._file_hash(os.path.join(mission_folder, "risks.md"))},
                {"path": "validation.md", "sha256": self._file_hash(os.path.join(mission_folder, "validation.md"))}
            ]
        }
        with open(os.path.join(mission_folder, "evidence_manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)

        return evidence_package

    def _file_hash(self, filepath: str) -> str:
        with open(filepath, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.evidence_dir, mission_id, "mission.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None

    def list_missions(self) -> List[Dict[str, Any]]:
        missions = []
        if not os.path.exists(self.evidence_dir):
            return []
        for name in os.listdir(self.evidence_dir):
            path = os.path.join(self.evidence_dir, name, "mission.json")
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        missions.append(json.load(f))
                except Exception:
                    pass
        return sorted(missions, key=lambda m: m.get("created_at", ""), reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        missions = self.list_missions()
        fail_closed_count = sum(1 for m in missions if m.get("release_decision") == "FAIL_CLOSED")
        conditional_go_count = sum(1 for m in missions if m.get("release_decision") == "CONDITIONAL_GO")
        go_count = sum(1 for m in missions if m.get("release_decision") == "GO")
        
        state = "LIVE"
        if fail_closed_count > 0:
            state = "FAIL_CLOSED"

        return {
            "state": state,
            "mission_count": len(missions),
            "fail_closed_count": fail_closed_count,
            "conditional_go_count": conditional_go_count,
            "go_count": go_count,
            "latest_mission_id": missions[0]["mission_id"] if missions else None,
            "execution_enabled": False
        }
