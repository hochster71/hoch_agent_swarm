export type InsightType =
  | "recommendation"
  | "anomaly"
  | "trend"
  | "prediction"
  | "risk";

export type InsightSeverity = "info" | "low" | "medium" | "high" | "critical";

export type InsightStatus =
  | "new"
  | "reviewed"
  | "accepted"
  | "dismissed"
  | "actioned"
  | "resolved";

export type InsightFeedback = "helpful" | "partial" | "not_helpful";

export type OperationalInsight = {
  insight_id: string;
  created_at: string;
  type: InsightType;
  severity: InsightSeverity;
  status: InsightStatus;
  title: string;
  summary: string;
  target: {
    type: "asset" | "swarm" | "task" | "system";
    id: string;
    name: string;
  };
  confidence: number;
  explanation: {
    rationale: string;
    contributing_factors: string[];
    assumptions: string[];
    evidence_refs: string[];
  };
  recommendation?: {
    action_label: string;
    command_text?: string;
    expected_impact?: string;
    risk?: "low" | "medium" | "high" | "critical";
  };
  feedback?: {
    value: InsightFeedback;
    comment?: string;
    submitted_at: string;
    submitted_by: string;
  };
  metadata?: Record<string, unknown>;
};
