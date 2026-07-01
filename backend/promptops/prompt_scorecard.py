import re
import yaml
import os

class PromptScorecard:
    def __init__(self, rubric_path=None):
        if rubric_path is None:
            if os.path.exists("/app"):
                rubric_path = "/app/config/prompt_score_rubric.yaml"
            else:
                rubric_path = os.path.join(os.path.dirname(__file__), "../../config/prompt_score_rubric.yaml")
        
        self.rubric = {}
        if os.path.exists(rubric_path):
            try:
                with open(rubric_path, "r") as f:
                    self.rubric = yaml.safe_load(f).get("dimensions", {})
            except Exception:
                pass
        
        if not self.rubric:
            self.rubric = {
                "scope_clarity": {"weight": 0.15},
                "non_goals_defined": {"weight": 0.10},
                "runtime_truth_required": {"weight": 0.15},
                "gate_requirements_defined": {"weight": 0.10},
                "evidence_required": {"weight": 0.15},
                "final_report_schema_defined": {"weight": 0.05},
                "anti_fake_claim_controls": {"weight": 0.10},
                "human_loop_reduction": {"weight": 0.10},
                "rollback_or_stop_condition": {"weight": 0.05},
                "integration_safety": {"weight": 0.05}
            }

    def evaluate(self, prompt_text: str) -> dict:
        text_lower = prompt_text.lower()
        
        scores = {}
        
        # 1. Scope clarity: Look for file paths, modules, specific files
        paths_count = len(re.findall(r"[\w\-\.\/]+\.(?:py|ts|tsx|yaml|yml|sh|md|json)", text_lower))
        scores["scope_clarity"] = min(paths_count * 2, 10)
        if "scope:" in text_lower or "files:" in text_lower:
            scores["scope_clarity"] = max(scores["scope_clarity"], 8)
            
        # 2. Non-goals: Look for non-goals or what not to touch
        if "non-goal" in text_lower or "non goal" in text_lower or "do not touch" in text_lower or "do not modify" in text_lower:
            scores["non_goals_defined"] = 10
        else:
            scores["non_goals_defined"] = 2
            
        # 3. Runtime truth required
        if "runtime truth" in text_lower or "docker" in text_lower or "k8s" in text_lower or "inspect" in text_lower or "truth" in text_lower:
            scores["runtime_truth_required"] = 10
        else:
            scores["runtime_truth_required"] = 3
            
        # 4. Gate requirements
        if "gate" in text_lower or "check" in text_lower or "_gate" in text_lower:
            scores["gate_requirements_defined"] = 10
        else:
            scores["gate_requirements_defined"] = 2
            
        # 5. Evidence required
        if "evidence" in text_lower or "proof" in text_lower or "docs/evidence" in text_lower or "report" in text_lower:
            scores["evidence_required"] = 10
        else:
            scores["evidence_required"] = 1
            
        # 6. Final report schema defined
        if "final report" in text_lower or "schema" in text_lower or "closeout" in text_lower or "report" in text_lower or "prove" in text_lower:
            scores["final_report_schema_defined"] = 10
        else:
            scores["final_report_schema_defined"] = 2
            
        # 7. Anti-fake controls
        if "prevent fake" in text_lower or "fake" in text_lower or "anti-fake" in text_lower or "mismatch" in text_lower:
            scores["anti_fake_claim_controls"] = 10
        else:
            scores["anti_fake_claim_controls"] = 2
            
        # 8. Human loop reduction
        if "take michael out" in text_lower or "automation" in text_lower or "automatic" in text_lower or "run" in text_lower:
            scores["human_loop_reduction"] = 10
        else:
            scores["human_loop_reduction"] = 4
            
        # 9. Rollback or stop condition
        if "rollback" in text_lower or "stop condition" in text_lower or "fail if" in text_lower or "exit 1" in text_lower:
            scores["rollback_or_stop_condition"] = 10
        else:
            scores["rollback_or_stop_condition"] = 3
            
        # 10. Integration safety
        if "regression" in text_lower or "pytest" in text_lower or "playwright" in text_lower or "tests/" in text_lower:
            scores["integration_safety"] = 10
        else:
            scores["integration_safety"] = 4

        # Calculate weighted overall score
        total_score = 0.0
        for dim, info in self.rubric.items():
            total_score += scores.get(dim, 0) * info.get("weight", 0.1) * 10
            
        total_score = min(max(total_score, 0.0), 100.0)
        
        if total_score >= 80:
            status = "EXECUTABLE"
        elif total_score >= 60:
            status = "NEEDS_PROMPTOPS_REWRITE"
        else:
            status = "BLOCKED_UNTIL_SCOPED"
            
        return {
            "score": round(total_score, 1),
            "status": status,
            "dimension_scores": scores
        }
