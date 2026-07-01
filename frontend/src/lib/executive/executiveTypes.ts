export type ExecutivePostureStatus =
  | "strong"
  | "stable"
  | "watch"
  | "degraded"
  | "critical";

export type PortfolioMetric = {
  metric_id: string;
  label: string;
  value: number | string;
  status: ExecutivePostureStatus;
  trend: "up" | "down" | "flat";
  summary: string;
};

export type ExecutiveRecommendation = {
  recommendation_id: string;
  title: string;
  priority: "low" | "medium" | "high" | "critical";
  decision_required: boolean;
  summary: string;
  rationale: string;
  expected_impact: string;
  evidence_refs: string[];
  proposed_action: string;
};

export type ExecutiveReport = {
  report_id: string;
  generated_at: string;
  time_range: {
    start: string;
    end: string;
  };
  posture: {
    overall_status: ExecutivePostureStatus;
    risk_score: number;
    readiness_score: number;
    governance_score: number;
    compliance_coverage_percent: number;
  };
  metrics: PortfolioMetric[];
  recommendations: ExecutiveRecommendation[];
  open_risks: string[];
  blocked_decisions: string[];
  evidence_refs: string[];
};
