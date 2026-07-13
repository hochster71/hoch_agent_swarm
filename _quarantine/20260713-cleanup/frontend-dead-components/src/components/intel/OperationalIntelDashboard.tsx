import React from "react";
import { useIntelStore } from "../../lib/intel/insightFeedback";
import { InsightExplanationPanel } from "./InsightExplanationPanel";
import { AnomalyDetectionPanel } from "./AnomalyDetectionPanel";
import { TrendAnalysisPanel } from "./TrendAnalysisPanel";
import { RecommendationList } from "./RecommendationList";
import { ModelHealthPanel } from "./ModelHealthPanel";
import { InsightHistory } from "./InsightHistory";
import type { OperationalInsight } from "../../lib/intel/insightTypes";

export const OperationalIntelDashboard: React.FC = () => {
  const intelState = useIntelStore();

  const handleAction = (insight: OperationalInsight) => {
    if (insight.recommendation?.command_text) {
      // Dispatch to CommandInput bridge
      const commandInput = document.getElementById("command-input") as HTMLInputElement;
      if (commandInput) {
        commandInput.value = insight.recommendation.command_text;
        // Trigger React store dispatch if window bindings exist
        const previewBtn = document.getElementById("btn-preview-command");
        if (previewBtn) {
          previewBtn.click();
        }
      }
    }
  };

  const activeInsightsCount = intelState.insights.filter(x => x.status === "new").length;
  const criticalFindingsCount = intelState.insights.filter(x => x.severity === "high" || x.severity === "critical").length;

  return (
    <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px", height: "100%", overflowY: "auto", boxSizing: "border-box" }}>
      {/* Title Header */}
      <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "10px" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "16px", fontWeight: "bold", color: "#fff", display: "flex", alignItems: "center", gap: "8px" }}>
            🧠 OPERATIONAL INTELLIGENCE & INSIGHTS
          </h1>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", display: "block", marginTop: "4px" }}>
            Automated anomaly detections, model confidence metrics, and explainable recommendations.
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "9px", color: "var(--accent-teal)", fontFamily: "monospace", animation: "pulse 2s infinite" }}>● model online</span>
        </div>
      </div>

      {/* Info Stats Banner */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "12px" }}>
        <div style={{ background: "rgba(22, 28, 45, 0.5)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "8px", padding: "10px", textAlign: "left" }}>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", display: "block" }}>ACTIVE INSIGHTS</span>
          <span style={{ fontSize: "18px", fontWeight: "bold", color: "#fff" }}>{activeInsightsCount}</span>
        </div>
        <div style={{ background: "rgba(22, 28, 45, 0.5)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "8px", padding: "10px", textAlign: "left" }}>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", display: "block" }}>CRITICAL FINDINGS</span>
          <span style={{ fontSize: "18px", fontWeight: "bold", color: criticalFindingsCount > 0 ? "#f87171" : "#10b981" }}>{criticalFindingsCount}</span>
        </div>
        <div style={{ background: "rgba(22, 28, 45, 0.5)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "8px", padding: "10px", textAlign: "left" }}>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", display: "block" }}>MODEL ACCURACY</span>
          <span style={{ fontSize: "18px", fontWeight: "bold", color: "#818cf8" }}>{intelState.modelAccuracyScore}%</span>
        </div>
        <div style={{ background: "rgba(22, 28, 45, 0.5)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "8px", padding: "10px", textAlign: "left" }}>
          <span style={{ fontSize: "9px", color: "var(--text-secondary)", display: "block" }}>EVALUATION LATENCY</span>
          <span style={{ fontSize: "18px", fontWeight: "bold", color: "#10b981" }}>24ms</span>
        </div>
      </div>

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "16px" }}>
        
        {/* Left Side: Recommendations and Historical feedback */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "12px" }}>TOP AI SWARM RECOMMENDATIONS</h2>
            <RecommendationList
              insights={intelState.insights}
              onExplain={intelState.selectInsight}
              onAction={handleAction}
            />
          </div>

          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "10px" }}>FEEDBACK AUDIT TRAIL</h2>
            <InsightHistory insights={intelState.insights} />
          </div>
        </div>

        {/* Right Side: Anomaly logs and Model Health */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "12px" }}>REAL-TIME ANOMALY DETECTIONS</h2>
            <AnomalyDetectionPanel />
          </div>

          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "12px" }}>HISTORICAL TELEMETRY TRENDS</h2>
            <TrendAnalysisPanel />
          </div>

          <div className="card" style={{ padding: "16px" }}>
            <h2 className="card-title" style={{ fontSize: "12px", marginBottom: "10px" }}>MODEL COMPLIANCE HEALTH</h2>
            <ModelHealthPanel />
          </div>
        </div>

      </div>

      {/* Slide-out Explanation Drawer */}
      {intelState.activeInsight && (
        <InsightExplanationPanel
          insight={intelState.activeInsight}
          onClose={() => intelState.selectInsight(null)}
          onSubmitFeedback={(val) => intelState.submitFeedback(intelState.activeInsight!.insight_id, val)}
        />
      )}
    </div>
  );
};
