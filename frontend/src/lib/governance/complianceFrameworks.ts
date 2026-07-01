export type ComplianceFrameworkCode = "NIST_AI_RMF" | "NIST_800_53" | "OWASP_SAMM" | "CUSTOM";

export type ComplianceControlDefinition = {
  control_id: string;
  framework: ComplianceFrameworkCode;
  name: string;
  description: string;
};

export const frameworkDefinitions: ComplianceControlDefinition[] = [
  { control_id: "NIST-AI-1.1", framework: "NIST_AI_RMF", name: "Govern 1.1", description: "Policies, processes, procedures, and practices across the organization are established and deployed." },
  { control_id: "NIST-AI-1.2", framework: "NIST_AI_RMF", name: "Govern 1.2", description: "Risk management culture is established and maintained." },
  { control_id: "NIST-AI-2.1", framework: "NIST_AI_RMF", name: "Map 2.1", description: "AI system categorization is performed according to context and domain." },
  { control_id: "NIST-AI-3.1", framework: "NIST_AI_RMF", name: "Measure 3.1", description: "Assessing AI system trustworthiness, including transparency, bias, and performance." },
  { control_id: "NIST-AI-4.1", framework: "NIST_AI_RMF", name: "Manage 4.1", description: "AI systems are monitored and managed continuously for post-deployment risks." },
  { control_id: "AC-3", framework: "NIST_800_53", name: "Access Enforcement", description: "Enforces approved authorizations for logical access to information." },
  { control_id: "AC-6", framework: "NIST_800_53", name: "Least Privilege", description: "Limits access privileges to the minimum necessary for performance of duties." },
  { control_id: "AC-17", framework: "NIST_800_53", name: "Remote Access", description: "Monitors and controls remote access sessions." },
  { control_id: "SI-2", framework: "NIST_800_53", name: "Flaw Remediation", description: "Identifies, reports, and corrects software vulnerabilities." },
  { control_id: "SAMM-SM-1.1", framework: "OWASP_SAMM", name: "Strategy & Metrics - Level 1", description: "Establish a software security program roadmap." },
  { control_id: "SAMM-SM-1.2", framework: "OWASP_SAMM", name: "Strategy & Metrics - Level 2", description: "Define and execute consistent compliance audits." },
  { control_id: "SAMM-SM-2.1", framework: "OWASP_SAMM", name: "Policy & Compliance - Level 1", description: "Identify external compliance requirements and map them." },
];
