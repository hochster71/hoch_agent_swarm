import { ComplianceControl, ComplianceEvidence, AttestationRecord } from "./complianceTypes";

export const initialControls: ComplianceControl[] = [
  {
    control_id: "GV.OC-01",
    framework: "nist-csf-2.0",
    section: "Govern (GV)",
    title: "Organizational Context",
    description: "The organization's mission, stakeholders, and legal requirements are understood and documented.",
    status: "implemented",
    evidence_ids: ["ev-gov-context-01"],
    last_evaluated: "2026-06-24T10:00:00Z",
    owner: "Security Swarm"
  },
  {
    control_id: "ID.RA-01",
    framework: "nist-csf-2.0",
    section: "Identify (ID)",
    title: "Risk Assessment Policy",
    description: "Cybersecurity risk assessment procedures are established, documented, and reviewed.",
    status: "implemented",
    evidence_ids: ["ev-risk-policy-01"],
    last_evaluated: "2026-06-24T11:15:00Z",
    owner: "Security Swarm"
  },
  {
    control_id: "PR.AT-01",
    framework: "nist-csf-2.0",
    section: "Protect (PR)",
    title: "Awareness & Training",
    description: "Personnel are provided with cybersecurity awareness training to perform roles securely.",
    status: "partially_implemented",
    evidence_ids: [],
    last_evaluated: "2026-06-24T12:00:00Z",
    owner: "QA Swarm"
  },
  {
    control_id: "AC-2",
    framework: "nist-800-53",
    section: "Access Control (AC)",
    title: "Account Management",
    description: "Manage system accounts, including establishing, activating, modifying, and disabling accounts.",
    status: "implemented",
    evidence_ids: ["ev-ac-mgmt-01"],
    last_evaluated: "2026-06-23T09:30:00Z",
    owner: "Control Plane Swarm"
  },
  {
    control_id: "AU-6",
    framework: "nist-800-53",
    section: "Audit and Accountability (AU)",
    title: "Audit Record Review & Analysis",
    description: "Review and analyze system audit records for indications of unusual or suspicious activity.",
    status: "implemented",
    evidence_ids: ["ev-audit-review-01"],
    last_evaluated: "2026-06-24T12:10:00Z",
    owner: "Security Swarm"
  },
  {
    control_id: "A.6.1",
    framework: "iso-42001",
    section: "AI Governance & Policies",
    title: "AI Risk Management Policies",
    description: "Define policies governing risk criteria and threshold boundaries for autonomous model operations.",
    status: "implemented",
    evidence_ids: ["ev-ai-policy-01"],
    last_evaluated: "2026-06-24T08:45:00Z",
    owner: "Governance Swarm"
  },
  {
    control_id: "A.8.2",
    framework: "iso-42001",
    section: "Data Management & Traceability",
    title: "Data Provenance Logging",
    description: "Ensure exact provenance and lifecycle tracking for training, testing, and execution data sets.",
    status: "partially_implemented",
    evidence_ids: ["ev-data-prov-stale"],
    last_evaluated: "2026-06-24T07:15:00Z",
    owner: "Memory Swarm"
  },
  {
    control_id: "CC6.1",
    framework: "soc2",
    section: "Common Criteria (CC)",
    title: "Logical Access Controls",
    description: "Implement logical access security controls to prevent unauthorized access to assets.",
    status: "implemented",
    evidence_ids: ["ev-soc2-access-01"],
    last_evaluated: "2026-06-23T14:20:00Z",
    owner: "Control Plane Swarm"
  }
];

export const initialEvidence: ComplianceEvidence[] = [
  {
    evidence_id: "ev-gov-context-01",
    title: "Organizational Mission & Scope Charter",
    collected_at: "2026-06-24T09:30:00Z",
    source_type: "manual",
    file_path: "/docs/compliance/mission_charter.pdf",
    file_hash: "sha256:8f430de28ba248faec892e80bc8f7c9e",
    status: "valid"
  },
  {
    evidence_id: "ev-risk-policy-01",
    title: "Security Swarm Risk Assessment Report",
    collected_at: "2026-06-24T11:00:00Z",
    source_type: "scan_report",
    file_path: "/scans/risk_report_latest.json",
    file_hash: "sha256:d82b40a32490dfb190f84523ad0b0d39",
    status: "valid"
  },
  {
    evidence_id: "ev-ac-mgmt-01",
    title: "Decentralized Ledger User Access Logs",
    collected_at: "2026-06-23T08:00:00Z",
    source_type: "audit_log",
    file_path: "/audit/ledger_block_access.log",
    file_hash: "sha256:ca820f8c32da45dfaef8234ea72ef21a",
    status: "valid"
  },
  {
    evidence_id: "ev-audit-review-01",
    title: "ZTA Audit Pipeline Telemetry Verify Record",
    collected_at: "2026-06-24T12:05:00Z",
    source_type: "policy_assertion",
    file_path: "/audit/zta_telemetry_signature.sig",
    file_hash: "sha256:f12a938cde9943fe0b28eef92e92c2da",
    status: "valid"
  },
  {
    evidence_id: "ev-ai-policy-01",
    title: "NIST AI Risk Management Framework Compliance Policy Document",
    collected_at: "2026-06-24T08:00:00Z",
    source_type: "manual",
    file_path: "/docs/compliance/ai_governance_v1.pdf",
    file_hash: "sha256:1a8b9c2d3e4f5a6b7c8d9e0f1a2b3c4d",
    status: "valid"
  },
  {
    evidence_id: "ev-data-prov-stale",
    title: "Swarms Dataset Fingerprint Record",
    collected_at: "2026-06-24T12:00:00Z",
    source_type: "runbook_run",
    file_path: "/runs/dataset_fingerprint_2026-06-24.json",
    file_hash: "sha256:abc321d82b40a32490dfb190f84523ad",
    status: "valid",
    expires_at: "2026-08-24T12:00:00Z"
  },
  {
    evidence_id: "ev-soc2-access-01",
    title: "Tenant Isolation Security Scan Report",
    collected_at: "2026-06-23T14:00:00Z",
    source_type: "scan_report",
    file_path: "/scans/tenant_isolation_report.json",
    file_hash: "sha256:9f8e7d6c5b4a3c2b1a0f9e8d7c6b5a4",
    status: "valid"
  }
];

export const initialAttestations: AttestationRecord[] = [
  {
    attestation_id: "att-001",
    control_id: "GV.OC-01",
    operator_id: "op-mh-99",
    operator_name: "Michael Hoch",
    timestamp: "2026-06-24T09:45:00Z",
    notes: "Verified Scope Charter and confirmed legal alignment with control plane swarms.",
    evidence_refs: ["ev-gov-context-01"]
  },
  {
    attestation_id: "att-002",
    control_id: "A.6.1",
    operator_id: "op-mh-99",
    operator_name: "Michael Hoch",
    timestamp: "2026-06-24T08:15:00Z",
    notes: "NIST AI RMF policy mapping verified and approved for active swarm deployments.",
    evidence_refs: ["ev-ai-policy-01"]
  }
];
