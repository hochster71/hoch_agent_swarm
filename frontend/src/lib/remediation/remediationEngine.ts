import { create } from "zustand";
import type { Runbook, RunbookExecution, RunbookExecutionStatus, RunbookStatus } from "./runbookTypes";
import { initialRunbooks, initialExecutions } from "./remediationFixtures";
import { simulateRunbook } from "./runbookSimulator";

type RemediationStore = {
  runbooks: Runbook[];
  executions: RunbookExecution[];
  activeExecution: RunbookExecution | null;
  registerRunbook: (runbook: Omit<Runbook, "status" | "version">) => void;
  updateRunbookStatus: (id: string, status: RunbookStatus) => void;
  startExecution: (runbookId: string) => Promise<string>;
  triggerRollback: (executionId: string) => Promise<void>;
  approveExecutionStep: (executionId: string, stepId: string) => void;
  selectExecution: (id: string) => void;
  clearActiveExecution: () => void;
};

const triggerAuditLog = (
  action: string,
  summary: string,
  targetId: string,
  targetName: string,
  severity: "info" | "low" | "medium" | "high" | "critical",
  result: "success" | "failed" | "blocked" | "warning" | "pending"
) => {
  if (typeof window !== "undefined" && window.addAuditEvent) {
    window.addAuditEvent({
      action: {
        type: action,
        summary: summary,
      },
      actor: {
        id: "remediation-engine",
        name: "Closed-Loop Recovery Agent",
        type: "agent",
        role: "Autonomous Remediation",
      },
      target: {
        type: "task",
        id: targetId,
        name: targetName,
      },
      result: result,
      severity: severity,
      provenance: {
        source: "predicted",
        evidence_refs: [],
      },
      policy: {
        required: false,
        result: "not_required",
      },
    });
  }
};

export const useRemediationStore = create<RemediationStore>((set, get) => ({
  runbooks: initialRunbooks,
  executions: initialExecutions,
  activeExecution: null,

  registerRunbook: (runbook) => {
    const newRb: Runbook = {
      ...runbook,
      status: "draft",
      version: "v1.0.0",
    };

    set((state) => ({
      runbooks: [...state.runbooks, newRb],
    }));

    triggerAuditLog(
      "RUNBOOK_CREATED",
      `Runbook created: ${newRb.name} (${newRb.version}) for triggers: ${newRb.trigger_conditions.join(", ")}`,
      newRb.runbook_id,
      newRb.name,
      "low",
      "success"
    );
  },

  updateRunbookStatus: (id, status) => {
    set((state) => {
      const updated = state.runbooks.map((rb) => {
        if (rb.runbook_id === id) {
          const updatedRb = { ...rb, status };
          
          if (status === "approved") {
            triggerAuditLog(
              "RUNBOOK_APPROVED",
              `Runbook approved for swarm execution: ${rb.name} (${rb.version})`,
              rb.runbook_id,
              rb.name,
              rb.risk === "critical" ? "high" : "low",
              "success"
            );
          } else if (status === "validated") {
            triggerAuditLog(
              "RUNBOOK_VALIDATED",
              `Runbook structure validated: ${rb.name}`,
              rb.runbook_id,
              rb.name,
              "low",
              "success"
            );
          }

          return updatedRb;
        }
        return rb;
      });
      return { runbooks: updated };
    });
  },

  startExecution: async (runbookId) => {
    const rb = get().runbooks.find((r) => r.runbook_id === runbookId);
    if (!rb) throw new Error("Runbook not found");

    const execId = `EXEC-${Math.floor(1000 + Math.random() * 9000)}`;
    const newExec: RunbookExecution = {
      execution_id: execId,
      runbook_id: runbookId,
      correlation_id: `corr-${Math.random().toString(36).substring(2, 8)}`,
      status: "running",
      started_at: new Date().toISOString(),
      current_step_id: rb.steps[0]?.step_id,
      step_results: rb.steps.map((s, idx) => ({
        step_id: s.step_id,
        status: idx === 0 ? "running" : "pending",
        evidence_refs: [],
      })),
      rollback: {
        available: rb.steps.some((s) => s.rollback_step_id !== undefined),
        triggered: false,
      },
    };

    set((state) => ({
      executions: [newExec, ...state.executions],
      activeExecution: newExec,
    }));

    triggerAuditLog(
      "RUNBOOK_EXECUTION_STARTED",
      `Runbook recovery started: ${rb.name} (${execId}). Correlation ID: ${newExec.correlation_id}`,
      execId,
      rb.name,
      rb.risk === "critical" ? "critical" : rb.risk === "high" ? "high" : "medium",
      "pending"
    );

    // Simulate async execution flow of steps
    const runStepsAsync = async () => {
      let currentExec = get().executions.find((e) => e.execution_id === execId);
      if (!currentExec) return;

      for (let i = 0; i < rb.steps.length; i++) {
        const step = rb.steps[i];
        
        // Wait, is the execution still running or did it pause/fail/cancel?
        currentExec = get().executions.find((e) => e.execution_id === execId);
        if (!currentExec || currentExec.status !== "running") break;

        // If step requires approval, pause execution and wait
        if (step.requires_approval) {
          set((state) => {
            const updated = state.executions.map((e) => {
              if (e.execution_id === execId) {
                const results = e.step_results.map((sr) =>
                  sr.step_id === step.step_id ? { ...sr, status: "pending" as const } : sr
                );
                return { ...e, status: "paused" as const, current_step_id: step.step_id, step_results: results };
              }
              return e;
            });
            const active = updated.find((e) => e.execution_id === execId) || null;
            return { executions: updated, activeExecution: active };
          });

          triggerAuditLog(
            "RUNBOOK_STEP_COMPLETED",
            `Execution ${execId} paused. Step "${step.title}" requires operator authorization.`,
            execId,
            rb.name,
            "high",
            "pending"
          );

          break; // Stop async loop, operator will trigger continue
        }

        // Simulate execution delay
        await new Promise((resolve) => setTimeout(resolve, 2000));

        // Mark step as succeeded
        set((state) => {
          const updated = state.executions.map((e) => {
            if (e.execution_id === execId) {
              const results = e.step_results.map((sr) => {
                if (sr.step_id === step.step_id) {
                  return {
                    ...sr,
                    status: "succeeded" as const,
                    started_at: new Date(Date.now() - 2000).toISOString(),
                    completed_at: new Date().toISOString(),
                    output: `Executed: ${step.title}. Output: Operation completed successfully. Verified state changes.`,
                    evidence_refs: [`evidence.${step.step_id}_run.log`],
                  };
                }
                return sr;
              });

              // Set next step as running
              const nextStep = rb.steps[i + 1];
              const finalResults = results.map((sr) =>
                nextStep && sr.step_id === nextStep.step_id ? { ...sr, status: "running" as const } : sr
              );

              return {
                ...e,
                current_step_id: nextStep ? nextStep.step_id : step.step_id,
                step_results: finalResults,
              };
            }
            return e;
          });
          const active = updated.find((e) => e.execution_id === execId) || null;
          return { executions: updated, activeExecution: active };
        });

        triggerAuditLog(
          "RUNBOOK_STEP_COMPLETED",
          `Step completed: ${step.title} (${step.type}) for execution ${execId}.`,
          execId,
          rb.name,
          "low",
          "success"
        );
      }

      // Check if all steps completed
      currentExec = get().executions.find((e) => e.execution_id === execId);
      const allSucceeded = currentExec?.step_results.every((sr) => sr.status === "succeeded");
      if (allSucceeded) {
        set((state) => {
          const updated = state.executions.map((e) =>
            e.execution_id === execId
              ? { ...e, status: "succeeded" as const, completed_at: new Date().toISOString() }
              : e
          );
          const active = updated.find((e) => e.execution_id === execId) || null;
          return { executions: updated, activeExecution: active };
        });

        triggerAuditLog(
          "RUNBOOK_EXECUTION_SUCCEEDED",
          `Remediation recovery SUCCEEDED: ${rb.name} (${execId}). All controls verified.`,
          execId,
          rb.name,
          "medium",
          "success"
        );

        triggerAuditLog(
          "REMEDIATION_VERIFIED",
          `Remediation verified for ${rb.name}. Success conditions matched: ${rb.verification.success_conditions.join(", ")}`,
          execId,
          rb.name,
          "medium",
          "success"
        );
      }
    };

    runStepsAsync();
    return execId;
  },

  approveExecutionStep: (executionId, stepId) => {
    const exec = get().executions.find((e) => e.execution_id === executionId);
    if (!exec) return;

    const rb = get().runbooks.find((r) => r.runbook_id === exec.runbook_id);
    if (!rb) return;

    // Resume execution
    set((state) => {
      const updated = state.executions.map((e) => {
        if (e.execution_id === executionId) {
          const results = e.step_results.map((sr) =>
            sr.step_id === stepId ? { ...sr, status: "running" as const } : sr
          );
          return { ...e, status: "running" as const, step_results: results };
        }
        return e;
      });
      const active = updated.find((e) => e.execution_id === executionId) || null;
      return { executions: updated, activeExecution: active };
    });

    triggerAuditLog(
      "RUNBOOK_APPROVED",
      `Step authorization GRANTED: Step "${stepId}" of execution ${executionId} approved by Operator.`,
      executionId,
      rb.name,
      "medium",
      "success"
    );

    // Continue step execution
    const runRemainingSteps = async () => {
      const currentStepIdx = rb.steps.findIndex((s) => s.step_id === stepId);
      
      for (let i = currentStepIdx; i < rb.steps.length; i++) {
        const step = rb.steps[i];
        
        let currentExec = get().executions.find((e) => e.execution_id === executionId);
        if (!currentExec || currentExec.status !== "running") break;

        // Simulate execution delay
        await new Promise((resolve) => setTimeout(resolve, 2000));

        // Mark step as succeeded
        set((state) => {
          const updated = state.executions.map((e) => {
            if (e.execution_id === executionId) {
              const results = e.step_results.map((sr) => {
                if (sr.step_id === step.step_id) {
                  return {
                    ...sr,
                    status: "succeeded" as const,
                    started_at: new Date(Date.now() - 2000).toISOString(),
                    completed_at: new Date().toISOString(),
                    output: `Executed: ${step.title}. Output: Operation completed successfully. Verified state changes.`,
                    evidence_refs: [`evidence.${step.step_id}_run.log`],
                  };
                }
                return sr;
              });

              const nextStep = rb.steps[i + 1];
              const finalResults = results.map((sr) =>
                nextStep && sr.step_id === nextStep.step_id ? { ...sr, status: "running" as const } : sr
              );

              return {
                ...e,
                current_step_id: nextStep ? nextStep.step_id : step.step_id,
                step_results: finalResults,
              };
            }
            return e;
          });
          const active = updated.find((e) => e.execution_id === executionId) || null;
          return { executions: updated, activeExecution: active };
        });

        triggerAuditLog(
          "RUNBOOK_STEP_COMPLETED",
          `Step completed: ${step.title} (${step.type}) for execution ${executionId}.`,
          executionId,
          rb.name,
          "low",
          "success"
        );
      }

      // Check if all steps completed
      const currentExec = get().executions.find((e) => e.execution_id === executionId);
      const allSucceeded = currentExec?.step_results.every((sr) => sr.status === "succeeded");
      if (allSucceeded) {
        set((state) => {
          const updated = state.executions.map((e) =>
            e.execution_id === executionId
              ? { ...e, status: "succeeded" as const, completed_at: new Date().toISOString() }
              : e
          );
          const active = updated.find((e) => e.execution_id === executionId) || null;
          return { executions: updated, activeExecution: active };
        });

        triggerAuditLog(
          "RUNBOOK_EXECUTION_SUCCEEDED",
          `Remediation recovery SUCCEEDED: ${rb.name} (${executionId}). All controls verified.`,
          executionId,
          rb.name,
          "medium",
          "success"
        );

        triggerAuditLog(
          "REMEDIATION_VERIFIED",
          `Remediation verified for ${rb.name}. Success conditions matched: ${rb.verification.success_conditions.join(", ")}`,
          executionId,
          rb.name,
          "medium",
          "success"
        );
      }
    };

    runRemainingSteps();
  },

  triggerRollback: async (executionId) => {
    const exec = get().executions.find((e) => e.execution_id === executionId);
    if (!exec) return;

    const rb = get().runbooks.find((r) => r.runbook_id === exec.runbook_id);
    if (!rb) return;

    set((state) => {
      const updated = state.executions.map((e) =>
        e.execution_id === executionId ? { ...e, status: "failed" as const } : e
      );
      const active = updated.find((e) => e.execution_id === executionId) || null;
      return { executions: updated, activeExecution: active };
    });

    triggerAuditLog(
      "RUNBOOK_EXECUTION_FAILED",
      `Remediation execution FAILED for ${rb.name} (${executionId}). Initiating rollback...`,
      executionId,
      rb.name,
      "high",
      "failed"
    );

    // Start Rollback
    set((state) => {
      const updated = state.executions.map((e) => {
        if (e.execution_id === executionId) {
          return {
            ...e,
            rollback: { ...e.rollback, triggered: true },
          };
        }
        return e;
      });
      const active = updated.find((e) => e.execution_id === executionId) || null;
      return { executions: updated, activeExecution: active };
    });

    triggerAuditLog(
      "RUNBOOK_ROLLBACK_TRIGGERED",
      `Rollback recovery triggered for ${rb.name} (${executionId}). Restoring initial state...`,
      executionId,
      rb.name,
      "high",
      "warning"
    );

    // Simulate rollback delay
    await new Promise((resolve) => setTimeout(resolve, 2000));

    set((state) => {
      const updated = state.executions.map((e) => {
        if (e.execution_id === executionId) {
          return {
            ...e,
            status: "rolled_back" as const,
            completed_at: new Date().toISOString(),
          };
        }
        return e;
      });
      const active = updated.find((e) => e.execution_id === executionId) || null;
      return { executions: updated, activeExecution: active };
    });

    triggerAuditLog(
      "RUNBOOK_STEP_COMPLETED",
      `Rollback completed. Initial configuration states restored for ${rb.name}.`,
      executionId,
      rb.name,
      "medium",
      "success"
    );
  },

  selectExecution: (id) => {
    const exec = get().executions.find((e) => e.execution_id === id) || null;
    set({ activeExecution: exec });
  },

  clearActiveExecution: () => {
    set({ activeExecution: null });
  },
}));
