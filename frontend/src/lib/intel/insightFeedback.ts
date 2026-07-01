import { create } from "zustand";
import type { InsightFeedback, OperationalInsight } from "./insightTypes";
import { generateMockInsights } from "./insightEngine";

type IntelStore = {
  insights: OperationalInsight[];
  activeInsight: OperationalInsight | null;
  feedbackHistory: Record<string, InsightFeedback>;
  modelAccuracyScore: number;
  
  setInsights: (insights: OperationalInsight[]) => void;
  selectInsight: (insight: OperationalInsight | null) => void;
  submitFeedback: (insightId: string, value: InsightFeedback) => void;
  dismissInsight: (insightId: string) => void;
};

export const useIntelStore = create<IntelStore>((set) => ({
  insights: generateMockInsights(),
  activeInsight: null,
  feedbackHistory: {},
  modelAccuracyScore: 84, // Initial accuracy metric

  setInsights: (insights) => set({ insights }),
  selectInsight: (insight) => set({ activeInsight: insight }),
  submitFeedback: (insightId, value) =>
    set((state) => {
      const updatedInsights = state.insights.map((insight) => {
        if (insight.insight_id === insightId) {
          return {
            ...insight,
            status: "reviewed" as const,
            feedback: {
              value,
              submitted_at: new Date().toISOString(),
              submitted_by: "michael.hoch",
            },
          };
        }
        return insight;
      });
      
      const newHistory = { ...state.feedbackHistory, [insightId]: value };
      const totalFeedback = Object.keys(newHistory).length;
      const helpfulFeedback = Object.values(newHistory).filter(x => x === "helpful" || x === "partial").length;
      const accuracy = totalFeedback > 0 ? Math.round((helpfulFeedback / totalFeedback) * 100) : 84;

      return {
        insights: updatedInsights,
        feedbackHistory: newHistory,
        modelAccuracyScore: accuracy,
        activeInsight: state.activeInsight?.insight_id === insightId 
          ? {
              ...state.activeInsight,
              status: "reviewed" as const,
              feedback: {
                value,
                submitted_at: new Date().toISOString(),
                submitted_by: "michael.hoch",
              }
            }
          : state.activeInsight
      };
    }),
  dismissInsight: (insightId) =>
    set((state) => ({
      insights: state.insights.map((insight) =>
        insight.insight_id === insightId ? { ...insight, status: "dismissed" as const } : insight
      ),
      activeInsight: state.activeInsight?.insight_id === insightId ? null : state.activeInsight
    })),
}));
