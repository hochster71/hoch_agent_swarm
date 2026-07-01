import { create } from "zustand";
import type { AiSystemRecord, GovernanceStatus, ControlStatus } from "./governanceTypes";
import { scoreAiSystemRisk } from "./aiRiskScoring";
import { initialAiSystems } from "./governanceFixtures";

type GovernanceRegistryStore = {
  systems: AiSystemRecord[];
  registerSystem: (system: Omit<AiSystemRecord, "risk_tier" | "review">) => void;
  updateControlStatus: (systemId: string, controlId: string, status: ControlStatus, evidenceRef?: string) => void;
  submitReview: (systemId: string) => void;
  approveReview: (systemId: string, reviewer: string) => void;
  rejectReview: (systemId: string, reviewer: string) => void;
  retireSystem: (systemId: string) => void;
};

const triggerAuditLog = (action: string, summary: string, targetId: string, targetName: string, severity: string, result: string) => {
  if (typeof window !== "undefined" && window.addAuditEvent) {
    window.addAuditEvent({
      action: {
        type: action,
        summary: summary,
      },
      actor: {
        id: "operator",
        name: "Michael Hoch",
        type: "human",
        role: "Operator",
      },
      target: {
        type: "system",
        id: targetId,
        name: targetName,
      },
      result: result,
      severity: severity,
      provenance: {
        source: "manual",
        evidence_refs: [],
      },
      policy: {
        required: false,
        result: "not_required",
      },
    });
  }
};

export const useGovernanceRegistryStore = create<GovernanceRegistryStore>((set) => ({
  systems: initialAiSystems.map((s) => {
    const scored = scoreAiSystemRisk(s);
    return { ...s, risk_tier: scored.tier };
  }),

  registerSystem: (newSystem) => {
    const tempRecord: AiSystemRecord = {
      ...newSystem,
      risk_tier: "low",
      review: {
        next_review_due: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString(),
      },
    };
    const scored = scoreAiSystemRisk(tempRecord);
    const finalRecord: AiSystemRecord = {
      ...tempRecord,
      risk_tier: scored.tier,
    };

    set((state) => ({
      systems: [...state.systems, finalRecord],
    }));

    triggerAuditLog(
      "AI_SYSTEM_REGISTERED",
      `AI System registered: ${finalRecord.name} (${finalRecord.type}) with risk tier ${finalRecord.risk_tier}`,
      finalRecord.system_id,
      finalRecord.name,
      finalRecord.risk_tier === "critical" || finalRecord.risk_tier === "high" ? "high" : "low",
      "success"
    );

    triggerAuditLog(
      "AI_RISK_ASSESSED",
      `AI Risk assessed for ${finalRecord.name}: Score ${scored.score} (${scored.tier})`,
      finalRecord.system_id,
      finalRecord.name,
      finalRecord.risk_tier === "critical" || finalRecord.risk_tier === "high" ? "high" : "low",
      "success"
    );
  },

  updateControlStatus: (systemId, controlId, status, evidenceRef) => {
    set((state) => {
      const updated = state.systems.map((sys) => {
        if (sys.system_id === systemId) {
          const controls = sys.controls.map((ctrl) => {
            if (ctrl.control_id === controlId) {
              const evidence_refs = ctrl.evidence_refs;
              if (evidenceRef && !evidence_refs.includes(evidenceRef)) {
                evidence_refs.push(evidenceRef);
              }
              return { ...ctrl, status, evidence_refs };
            }
            return ctrl;
          });
          const tempSys = { ...sys, controls };
          const scored = scoreAiSystemRisk(tempSys);
          return { ...tempSys, risk_tier: scored.tier };
        }
        return sys;
      });

      const updatedSys = updated.find((s) => s.system_id === systemId);
      if (updatedSys) {
        triggerAuditLog(
          "CONTROL_MAPPING_UPDATED",
          `Control ${controlId} status updated to ${status} for ${updatedSys.name}`,
          systemId,
          updatedSys.name,
          "info",
          "success"
        );
        const scored = scoreAiSystemRisk(updatedSys);
        triggerAuditLog(
          "AI_RISK_ASSESSED",
          `AI Risk re-assessed for ${updatedSys.name}: Score ${scored.score} (${scored.tier})`,
          systemId,
          updatedSys.name,
          scored.tier === "critical" || scored.tier === "high" ? "high" : "low",
          "success"
        );
      }
      return { systems: updated };
    });
  },

  submitReview: (systemId) => {
    set((state) => {
      const updated = state.systems.map((sys) => {
        if (sys.system_id === systemId) {
          triggerAuditLog(
            "GOVERNANCE_REVIEW_REQUESTED",
            `Governance review requested for ${sys.name}`,
            systemId,
            sys.name,
            "medium",
            "success"
          );
          return { ...sys, status: "under_review" as GovernanceStatus };
        }
        return sys;
      });
      return { systems: updated };
    });
  },

  approveReview: (systemId, reviewer) => {
    set((state) => {
      const updated = state.systems.map((sys) => {
        if (sys.system_id === systemId) {
          triggerAuditLog(
            "GOVERNANCE_REVIEW_APPROVED",
            `Governance review approved for ${sys.name} by ${reviewer}`,
            systemId,
            sys.name,
            "info",
            "success"
          );
          return {
            ...sys,
            status: "approved" as GovernanceStatus,
            review: {
              reviewed_at: new Date().toISOString(),
              reviewed_by: reviewer,
              next_review_due: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString(),
            },
          };
        }
        return sys;
      });
      return { systems: updated };
    });
  },

  rejectReview: (systemId, reviewer) => {
    set((state) => {
      const updated = state.systems.map((sys) => {
        if (sys.system_id === systemId) {
          triggerAuditLog(
            "GOVERNANCE_REVIEW_REJECTED",
            `Governance review rejected (restricted) for ${sys.name} by ${reviewer}`,
            systemId,
            sys.name,
            "high",
            "success"
          );
          return {
            ...sys,
            status: "restricted" as GovernanceStatus,
            review: {
              reviewed_at: new Date().toISOString(),
              reviewed_by: reviewer,
              next_review_due: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
            },
          };
        }
        return sys;
      });
      return { systems: updated };
    });
  },

  retireSystem: (systemId) => {
    set((state) => {
      const updated = state.systems.map((sys) => {
        if (sys.system_id === systemId) {
          triggerAuditLog(
            "GOVERNANCE_REVIEW_REJECTED",
            `AI System retired: ${sys.name}`,
            systemId,
            sys.name,
            "info",
            "success"
          );
          return { ...sys, status: "retired" as GovernanceStatus };
        }
        return sys;
      });
      return { systems: updated };
    });
  },
}));
