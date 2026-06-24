import { create } from "zustand";
import type { AdversarialScenario } from "./adversarialTypes";
import { initialScenarios } from "./adversarialFixtures";
import { runMockScenario } from "./redTeamRunner";

export type RemediationTask = {
  task_id: string;
  scenario_id: string;
  scenario_name: string;
  failed_assertion: string;
  description: string;
  status: "open" | "resolved";
  created_at: string;
};

type ChaosEngineStore = {
  scenarios: AdversarialScenario[];
  remediations: RemediationTask[];
  injectedFaults: {
    telemetryDelay: number; // in milliseconds
    packetLoss: number;     // percentage (0-100)
    apiErrors: number;      // percentage (0-100)
    dbLatency: number;      // in milliseconds
  };
  runScenario: (scenarioId: string) => void;
  setFault: (key: "telemetryDelay" | "packetLoss" | "apiErrors" | "dbLatency", value: number) => void;
  resolveRemediation: (taskId: string) => void;
};

const triggerAuditLog = (action: string, summary: string, targetId: string, severity: string, result: string) => {
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
        name: "Chaos Engine",
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

export const useChaosEngineStore = create<ChaosEngineStore>((set) => ({
  scenarios: initialScenarios,
  remediations: [],
  injectedFaults: {
    telemetryDelay: 0,
    packetLoss: 0,
    apiErrors: 0,
    dbLatency: 0,
  },

  runScenario: (scenarioId) => {
    set((state) => {
      const scenario = state.scenarios.find((s) => s.scenario_id === scenarioId);
      if (!scenario) return state;

      const runResult = runMockScenario(scenario);
      const scenarios = state.scenarios.map((s) => (s.scenario_id === scenarioId ? runResult : s));

      // Handle remediation creation if failed
      let newRemediations = [...state.remediations];
      if (runResult.result?.status === "failed") {
        runResult.result.failed_assertions.forEach((failAst) => {
          const matchingAst = runResult.assertions.find((a) => a.assertion_id === failAst);
          const taskId = `rem-${scenarioId}-${Date.now().toString().slice(-4)}`;

          const newTask: RemediationTask = {
            task_id: taskId,
            scenario_id: scenarioId,
            scenario_name: runResult.name,
            failed_assertion: failAst,
            description: matchingAst ? `Fix failed assertion: ${matchingAst.description}` : `Remediate security guardrail failure ${failAst}`,
            status: "open",
            created_at: new Date().toISOString(),
          };

          newRemediations.push(newTask);

          triggerAuditLog(
            "REMEDIATION_TASK_CREATED",
            `Remediation task created: ${newTask.description}`,
            taskId,
            "medium",
            "success"
          );
        });
      }

      return { scenarios, remediations: newRemediations };
    });
  },

  setFault: (key, value) => {
    set((state) => {
      const injectedFaults = { ...state.injectedFaults, [key]: value };

      triggerAuditLog(
        "FAULT_INJECTED",
        `Chaos fault injected: ${key} set to ${value}`,
        `fault-${key}`,
        value > 0 ? "medium" : "info",
        "success"
      );

      // Trigger audit log for CHAOS_DRILL_STARTED if fault is added
      if (value > 0) {
        triggerAuditLog(
          "CHAOS_DRILL_STARTED",
          `Active chaos drill triggered by injecting fault ${key}: ${value}`,
          `drill-${key}`,
          "medium",
          "success"
        );
      } else {
        triggerAuditLog(
          "CHAOS_DRILL_COMPLETED",
          `Active chaos drill stopped for fault ${key}`,
          `drill-${key}`,
          "info",
          "success"
        );
      }

      return { injectedFaults };
    });
  },

  resolveRemediation: (taskId) => {
    set((state) => {
      const remediations = state.remediations.map((rem) =>
        rem.task_id === taskId ? { ...rem, status: "resolved" as const } : rem
      );

      const matchingRem = state.remediations.find((r) => r.task_id === taskId);
      if (matchingRem) {
        triggerAuditLog(
          "REMEDIATION_TASK_CREATED", // Use task created or mapping to log resolve
          `Remediation task resolved: ${matchingRem.description}`,
          taskId,
          "info",
          "success"
        );
      }

      return { remediations };
    });
  },
}));
