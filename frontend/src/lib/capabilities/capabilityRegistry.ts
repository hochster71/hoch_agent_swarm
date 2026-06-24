import { create } from "zustand";
import type { CapabilityRecord, CapabilityStatus, CapabilityRisk } from "./capabilityTypes";
import { scoreCapabilityRisk } from "./capabilityRisk";
import { initialCapabilities } from "./capabilityFixtures";

type TestResult = {
  test_name: string;
  passed: boolean;
  duration_ms: number;
  message: string;
};

type CapabilityRegistryStore = {
  capabilities: CapabilityRecord[];
  testResults: Record<string, { running: boolean; results: TestResult[] }>;
  registerCapability: (cap: Omit<CapabilityRecord, "risk" | "lifecycle" | "telemetry">) => void;
  updatePermissions: (capId: string, permissions: CapabilityRecord["permissions"]) => void;
  transitionLifecycle: (capId: string, nextStatus: CapabilityStatus) => void;
  runTests: (capId: string) => Promise<void>;
  executeCapability: (capId: string) => boolean;
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

export const useCapabilityRegistryStore = create<CapabilityRegistryStore>((set, get) => ({
  capabilities: initialCapabilities.map((c) => {
    const scored = scoreCapabilityRisk(c);
    return { ...c, risk: scored.risk };
  }),
  testResults: {},

  registerCapability: (cap) => {
    const newCap: CapabilityRecord = {
      ...cap,
      risk: "low",
      lifecycle: {
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      telemetry: {
        executions_30d: 0,
        failure_rate_30d: 0,
        avg_latency_ms: 0,
      },
    };
    const scored = scoreCapabilityRisk(newCap);
    newCap.risk = scored.risk;

    set((state) => ({
      capabilities: [...state.capabilities, newCap],
    }));

    triggerAuditLog(
      "CAPABILITY_REGISTERED",
      `Capability registered: ${newCap.name} (${newCap.kind}) with risk level ${newCap.risk}`,
      newCap.capability_id,
      newCap.name,
      newCap.risk === "critical" || newCap.risk === "high" ? "high" : "low",
      "success"
    );
  },

  updatePermissions: (capId, permissions) => {
    set((state) => {
      const updated = state.capabilities.map((c) => {
        if (c.capability_id === capId) {
          const updatedCap = {
            ...c,
            permissions,
            lifecycle: {
              ...c.lifecycle,
              updated_at: new Date().toISOString(),
            },
          };
          const scored = scoreCapabilityRisk(updatedCap);
          updatedCap.risk = scored.risk;

          // Trigger audit log for permission change
          triggerAuditLog(
            "CAPABILITY_PERMISSION_CHANGED",
            `Capability permissions updated for ${c.name}. Computed risk level is now ${scored.risk}. Reasons: ${scored.reasons.join(", ")}`,
            c.capability_id,
            c.name,
            scored.risk === "critical" || scored.risk === "high" ? "high" : "low",
            "success"
          );

          return updatedCap;
        }
        return c;
      });
      return { capabilities: updated };
    });
  },

  transitionLifecycle: (capId, nextStatus) => {
    set((state) => {
      const updated = state.capabilities.map((c) => {
        if (c.capability_id === capId) {
          const nowStr = new Date().toISOString();
          const updatedCap: CapabilityRecord = {
            ...c,
            status: nextStatus,
            lifecycle: {
              ...c.lifecycle,
              updated_at: nowStr,
              approved_at: nextStatus === "approved" ? nowStr : c.lifecycle.approved_at,
              deprecated_at: nextStatus === "deprecated" ? nowStr : c.lifecycle.deprecated_at,
              retired_at: nextStatus === "retired" ? nowStr : c.lifecycle.retired_at,
            },
          };

          let auditAction = "";
          let auditMsg = "";
          let result: "success" | "failed" | "blocked" | "warning" | "pending" = "success";

          if (nextStatus === "approved") {
            auditAction = "CAPABILITY_APPROVED";
            auditMsg = `Capability approved for execution: ${c.name} (${c.version})`;
          } else if (nextStatus === "restricted") {
            auditAction = "CAPABILITY_RESTRICTED";
            auditMsg = `Capability restricted: ${c.name} due to security constraints.`;
            result = "warning";
          } else if (nextStatus === "deprecated") {
            auditAction = "CAPABILITY_DEPRECATED";
            auditMsg = `Capability marked deprecated: ${c.name}`;
          } else if (nextStatus === "retired") {
            auditAction = "CAPABILITY_RETIRED";
            auditMsg = `Capability retired: ${c.name}. Execution is now blocked.`;
            result = "blocked";
          }

          if (auditAction) {
            triggerAuditLog(
              auditAction,
              auditMsg,
              c.capability_id,
              c.name,
              c.risk === "critical" || c.risk === "high" ? "high" : "low",
              result
            );
          }

          return updatedCap;
        }
        return c;
      });
      return { capabilities: updated };
    });
  },

  runTests: async (capId) => {
    const c = get().capabilities.find((cap) => cap.capability_id === capId);
    if (!c) return;

    set((state) => ({
      testResults: {
        ...state.testResults,
        [capId]: { running: true, results: [] },
      },
    }));

    // Transition status to testing
    if (c.status === "draft") {
      get().transitionLifecycle(capId, "testing");
    }

    // Simulate test runs delay
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Compile mock results based on risk and permissions
    const results: TestResult[] = [
      {
        test_name: "Sandboxing Integrity Test",
        passed: true,
        duration_ms: 120,
        message: "No runtime leakage detected. Sandbox namespace constraints verified.",
      },
      {
        test_name: "Permission Bounds Assertion",
        passed: !c.permissions.shell || c.guardrails.requires_human_approval,
        duration_ms: 80,
        message: c.permissions.shell && !c.guardrails.requires_human_approval
          ? "FAIL: Unapproved shell execution without human gatekeeper constraint."
          : "PASS: Active credentials matched allowed policy scopes.",
      },
      {
        test_name: "Static Code Vulnerability Scan",
        passed: c.risk !== "critical",
        duration_ms: 220,
        message: c.risk === "critical"
          ? "WARNING: Unsafe system call usage detected in ad-hoc scripts."
          : "PASS: Code logic scan verified against OWASP SAMM patterns.",
      },
      {
        test_name: "Telemetry Integration Checks",
        passed: true,
        duration_ms: 50,
        message: "Active telemetry emitter and latency diagnostics responding.",
      },
    ];

    set((state) => ({
      testResults: {
        ...state.testResults,
        [capId]: { running: false, results },
      },
    }));

    const allPassed = results.every((r) => r.passed);

    triggerAuditLog(
      "CAPABILITY_TESTED",
      `Capability verification test suite completed for ${c.name}. Results: ${
        allPassed ? "PASS" : "FAIL"
      } (${results.filter((r) => r.passed).length}/${results.length} tests passed)`,
      c.capability_id,
      c.name,
      allPassed ? "info" : "high",
      allPassed ? "success" : "failed"
    );
  },

  executeCapability: (capId) => {
    const c = get().capabilities.find((cap) => cap.capability_id === capId);
    if (!c) return false;

    // Block execution if restricted or retired
    if (c.status === "restricted" || c.status === "retired") {
      triggerAuditLog(
        "CAPABILITY_EXECUTED",
        `Execution BLOCKED for capability ${c.name} (Status: ${c.status})`,
        c.capability_id,
        c.name,
        "high",
        "blocked"
      );
      return false;
    }

    // Otherwise increment telemetry usage
    set((state) => {
      const updated = state.capabilities.map((cap) => {
        if (cap.capability_id === capId) {
          return {
            ...cap,
            telemetry: {
              ...cap.telemetry,
              executions_30d: cap.telemetry.executions_30d + 1,
              last_used_at: new Date().toISOString(),
            },
          };
        }
        return cap;
      });
      return { capabilities: updated };
    });

    triggerAuditLog(
      "CAPABILITY_EXECUTED",
      `Executed capability: ${c.name} (${c.version}). Latency: ${c.telemetry.avg_latency_ms || 120}ms.`,
      c.capability_id,
      c.name,
      c.risk === "critical" ? "high" : "info",
      "success"
    );

    return true;
  },
}));
