export interface Control {
  id: string;
  name: string;
  family: string;
  description: string;
}

export interface ChecklistItem {
  id: string;
  controlId: string;
  status: 'COMPLIANT' | 'NON_COMPLIANT' | 'NOT_APPLICABLE';
  comments?: string;
}

export interface EvidenceArtifact {
  id: string;
  checklistId: string;
  filePath: string;
  sha256: string;
  createdAt: string;
}

export interface Risk {
  id: string;
  title: string;
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  likelihood: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'OPEN' | 'MITIGATED';
}

export interface ActionItem {
  id: string;
  title: string;
  assignedTo: string;
  dueDate: string;
  status: 'PENDING' | 'COMPLETED';
}

export interface ReviewDecision {
  id: string;
  checkpointName: string;
  authorized: boolean;
  signer: string;
  signedAt: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  action: string;
  details: string;
}
