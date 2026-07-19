from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Control(BaseModel):
    control_id: str
    version: str
    level: str
    domain: str
    family: str
    title: str
    requirement: str
    rationale: Optional[str] = None
    applicability: List[str] = Field(default_factory=list)
    severity: str
    mandatory: bool
    framework_mappings: Dict[str, List[str]] = Field(default_factory=dict)
    assessment_procedure_ids: List[str]
    freshness_period_hours: int
    failure_effect: str
    owner_role: Optional[str] = None
    validator_role: Optional[str] = None
    status: str

class Evidence(BaseModel):
    evidence_id: str
    control_id: str
    assessment_run_id: str
    source_type: str
    source_path: str
    source_system: str
    generated_at: str
    collected_at: str
    commit_sha: Optional[str] = None
    sha256: str
    producer: str
    validator: str
    fresh_until: str
    status: str
    metadata: Dict = Field(default_factory=dict)

class Finding(BaseModel):
    finding_id: str
    control_id: str
    assessment_run_id: str
    title: str
    description: str
    severity: str
    status: str
    technical_result: str
    affected_components: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    root_cause: Optional[str] = None
    recommended_action: Optional[str] = None
    created_at: str
    due_at: Optional[str] = None
    closed_at: Optional[str] = None

class Milestone(BaseModel):
    milestone_id: str
    description: str
    due_date: str
    completed_at: Optional[str] = None
    status: str

class POAMHistoryItem(BaseModel):
    timestamp: str
    updated_by: str
    previous_status: str
    new_status: str
    comment: str

class POAMItem(BaseModel):
    poam_id: str
    finding_ids: List[str]
    owner: str
    milestones: List[Milestone] = Field(default_factory=list)
    due_date: str
    severity: str
    status: str
    remediation_plan: str
    history: List[POAMHistoryItem] = Field(default_factory=list)

class Reason(BaseModel):
    control_id: str
    reason: str

class CertificationDecision(BaseModel):
    decision_id: str
    scope: str
    level: str
    decision: str
    reasons: List[Reason] = Field(default_factory=list)
    assessed_at: str
    expires_at: str
    evaluator: str
    risk_decision: Optional[str] = None
    operating_posture: str

class ConMonSignal(BaseModel):
    signal_id: str
    signal_type: str
    target: str
    observed_at: str
    previous_state: Optional[str] = None
    new_state: str
    impacted_controls: List[str]
    severity: str
