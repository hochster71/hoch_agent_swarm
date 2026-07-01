export type ControlImplementationStatus =
  | "implemented"
  | "partially_implemented"
  | "planned"
  | "not_applicable";

export type EvidenceStatus =
  | "valid"
  | "stale"
  | "missing"
  | "pending_review";

export type ComplianceControl = {
  control_id: string;
  framework: string;
  section: string;
  title: string;
  description: string;
  status: ControlImplementationStatus;
  evidence_ids: string[];
  last_evaluated: string;
  owner: string;
};

export type ComplianceEvidence = {
  evidence_id: string;
  title: string;
  collected_at: string;
  source_type: "audit_log" | "runbook_run" | "scan_report" | "policy_assertion" | "manual";
  file_path: string;
  file_hash: string;
  status: EvidenceStatus;
  expires_at?: string;
  reviewed_by?: string;
  reviewed_at?: string;
};

export type AttestationRecord = {
  attestation_id: string;
  control_id: string;
  operator_id: string;
  operator_name: string;
  timestamp: string;
  notes: string;
  evidence_refs: string[];
};

export type FrameworkSummary = {
  id: string;
  name: string;
  description: string;
  total_controls: number;
  implemented_controls: number;
  partial_controls: number;
  coverage_percent: number;
};
