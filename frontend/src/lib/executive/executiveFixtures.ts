import type { PortfolioMetric, ExecutiveRecommendation } from "./executiveTypes";

export const initialPortfolioMetrics: PortfolioMetric[] = [
  {
    metric_id: "m-risk",
    label: "Portfolio Risk Level",
    value: "28 High Risks",
    status: "watch",
    trend: "down",
    summary: "Reflects active threats including prompt injection attempts and missing controls.",
  },
  {
    metric_id: "m-readiness",
    label: "Operational Readiness",
    value: "84% Ready",
    status: "stable",
    trend: "up",
    summary: "System availability, average node CPU headrooms, and ICMP ping thresholds are stable.",
  },
  {
    metric_id: "m-gov",
    label: "Governance Control Mappings",
    value: "76% Covered",
    status: "stable",
    trend: "flat",
    summary: "Progress in NIST AI RMF and NIST 800-53 security control mapping alignments.",
  },
  {
    metric_id: "m-compliance",
    label: "Compliance Gaps",
    value: "9 Controls Missing",
    status: "watch",
    trend: "down",
    summary: "Number of missing framework controls across registered AI systems.",
  }
];

export const initialRecommendations: ExecutiveRecommendation[] = [
  {
    recommendation_id: "rec-remediate-controls",
    title: "Remediate Missing AI Security Controls",
    priority: "high",
    decision_required: true,
    summary: "Coordinate with the Security team to map AC-3 and AC-6 controls on critical-risk systems.",
    rationale: "4 critical/high-risk systems currently have missing compliance mapping links, raising risk scores.",
    expected_impact: "Will improve overall governance score by +12% and lower portfolio risk.",
    evidence_refs: ["evidence.samm.sm21", "evidence.800_53.ac17"],
    proposed_action: "Initiate patching of missing enclaves controls.",
  },
  {
    recommendation_id: "rec-run-chaos",
    title: "Schedule Automated Adversarial Drills",
    priority: "medium",
    decision_required: false,
    summary: "Schedule weekly automated red-team simulations to audit enclaves under degraded state.",
    rationale: "Safety assertions for policy enforcement dropped to 92% during the last policy bypass drill.",
    expected_impact: "Confirm resilience and generate continuous compliance evidence.",
    evidence_refs: ["scenario.sc-policy-bypass.run.latest"],
    proposed_action: "Inject automated scheduling hook into CI/CD pipeline.",
  }
];
