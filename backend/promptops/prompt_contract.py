from pydantic import BaseModel
from typing import List, Dict

class PromptContractModel(BaseModel):
    mission_id: str
    prompt_class: str
    objective: str
    current_proven_state: str
    exact_scope: str
    non_goals: str
    required_files: str
    required_tests: str = ""
    required_gates: str
    runtime_truth_signals: str
    evidence_path: str
    commit_policy: str
    closeout_report_schema: str
    stop_conditions: str
    fake_completion_controls: str
    rewritten_text: str = ""
