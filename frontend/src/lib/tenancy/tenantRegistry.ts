import { create } from "zustand";
import type { TenantRecord, TenantStatus, TenantPlan } from "./tenantTypes";
import { initialTenants } from "./tenantFixtures";
import { evaluateTenantIsolation } from "./isolationChecks";

type TenantStore = {
  tenants: TenantRecord[];
  activeTenant: TenantRecord | null;
  registerTenant: (tenant: Omit<TenantRecord, "status" | "usage" | "lifecycle">) => void;
  updateTenantStatus: (id: string, status: TenantStatus) => void;
  updateTenantQuotas: (id: string, quotas: TenantRecord["quotas"]) => void;
  updateTenantPolicy: (id: string, policy: TenantRecord["policy"]) => void;
  addUserToTenant: (id: string, admin: TenantRecord["admins"][number]) => void;
  selectTenant: (id: string) => void;
};

const triggerAuditLog = (
  action: string,
  summary: string,
  targetId: string,
  targetName: string,
  severity: "info" | "low" | "medium" | "high" | "critical",
  result: "success" | "failed" | "blocked" | "warning" | "pending",
  tenantId?: string
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
      metadata: {
        tenant_id: tenantId || targetId,
      },
    });
  }
};

export const useTenantStore = create<TenantStore>((set, get) => ({
  tenants: initialTenants,
  activeTenant: initialTenants[0] || null,

  registerTenant: (tenant) => {
    const newTenant: TenantRecord = {
      ...tenant,
      status: "active",
      usage: {
        users: tenant.admins.length,
        agents: 0,
        events_today: 0,
        integrations: 0,
        storage_gb: 0,
      },
      lifecycle: {
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    };

    set((state) => ({
      tenants: [...state.tenants, newTenant],
    }));

    triggerAuditLog(
      "TENANT_CREATED",
      `Tenant onboarded: ${newTenant.name} (${newTenant.plan})`,
      newTenant.tenant_id,
      newTenant.name,
      "low",
      "success",
      newTenant.tenant_id
    );

    // Run isolation check
    const check = evaluateTenantIsolation(newTenant);
    triggerAuditLog(
      "TENANT_ISOLATION_CHECKED",
      `Isolation evaluation completed for ${newTenant.name}. Status: ${check.passed ? "PASSED" : "WARNING"} (${check.findings.length} findings)`,
      newTenant.tenant_id,
      newTenant.name,
      check.passed ? "info" : "high",
      check.passed ? "success" : "warning",
      newTenant.tenant_id
    );
  },

  updateTenantStatus: (id, status) => {
    set((state) => {
      const updated = state.tenants.map((t) => {
        if (t.tenant_id === id) {
          const nowStr = new Date().toISOString();
          const updatedTenant = {
            ...t,
            status,
            lifecycle: {
              ...t.lifecycle,
              updated_at: nowStr,
              suspended_at: status === "suspended" ? nowStr : t.lifecycle.suspended_at,
              archived_at: status === "archived" ? nowStr : t.lifecycle.archived_at,
            },
          };

          let auditAction = "TENANT_UPDATED";
          let auditMsg = `Tenant ${t.name} state updated to ${status}`;
          let result: "success" | "warning" | "blocked" = "success";

          if (status === "suspended") {
            auditAction = "TENANT_SUSPENDED";
            auditMsg = `Tenant SUSPENDED: ${t.name}. Access blocked.`;
            result = "blocked";
          } else if (status === "archived") {
            auditAction = "TENANT_ARCHIVED";
            auditMsg = `Tenant ARCHIVED: ${t.name}. Isolation storage locked.`;
            result = "blocked";
          }

          triggerAuditLog(
            auditAction,
            auditMsg,
            t.tenant_id,
            t.name,
            status === "active" ? "low" : "high",
            result,
            t.tenant_id
          );

          return updatedTenant;
        }
        return t;
      });
      
      const active = updated.find((t) => t.tenant_id === get().activeTenant?.tenant_id) || null;
      return { tenants: updated, activeTenant: active };
    });
  },

  updateTenantQuotas: (id, quotas) => {
    set((state) => {
      const updated = state.tenants.map((t) => {
        if (t.tenant_id === id) {
          const updatedTenant = {
            ...t,
            quotas,
            lifecycle: {
              ...t.lifecycle,
              updated_at: new Date().toISOString(),
            },
          };

          triggerAuditLog(
            "TENANT_QUOTA_UPDATED",
            `Quotas updated for ${t.name}. User cap: ${quotas.max_users}, Agent cap: ${quotas.max_agents}, Storage: ${quotas.max_storage_gb}GB`,
            t.tenant_id,
            t.name,
            "medium",
            "success",
            t.tenant_id
          );

          return updatedTenant;
        }
        return t;
      });

      const active = updated.find((t) => t.tenant_id === get().activeTenant?.tenant_id) || null;
      return { tenants: updated, activeTenant: active };
    });
  },

  updateTenantPolicy: (id, policy) => {
    set((state) => {
      const updated = state.tenants.map((t) => {
        if (t.tenant_id === id) {
          const updatedTenant = {
            ...t,
            policy,
            lifecycle: {
              ...t.lifecycle,
              updated_at: new Date().toISOString(),
            },
          };

          triggerAuditLog(
            "TENANT_POLICY_UPDATED",
            `Policies updated for ${t.name}. Environments allowed: ${policy.allowed_environments.join(", ")}, Data region: ${policy.data_residency_region || "None"}`,
            t.tenant_id,
            t.name,
            "medium",
            "success",
            t.tenant_id
          );

          return updatedTenant;
        }
        return t;
      });

      const active = updated.find((t) => t.tenant_id === get().activeTenant?.tenant_id) || null;
      return { tenants: updated, activeTenant: active };
    });
  },

  addUserToTenant: (id, admin) => {
    set((state) => {
      const updated = state.tenants.map((t) => {
        if (t.tenant_id === id) {
          const updatedTenant = {
            ...t,
            admins: [...t.admins, admin],
            usage: {
              ...t.usage,
              users: t.usage.users + 1,
            },
            lifecycle: {
              ...t.lifecycle,
              updated_at: new Date().toISOString(),
            },
          };

          triggerAuditLog(
            "TENANT_USER_ADDED",
            `User user added to tenant ${t.name}: ${admin.name} (${admin.email})`,
            t.tenant_id,
            t.name,
            "low",
            "success",
            t.tenant_id
          );

          return updatedTenant;
        }
        return t;
      });

      const active = updated.find((t) => t.tenant_id === get().activeTenant?.tenant_id) || null;
      return { tenants: updated, activeTenant: active };
    });
  },

  selectTenant: (id) => {
    const t = get().tenants.find((x) => x.tenant_id === id) || null;
    set({ activeTenant: t });
  },
}));
