import { Control, ChecklistItem, Risk } from './schemas';

export const mockControls: Control[] = [
  {
    id: "AC-1",
    name: "Access Control Policy",
    family: "Access Control",
    description: "Establish access control policy rules."
  },
  {
    id: "SC-7",
    name: "Boundary Protection",
    family: "System and Communications Protection",
    description: "Protect application boundaries from external routing."
  }
];

export const mockChecklist: ChecklistItem[] = [
  {
    id: "chk-001",
    controlId: "AC-1",
    status: "COMPLIANT",
    comments: "Verified local user limits active."
  },
  {
    id: "chk-002",
    controlId: "SC-7",
    status: "COMPLIANT",
    comments: "Exposed API only behind Tailscale."
  }
];

export const mockRisks: Risk[] = [
  {
    id: "risk-001",
    title: "Unauthorized public deployment",
    impact: "HIGH",
    likelihood: "LOW",
    status: "MITIGATED"
  }
];
