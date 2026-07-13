import React from "react";
import { InsightCard } from "./InsightCard";
import type { OperationalInsight } from "../../lib/intel/insightTypes";

type Props = {
  insights: OperationalInsight[];
  onExplain: (insight: OperationalInsight) => void;
  onAction: (insight: OperationalInsight) => void;
};

export const RecommendationList: React.FC<Props> = ({ insights, onExplain, onAction }) => {
  const recommendations = insights.filter(x => x.type === "recommendation" && x.status === "new");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {recommendations.length === 0 ? (
        <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontStyle: "italic", padding: "12px 0", textAlign: "left" }}>
          No active AI recommendations. All swarms functioning normally.
        </div>
      ) : (
        recommendations.map((insight) => (
          <InsightCard
            key={insight.insight_id}
            insight={insight}
            onExplain={onExplain}
            onAction={onAction}
          />
        ))
      )}
    </div>
  );
};
