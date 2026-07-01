import { create } from "zustand";
import type { ApprovalRequest, OperatorPresence } from "./collaborationTypes";
import { generateMockApprovals, generateMockOperators } from "./collaborationFixtures";

type ApprovalStore = {
  requests: ApprovalRequest[];
  operators: OperatorPresence[];
  
  addRequest: (request: ApprovalRequest) => void;
  addDecision: (
    approvalId: string,
    decision: ApprovalRequest["decisions"][number]
  ) => void;
  updateStatus: (approvalId: string, status: ApprovalRequest["status"]) => void;
  setOperators: (operators: OperatorPresence[]) => void;
  updateOperatorStatus: (operatorId: string, status: OperatorPresence["status"]) => void;
};

export const useApprovalStore = create<ApprovalStore>((set) => ({
  requests: generateMockApprovals(),
  operators: generateMockOperators(),

  addRequest: (request) =>
    set((state) => ({
      requests: [request, ...state.requests],
    })),

  addDecision: (approvalId, decision) =>
    set((state) => {
      const updatedRequests = state.requests.map((request) => {
        if (request.approval_id === approvalId) {
          const newDecisions = [decision, ...request.decisions];
          
          // Determine status based on decision
          let newStatus = request.status;
          if (decision.decision === "approve") {
            const hasDual = request.command.risk === "critical";
            const uniqueApprovers = new Set(
              newDecisions
                .filter((d) => d.decision === "approve")
                .map((d) => d.decided_by.id)
            );
            if (!hasDual || uniqueApprovers.size >= 2) {
              newStatus = "approved";
            }
          } else if (decision.decision === "reject") {
            newStatus = "rejected";
          } else if (decision.decision === "request_changes") {
            newStatus = "changes_requested";
          }

          return {
            ...request,
            decisions: newDecisions,
            status: newStatus
          };
        }
        return request;
      });

      return { requests: updatedRequests };
    }),

  updateStatus: (approvalId, status) =>
    set((state) => ({
      requests: state.requests.map((request) =>
        request.approval_id === approvalId ? { ...request, status } : request
      ),
    })),

  setOperators: (operators) => set({ operators }),
  
  updateOperatorStatus: (operatorId, status) =>
    set((state) => ({
      operators: state.operators.map((op) =>
        op.id === operatorId ? { ...op, status, last_active: new Date().toISOString() } : op
      )
    })),
}));
